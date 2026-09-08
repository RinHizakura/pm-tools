#!/usr/bin/env python3
"""Run `lspci -D -vvv` on the local machine and report PCIe link/slot/AER anomalies.

Usage:
    sudo ./pci_health.py
"""

import re
import subprocess

SPEED_GT = {"2.5GT/s": 1, "5GT/s": 2, "8GT/s": 3, "16GT/s": 4, "32GT/s": 5, "64GT/s": 6}

BDF_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F]$")
BLOCK_RE = re.compile(r"^(\S+) (.+)$")


def get_lspci_output():
    return subprocess.run(["sudo", "lspci", "-D", "-vvv"],
                           capture_output=True, text=True, check=True).stdout


def parse_devices(text):
    devices = []
    cur = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            m = BLOCK_RE.match(line)
            if m and BDF_RE.match(m.group(1)):
                cur = {"bdf": m.group(1), "desc": m.group(2), "lines": []}
                devices.append(cur)
            continue
        if cur is not None:
            cur["lines"].append(line.strip())
    return devices


def field(pattern, text, group=1):
    m = re.search(pattern, text)
    return m.group(group) if m else None


def check_slot_link_active(body):
    """Slot has a card seated (PresDet+) but the link never trained (DLActive-)."""
    slt_cap = "SltCap:" in body
    if not slt_cap:
        return []
    pres_det = "PresDet+" in body
    dl_active = "DLActive+" in body
    if pres_det and not dl_active:
        return ["card present (PresDet+) but PCIe link never came up (DLActive-) "
                "-> endpoint unresponsive, needs power cycle"]
    return []


def check_link_speed_width(body):
    """Trained link speed/width below what the device is capable of."""
    lnk_cap_m = re.search(r"LnkCap:\s*.*?Speed ([\d.]+GT/s),\s*Width (x\d+)", body)
    lnk_sta_m = re.search(r"LnkSta:\s*Speed ([\d.]+GT/s),\s*Width (x\d+)", body)
    if not (lnk_cap_m and lnk_sta_m):
        return []

    issues = []
    cap_speed, cap_width = lnk_cap_m.groups()
    sta_speed, sta_width = lnk_sta_m.groups()

    if sta_width == "x0":
        return ["link width x0 (link down)"]

    if sta_width != cap_width:
        issues.append(f"link width trained {sta_width}, capable of {cap_width}")

    cap_gen = SPEED_GT.get(cap_speed)
    sta_gen = SPEED_GT.get(sta_speed)
    if cap_gen and sta_gen and sta_gen < cap_gen:
        issues.append(f"link speed trained {sta_speed}, capable of {cap_speed}")

    return issues


def check_aer_errors(body):
    """AER uncorrectable/correctable error bits latched in the status registers."""
    issues = []

    ue_sta = field(r"UESta:\s*(.+)", body)
    if ue_sta:
        set_bits = [b[:-1] for b in ue_sta.split() if b.endswith("+")]
        if set_bits:
            issues.append(f"AER uncorrectable error latched: {', '.join(set_bits)}")

    ce_sta = field(r"CESta:\s*(.+)", body)
    if ce_sta:
        set_bits = [b[:-1] for b in ce_sta.split() if b.endswith("+")]
        if set_bits:
            issues.append(f"AER correctable error latched: {', '.join(set_bits)} (informational)")

    return issues


def check_driver_bound(dev, body):
    """Non-bridge device with no kernel driver attached."""
    is_bridge = "PCI bridge" in dev["desc"]
    driver = field(r"Kernel driver in use:\s*(\S+)", body)
    if not is_bridge and driver is None and "Class" not in dev["desc"]:
        return ["no kernel driver bound"]
    return []


def check_dpc_triggered(body):
    """Downstream Port Containment fired and shut the link down."""
    dpc_sta = field(r"DpcSta:\s*(.+)", body)
    if dpc_sta and "Trigger+" in dpc_sta:
        reason = field(r"Reason:(\S+)", dpc_sta)
        return [f"DPC triggered (Reason:{reason}) -> port auto-disabled, link stays down until cleared/reset"]
    return []


def check_root_error_status(body):
    """Root Port's RootSta shows an error was reported up to the root complex."""
    root_sta = field(r"RootSta:\s*(.+)", body)
    if not root_sta:
        return []
    set_bits = [b[:-1] for b in root_sta.split() if b.endswith("+")]
    if set_bits:
        return [f"Root Port reports error(s) from a downstream device: {', '.join(set_bits)}"]
    return []


def check_bus_aborts(body):
    """Master/Target Abort seen on the primary bus Status register."""
    m = re.search(r"^Status:\s*(.+)$", body, re.MULTILINE)
    status = m.group(1) if m else None
    if not status:
        return []
    issues = []
    if "<MAbort+" in status:
        issues.append("Master Abort signaled on this device's bus (<MAbort+)")
    if "<TAbort+" in status:
        issues.append("Target Abort signaled on this device's bus (<TAbort+)")
    if ">TAbort+" in status:
        issues.append("Target Abort received by this device (>TAbort+)")
    return issues


CHECKS = [
    lambda dev, body: check_slot_link_active(body),
    lambda dev, body: check_link_speed_width(body),
    lambda dev, body: check_aer_errors(body),
    check_driver_bound,
    lambda dev, body: check_dpc_triggered(body),
    lambda dev, body: check_root_error_status(body),
    lambda dev, body: check_bus_aborts(body),
]


def check_device(dev):
    body = "\n".join(dev["lines"])
    issues = []
    for check in CHECKS:
        issues.extend(check(dev, body))
    return issues


def main():
    text = get_lspci_output()
    devices = parse_devices(text)

    total_issues = 0
    for dev in devices:
        issues = check_device(dev)
        if not issues:
            continue
        total_issues += len(issues)
        print(f"{dev['bdf']}  {dev['desc']}")
        for issue in issues:
            print(f"  - {issue}")

    if total_issues == 0:
        print(f"scanned {len(devices)} devices, no anomalies found")
    else:
        print(f"\n{total_issues} anomalies across {len(devices)} devices")


if __name__ == "__main__":
    main()
