#!/usr/bin/env python3

import argparse, sys, os
sys.path.append(os.path.join(sys.path[0], "../pci"))
sys.path.append(os.path.join(sys.path[0], "../lib"))
from libpci import *
from devmem import DevMem

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("dev")
    args = parser.parse_args()

    return args


if os.geteuid() != 0:
    exit("Please run script this as root")

args = get_args()
dev = PciDev(args.dev)

# Get the offset for SATA AHCI base address
hba_base = dev.get_bar(5)
print(f"BAR5@{hba_base:x}")

hba_cap = dev.read_bar5(0, 4)
port_num = (hba_cap & 0x1F) + 1
print(f"SATA AHCI Port Num: {port_num}")

for port in range(port_num):
    port_reg_base = 0x100 + port * 0x80
    port_ssts = dev.read_bar5(port_reg_base + 0x28, 4)
    ipm = (port_ssts >> 8) & 0x0F
    det = port_ssts & 0x0F
    print(f"Port {port}: SSTS=0x{port_ssts:08x} (IPM={ipm}, DET={det})")
    if det == 3:
        print(f"  Port {port} is connected to a device.")
        port_sig = dev.read_bar5(port_reg_base + 0x24, 4)
        if port_sig == 0x00000101:
            print(f"  Port {port} Device: SATA drive")
        elif port_sig == 0xEB140101:
            print(f"  Port {port} Device: ATAPI drive")
        else:
            print(f"  Port {port} Device: Unknown (Signature=0x{port_sig:08x})")
    else:
        print(f"  Port {port} is not connected to any device.")
