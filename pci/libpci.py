import sys, os

sys.path.append(os.path.join(sys.path[0], ".."))
from lib.devmem import *
from lib.sys import read_f

class CAP_ID:
    MSIX = 0x11

class ECAP_ID:
    L1PM = 0x001E

def _read(reg, offset, size):
    return int.from_bytes(reg[offset:offset+size], byteorder='little')

def _en(val):
    return "+" if val else "-"

class PciDev:
    def __init__(self, dev):
        self.dev = dev
        self.devmem = DevMem()

        with open(f"/sys/bus/pci/devices/{dev}/config", mode="rb") as file:
            self.config = file.read()

        # Split PCI resource host addresses to double-dword string
        resources = read_f(f"/sys/bus/pci/devices/{dev}/resource").split(' ')
        self.base = int(resources[0], 16)

    def find_cap(self, target_cap_id):
        # Find capibility pointer at offset 0x34
        next_cap = self.config[0x34]
        cap_id = self.config[next_cap]

        while cap_id != target_cap_id:
            if cap_id == 0 or cap_id >= 0x12:
                break
            # Try to find next availible cap
            next_cap = self.config[next_cap + 1]
            cap_id = self.config[next_cap]

        if cap_id == target_cap_id:
            return next_cap

        return -1

    def find_ecap(self, target_ecap_id):
        # Find extend cap header
        pcie_cap_id = _read(self.config, 0x100, 4)
        cap_id = pcie_cap_id & 0xff

        while cap_id != target_ecap_id:
            if cap_id == 0 or cap_id >= 0x29:
                break
            # Try to find next availible cap
            next_cap = pcie_cap_id >> 20

            pcie_cap_id = _read(self.config, next_cap, 4)
            cap_id = pcie_cap_id & 0xff

        if cap_id == target_ecap_id:
            return next_cap

        return -1

    def dump_bar(self):
        # Show the content for BAR 0 to 5
        for i in range(6):
            offset = 0x10 + 4 * i
            value = _read(self.config, offset, 4)
            print(f"BAR {i}({offset:x})@{value:x}")

    def dump_msix(self, offset):
        msg_ctl = _read(self.config, offset, 4) >> 16
        entry_cnt = msg_ctl & 0x3ff
        print(f"MSI-X/{(msg_ctl >> 15) & 1} entry cnt = {entry_cnt}")
        table_off = _read(self.config, offset+4, 4) & ~0x7
        pba_off = _read(self.config, offset+8, 4) & ~0x7
        print(f"MSI-X table @{hex(self.base + table_off)}, PBA@{hex(self.base + pba_off)}")

        entry_size = 16
        for i in range(entry_cnt):
            addr = self.base + table_off + i * 16
            msg_addr = self.devmem.read(addr, 4, False)
            msg_upper = self.devmem.read(addr + 4, 4, False)
            msg_data = self.devmem.read(addr + 8, 4, False)
            vec_ctl = self.devmem.read(addr + 12, 4, False)
            print(f"MSI-X Entry[{i}] @{addr:x}")
            print(f"Message address {hex(msg_upper << 32 | msg_addr)}, Data: {msg_data:x}")
            print(f"Vector control: {vec_ctl:x}")

    def dump_l1pm(self, offset):
        # L1 PM Substates Capabilities Register(0x4)
        val = _read(self.config, offset+4, 4)
        print(f"L1SubCap: PCI-PM_L1.2%s PCI-PM_L1.1%s ASPM_L1.2%s ASPM_L1.1%s" %
                (_en(val & 1), _en((val >> 1) & 1), _en((val >> 2) & 1), _en((val >> 3) & 1)))
        val = _read(self.config, offset+8, 4)
        print(f"L1SubCtl1: PCI-PM_L1.2%s PCI-PM_L1.1%s ASPM_L1.2%s ASPM_L1.1%s" %
                (_en(val & 1), _en((val >> 1) & 1), _en((val >> 2) & 1), _en((val >> 3) & 1)))
