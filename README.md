# pm-tools

## Overview

pm-tools is a suite of tools that facilitate obtaining or configuring power management settings and states for devices on Linux.

## Tools

### pci

* `aspm_dump.py`: Dump ASPM-related information
* `msi_dump.py`: Dump PCIe MSI/MSI-X related information
* `pcie_setspeed.sh`: Configure the PCIe device Gen speed in runtime

### usb

* `xhci-stat.sh`: Get the link power state of the USB devices under the xHCI controller  

### ata

* `pcie_sata_controller.py`: Get the link power state of the SATA devices under the PCIe SATA controller 
