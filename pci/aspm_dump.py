#!/usr/bin/env python3

import argparse
from libpci import *

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("dev")
    args = parser.parse_args()

    return args


if os.geteuid() != 0:
    exit("Please run script this as root")

args = get_args()
dev = PciDev(args.dev)

# Get the offset for MSI-X Capability structure
l1pm_cap = dev.find_ecap(ECAP_ID.L1PM)
dev.dump_l1pm(l1pm_cap)
