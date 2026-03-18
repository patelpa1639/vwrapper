from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from vwrapper.models.actions import ActionResult, VMInfo

if TYPE_CHECKING:
    from vwrapper.config import VCenterConfig


class VMwareProvider:
    """VMware vCenter provider using pyvmomi."""

    def __init__(self, config: VCenterConfig) -> None:
        self._config = config
        self._si: vim.ServiceInstance | None = None

    def connect(self) -> None:
        kwargs = {
            "host": self._config.host,
            "user": self._config.user,
            "pwd": self._config.password,
            "port": 443,
        }
        if self._config.insecure:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kwargs["sslContext"] = ctx

        self._si = SmartConnect(**kwargs)

    def disconnect(self) -> None:
        if self._si:
            Disconnect(self._si)
            self._si = None

    def __enter__(self) -> VMwareProvider:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    @property
    def content(self) -> vim.ServiceInstanceContent:
        assert self._si is not None, "Not connected to vCenter"
        return self._si.RetrieveContent()

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def list_vms(self) -> list[VMInfo]:
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.VirtualMachine], True
        )
        vms: list[VMInfo] = []
        try:
            for vm in container.view:
                summary = vm.summary
                vms.append(
                    VMInfo(
                        name=summary.config.name,
                        power_state=str(summary.runtime.powerState),
                        cpu=summary.config.numCpu,
                        memory_mb=summary.config.memorySizeMB,
                        guest_os=summary.config.guestFullName or "",
                        ip_address=summary.guest.ipAddress if summary.guest else None,
                    )
                )
        finally:
            container.Destroy()
        return vms

    def vm_count(self) -> int:
        return len(self.list_vms())

    def _get_dc_and_pool(self) -> tuple:
        """Get datacenter, resource pool, and datastore.

        Works with both standalone ESXi hosts and vCenter-managed clusters.
        """
        dc = self.content.rootFolder.childEntity[0]
        compute = dc.hostFolder.childEntity[0]
        resource_pool = compute.resourcePool
        datastore = dc.datastoreFolder.childEntity[0]
        return dc, resource_pool, datastore

    def create_vm(
        self,
        name: str,
        cpu: int = 2,
        memory_mb: int = 4096,
        disk_gb: int = 40,
    ) -> ActionResult:
        dc, resource_pool, datastore = self._get_dc_and_pool()

        # VM config spec
        vm_folder = dc.vmFolder
        config_spec = vim.vm.ConfigSpec(
            name=name,
            numCPUs=cpu,
            memoryMB=memory_mb,
            guestId="otherGuest64",
            files=vim.vm.FileInfo(
                vmPathName=f"[{datastore.name}] {name}/{name}.vmx"
            ),
        )

        # Add a disk
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.fileOperation = (
            vim.vm.device.VirtualDeviceSpec.FileOperation.create
        )
        disk = vim.vm.device.VirtualDisk()
        disk.capacityInKB = disk_gb * 1024 * 1024
        disk.controllerKey = 0
        disk.unitNumber = 0
        disk_backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_backing.diskMode = "persistent"
        disk_backing.fileName = f"[{datastore.name}] {name}/{name}.vmdk"
        disk.backing = disk_backing
        disk_spec.device = disk
        config_spec.deviceChange = [disk_spec]

        task = vm_folder.CreateVM_Task(
            config=config_spec, pool=resource_pool
        )
        self._wait_for_task(task)

        return ActionResult(
            success=True,
            action="create_vm",
            data={
                "name": name,
                "cpu": cpu,
                "memory_mb": memory_mb,
                "disk_gb": disk_gb,
            },
        )

    def get_capacity(self) -> dict:
        """Fetch host/cluster-level capacity summary."""
        dc = self.content.rootFolder.childEntity[0]
        compute = dc.hostFolder.childEntity[0]

        total_cpu_mhz = 0
        total_memory_bytes = 0
        used_cpu_mhz = 0
        used_memory_bytes = 0

        for host in compute.host:
            total_cpu_mhz += host.summary.hardware.cpuMhz * host.summary.hardware.numCpuCores
            total_memory_bytes += host.summary.hardware.memorySize
            used_cpu_mhz += host.summary.quickStats.overallCpuUsage
            used_memory_bytes += host.summary.quickStats.overallMemoryUsage * 1024 * 1024

        return {
            "total_cpu_mhz": total_cpu_mhz,
            "used_cpu_mhz": used_cpu_mhz,
            "cpu_percent": round(used_cpu_mhz / total_cpu_mhz * 100, 1) if total_cpu_mhz else 0,
            "total_memory_gb": round(total_memory_bytes / (1024**3), 1),
            "used_memory_gb": round(used_memory_bytes / (1024**3), 1),
            "memory_percent": round(used_memory_bytes / total_memory_bytes * 100, 1) if total_memory_bytes else 0,
            "host_count": len(compute.host),
            "vm_count": self.vm_count(),
        }

    def _wait_for_task(self, task: vim.Task) -> None:
        while task.info.state in (
            vim.TaskInfo.State.queued,
            vim.TaskInfo.State.running,
        ):
            pass
        if task.info.state == vim.TaskInfo.State.error:
            raise RuntimeError(f"VMware task failed: {task.info.error.msg}")
