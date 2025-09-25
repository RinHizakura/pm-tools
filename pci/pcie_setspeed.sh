#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root user."
    exit 1
fi

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <dev> <speed>"
    exit 1
fi

dev=$1
speed=$2

lnk_cap=$(setpci -s $dev CAP_EXP+0c.L)
max_speed=$((0x$lnk_cap & 0xF))
lnk_sta=$(setpci -s $dev CAP_EXP+12.W)
cur_speed=$((0x$lnk_sta & 0xF))

echo "Max link speed:" $max_speed
echo "Current link speed:" $cur_speed

lnk_ctl2=$(setpci -s $dev CAP_EXP+30.L)
lnk_ctl2=$(printf "%08x" $(((0x$lnk_ctl2 & 0xFFFFFFF0) | $speed)))
setpci -s $dev CAP_EXP+30.L=$lnk_ctl2

lnk_ctl=$(setpci -s $dev CAP_EXP+10.L)
lnk_ctl=$(printf "%08x" $((0x$lnk_ctl | (1 << 5))))
setpci -s $dev CAP_EXP+10.L=$lnk_ctl

sleep 0.1

lnk_sta=$(setpci -s $dev CAP_EXP+12.W)
cur_speed=$((0x$lnk_sta & 0xF))
echo "New link speed:" $cur_speed
