from __future__ import annotations

import random
import time

from vwrapper.models.actions import ActionResult, VMInfo

# Fake VM database — mutable so creates/deletes persist in session
_FAKE_VMS: list[VMInfo] = [
    VMInfo(name="web-01", power_state="poweredOn", cpu=4, memory_mb=8192, guest_os="Ubuntu 22.04 (64-bit)", ip_address="10.0.1.10"),
    VMInfo(name="db-01", power_state="poweredOn", cpu=8, memory_mb=16384, guest_os="CentOS 9 (64-bit)", ip_address="10.0.1.20"),
    VMInfo(name="api-gateway", power_state="poweredOn", cpu=2, memory_mb=4096, guest_os="Alpine Linux (64-bit)", ip_address="10.0.1.30"),
    VMInfo(name="ml-worker-01", power_state="poweredOff", cpu=16, memory_mb=65536, guest_os="Ubuntu 22.04 (64-bit)", ip_address=None),
    VMInfo(name="dev-box", power_state="poweredOff", cpu=2, memory_mb=4096, guest_os="Other Linux (64-bit)", ip_address=None),
]


class FakeProvider:
    """In-memory fake provider that simulates vCenter/ESXi operations."""

    def __init__(self) -> None:
        self._vms: list[VMInfo] = list(_FAKE_VMS)
        self._connected = False

    def connect(self) -> None:
        time.sleep(0.3)  # simulate latency
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def __enter__(self) -> FakeProvider:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    @property
    def content(self):
        class _About:
            fullName = "VMware ESXi 8.0.3 build-24859861 (demo)"

        class _Content:
            about = _About()

        return _Content()

    def list_vms(self) -> list[VMInfo]:
        time.sleep(0.2)  # simulate API call
        return list(self._vms)

    def vm_count(self) -> int:
        return len(self._vms)

    def create_vm(
        self,
        name: str,
        cpu: int = 2,
        memory_mb: int = 4096,
        disk_gb: int = 40,
    ) -> ActionResult:
        time.sleep(0.5)  # simulate task
        new_vm = VMInfo(
            name=name,
            power_state="poweredOff",
            cpu=cpu,
            memory_mb=memory_mb,
            guest_os="Other Linux (64-bit)",
            ip_address=None,
        )
        self._vms.append(new_vm)
        return ActionResult(
            success=True,
            action="create_vm",
            data={"name": name, "cpu": cpu, "memory_mb": memory_mb, "disk_gb": disk_gb},
        )

    def get_capacity(self) -> dict:
        time.sleep(0.2)  # simulate API call
        total_cpu = sum(vm.cpu for vm in self._vms)
        used_cpu = sum(vm.cpu for vm in self._vms if vm.power_state == "poweredOn")
        total_mem = sum(vm.memory_mb for vm in self._vms)
        used_mem = sum(vm.memory_mb for vm in self._vms if vm.power_state == "poweredOn")

        return {
            "total_cpu_mhz": total_cpu * 2400,
            "used_cpu_mhz": used_cpu * 2400,
            "cpu_percent": round(used_cpu / total_cpu * 100, 1) if total_cpu else 0,
            "total_memory_gb": round(total_mem / 1024, 1),
            "used_memory_gb": round(used_mem / 1024, 1),
            "memory_percent": round(used_mem / total_mem * 100, 1) if total_mem else 0,
            "host_count": 1,
            "vm_count": len(self._vms),
        }
