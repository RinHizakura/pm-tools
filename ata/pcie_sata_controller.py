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

print(f"{dev.read_bar5(0, 4):x}")
