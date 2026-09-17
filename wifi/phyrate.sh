#!/usr/bin/env bash

# Computes the theoretical 802.11 PHY rate for a WiFi interface's current
# connection, across legacy (a/b/g), HT (n), VHT (ac), HE (ax) and EHT (be).
#
#   rate_Mbps = NSS * (Nsd * bits_per_subcarrier * code_rate) / Tsym_us
#
# Usage: phyrate.sh <iface>
#   The interface must be currently associated to an AP/hotspot.

# bits-per-subcarrier * code-rate, indexed by MCS 0-13.
# 0-9 shared by HT/VHT/HE/EHT, 10-11 add HE/EHT 1024-QAM, 12-13 add EHT 4096-QAM.
BPSCR=(0.5 1.0 1.5 2.0 3.0 4.0 4.5 5.0 6.0 6.666667 7.5 8.333333 9.0 10.0)
# BPSCR[mcs] = MOD_BITS[mcs] (bits/symbol, i.e. log2(modulation order)) * CR_LABEL[mcs] (FEC code rate)
MOD_NAME=(BPSK QPSK QPSK 16-QAM 16-QAM 64-QAM 64-QAM 64-QAM 256-QAM 256-QAM 1024-QAM 1024-QAM 4096-QAM 4096-QAM)
MOD_BITS=(1 2 2 4 4 6 6 6 8 8 10 10 12 12)
CR_LABEL=("1/2" "1/2" "3/4" "1/2" "3/4" "2/3" "3/4" "5/6" "3/4" "5/6" "3/4" "5/6" "3/4" "5/6")

# HT/VHT use a 64/128/256/512-point FFT (Nsd fewer); HE/EHT use a 4x denser
# 256/512/1024/2048/4096-point FFT for the same channel widths.
nsd_for_width() {
	local width="$1" gen="$2"
	case "$gen" in
	ht_vht)
		case "$width" in
		20) echo 52 ;; 40) echo 108 ;; 80) echo 234 ;; 160) echo 468 ;;
		*) echo "" ;;
		esac
		;;
	he_eht)
		case "$width" in
		20) echo 234 ;; 40) echo 468 ;; 80) echo 980 ;; 160) echo 1960 ;; 320) echo 3920 ;;
		*) echo "" ;;
		esac
		;;
	esac
}

# Symbol duration in us: HT/VHT use a 3.2us FFT + GI; HE/EHT use a 12.8us FFT + GI.
tsym_for_gi() {
	local gen="$1" gi="$2"
	case "$gen" in
	ht_vht)
		case "$gi" in
		long) echo 4.0 ;; short) echo 3.6 ;;
		esac
		;;
	he_eht)
		case "$gi" in
		0.8) echo 13.6 ;; 1.6) echo 14.4 ;; 3.2) echo 16.0 ;;
		esac
		;;
	esac
}

calc_rate() {
	local mcs="$1" nss="$2" width="$3" gi="$4" gen="$5" nsd tsym bpscr
	nsd=$(nsd_for_width "$width" "$gen")
	[ -n "$nsd" ] || { echo ""; return; }
	bpscr="${BPSCR[$mcs]}"
	[ -n "$bpscr" ] || { echo ""; return; }
	tsym=$(tsym_for_gi "$gen" "$gi")
	[ -n "$tsym" ] || { echo ""; return; }
	awk -v nss="$nss" -v nsd="$nsd" -v bpscr="$bpscr" -v tsym="$tsym" \
		'BEGIN { printf "%.1f", nss * (nsd * bpscr) / tsym }'
}

# rate_vs_base RATE BASE -> "RATE Mbps (xN.NN)"
rate_vs_base() {
	awk -v rate="$1" -v base="$2" 'BEGIN { printf "%.1f Mbps (x%.2f)", rate, rate / base }'
}

iface="${1:-}"
if [ -z "$iface" ] || [ ! -d "/sys/class/net/${iface}" ]; then
	echo "Usage: $0 <wifi-iface>" >&2
	exit 1
fi

link=$(iw dev "$iface" link 2>/dev/null)
if ! echo "$link" | grep -q "^Connected"; then
	echo "Error: ${iface} is not connected" >&2
	exit 1
fi

rate_line=$(echo "$link" | grep "tx bitrate" | head -1)
live_mbps=$(echo "$rate_line" | grep -oE '^[[:space:]]*tx bitrate: [0-9.]+' | grep -oE '[0-9.]+$')

gi_labels=""
if echo "$rate_line" | grep -q "EHT-MCS"; then
	standard="EHT (802.11be)"
	gen="he_eht"
	mcs=$(echo "$rate_line" | grep -oE 'EHT-MCS [0-9]+' | grep -oE '[0-9]+')
	nss=$(echo "$rate_line" | grep -oE 'EHT-NSS [0-9]+' | grep -oE '[0-9]+')
	gi_idx=$(echo "$rate_line" | grep -oE 'EHT-GI [0-9]+' | grep -oE '[0-9]+')
elif echo "$rate_line" | grep -q "HE-MCS"; then
	standard="HE (802.11ax)"
	gen="he_eht"
	mcs=$(echo "$rate_line" | grep -oE 'HE-MCS [0-9]+' | grep -oE '[0-9]+')
	nss=$(echo "$rate_line" | grep -oE 'HE-NSS [0-9]+' | grep -oE '[0-9]+')
	gi_idx=$(echo "$rate_line" | grep -oE 'HE-GI [0-9]+' | grep -oE '[0-9]+')
