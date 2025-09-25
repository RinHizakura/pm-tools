#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root user."
    exit 1
fi

XHCI_PATH=/sys/kernel/debug/usb/xhci

for xhci in $XHCI_PATH/*; do
    controller=`basename $xhci`
    map=("" "" "" "" "" "" "" "" "" "")

    if [ -z "$( ls -A $xhci/devices/ )" ]; then
        continue
    fi

    for d in $xhci/devices/*; do
        dev=`cat $d/name`
        product=`cat /sys/bus/usb/devices/$dev/product`
        port=`cat $d/slot-context | grep -oE "Port# [0-9]+/" | grep -oE "[0-9]+"`
        port=`expr $port + 0`
        map[$port]+="$dev($product) "
    done

    for d in $xhci/ports/*; do
        port=`basename $d | grep -oE "[0-9]+"`
        port=`expr $port + 0`
        devs=${map[$port]}
        if [ "$devs" = "" ]; then
            continue
        fi
        echo $controller, Port $port: $devs
        cat $d/portsc | xargs echo -e "\t"
    done
done