elif echo "$rate_line" | grep -q "VHT-MCS"; then
	standard="VHT (802.11ac)"
	gen="ht_vht"
	mcs=$(echo "$rate_line" | grep -oE 'VHT-MCS [0-9]+' | grep -oE '[0-9]+')
	nss=$(echo "$rate_line" | grep -oE 'VHT-NSS [0-9]+' | grep -oE '[0-9]+')
elif echo "$rate_line" | grep -qE '(^|[^A-Z-])MCS [0-9]+'; then
	standard="HT (802.11n)"
	gen="ht_vht"
	mcs_raw=$(echo "$rate_line" | grep -oE 'MCS [0-9]+' | grep -oE '[0-9]+')
	mcs=$((mcs_raw % 8))
	nss=$((mcs_raw / 8 + 1))
else
	standard="Legacy (802.11a/b/g)"
	echo "${iface}: ${standard} (live reported: ${live_mbps:-unknown} Mbps)"
	echo "Legacy rates are fixed per modulation; no HT/VHT/HE/EHT knobs apply."
	exit 0
fi

width=$(iw dev "$iface" info 2>/dev/null | grep -oE 'width: [0-9]+' | grep -oE '[0-9]+')

if [ -z "$mcs" ] || [ -z "$nss" ] || [ -z "$width" ]; then
	echo "Error: could not determine MCS/NSS/width from ${iface}'s current link" >&2
	exit 1
fi

# Resolve the guard interval actually in use.
if [ "$gen" = "he_eht" ]; then
	case "${gi_idx:-0}" in
	1) gi="1.6" ;; 2) gi="3.2" ;; *) gi="0.8" ;;
	esac
	gi_options=(0.8 1.6 3.2)
else
	gi="long"
	rate_short=$(calc_rate "$mcs" "$nss" "$width" "short" "$gen")
	[ -n "$live_mbps" ] && [ "$live_mbps" = "$rate_short" ] && gi="short"
	gi_options=(long short)
fi

base=$(calc_rate "$mcs" "$nss" "$width" "$gi" "$gen")
nsd=$(nsd_for_width "$width" "$gen")
tsym=$(tsym_for_gi "$gen" "$gi")

echo "raw iw output: ${rate_line# }"
echo
echo "${iface}: ${standard} MCS ${mcs}, NSS ${nss}, ${width}MHz, GI ${gi}${gi_idx+us} (live reported: ${live_mbps:-unknown} Mbps)"
echo "  MCS ${mcs} -> ${MOD_NAME[$mcs]} (${MOD_BITS[$mcs]} bits/symbol) x code rate ${CR_LABEL[$mcs]} = ${BPSCR[$mcs]} bits/subcarrier"
echo "  width ${width}MHz + ${standard} tone plan (${gen}) -> Nsd ${nsd} data subcarriers"
echo "  GI ${gi} + ${standard} symbol timing (${gen}) -> Tsym ${tsym}us (FFT + guard interval)"
echo "  rate = NSS(${nss}) * (Nsd(${nsd}) * bits/subcarrier(${BPSCR[$mcs]})) / Tsym(${tsym}us) = ${base} Mbps"
echo
echo "Theoretical PHY rate: ${base} Mbps"
echo
echo "Per-knob multiplier from this baseline (one change at a time):"

for g in "${gi_options[@]}"; do
	[ "$g" = "$gi" ] && continue
	r=$(calc_rate "$mcs" "$nss" "$width" "$g" "$gen")
	[ -n "$r" ] && echo "  GI ${gi} -> ${g}:      $(rate_vs_base "$r" "$base")"
done

width_options=(20 40 80 160)
[ "$gen" = "he_eht" ] && width_options=(20 40 80 160 320)
for w in "${width_options[@]}"; do
	[ "$w" -eq "$width" ] && continue
	r=$(calc_rate "$mcs" "$nss" "$w" "$gi" "$gen")
	[ -n "$r" ] && echo "  width ${width}MHz -> ${w}MHz: $(rate_vs_base "$r" "$base")"
done

for n in 1 2 3 4; do
	[ "$n" -eq "$nss" ] && continue
	r=$(calc_rate "$mcs" "$n" "$width" "$gi" "$gen")
	[ -n "$r" ] && echo "  NSS ${nss} -> ${n}:          $(rate_vs_base "$r" "$base")"
done

max_mcs=9
[ "$gen" = "he_eht" ] && max_mcs=11
[ "$standard" = "EHT (802.11be)" ] && max_mcs=13
for m in $(seq 0 "$max_mcs"); do
	[ "$m" -eq "$mcs" ] && continue
	[ "$m" -eq 9 ] && [ "$width" -eq 20 ] && [ "$gen" = "ht_vht" ] && continue # MCS9 invalid at 20MHz VHT
	r=$(calc_rate "$m" "$nss" "$width" "$gi" "$gen")
	[ -n "$r" ] && echo "  MCS ${mcs} -> ${m}:          $(rate_vs_base "$r" "$base")"
done
