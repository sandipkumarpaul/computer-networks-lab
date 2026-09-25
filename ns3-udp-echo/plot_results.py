#!/usr/bin/env python3
"""
Plot delay and throughput against packet size from a sweep CSV, alongside an
analytical model of the 5 Mbps / 2 ms point-to-point link.

Needs only matplotlib (not ns-3):

    python3 plot_results.py
    python3 plot_results.py --csv results/packet_size_sweep.csv --out results/packet_size_sweep.png
"""

import argparse
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ECHO_PORT = 9  # client -> server flow is the one addressed to the echo port

# Link and protocol constants used by the simulation.
DATA_RATE_BPS = 5e6
PROP_DELAY_S = 2e-3
MTU = 1500          # PointToPointNetDevice default
IP_HEADER = 20
UDP_HEADER = 8
PPP_HEADER = 2      # added per frame by PointToPointNetDevice


def model(payload):
    """Expected one-way delay (s) and throughput (bit/s) for a single UDP packet."""
    ip_payload = payload + UDP_HEADER
    fragments = math.ceil(ip_payload / (MTU - IP_HEADER))
    bytes_on_wire = ip_payload + fragments * (IP_HEADER + PPP_HEADER)
    delay = bytes_on_wire * 8 / DATA_RATE_BPS + PROP_DELAY_S
    # FlowMonitor counts the reassembled IP packet (one IP header).
    return delay, (ip_payload + IP_HEADER) * 8 / delay


def load_request_flows(path):
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if int(r["dst_port"]) == ECHO_PORT]
    rows.sort(key=lambda r: int(r["packet_size"]))
    sizes = [int(r["packet_size"]) for r in rows]
    delays_ms = [float(r["mean_delay_s"]) * 1e3 for r in rows]
    throughput_mbps = [float(r["throughput_bps"]) / 1e6 for r in rows]
    return sizes, delays_ms, throughput_mbps


def main():
    parser = argparse.ArgumentParser(description="Plot a packet-size sweep")
    parser.add_argument("--csv", default=os.path.join(HERE, "results", "packet_size_sweep.csv"))
    parser.add_argument("--out", default=os.path.join(HERE, "results", "packet_size_sweep.png"))
    args = parser.parse_args()

    sizes, delays_ms, throughput_mbps = load_request_flows(args.csv)

    model_sizes = range(64, 4097, 8)
    model_points = [model(s) for s in model_sizes]
    model_delay_ms = [d * 1e3 for d, _ in model_points]
    model_tput_mbps = [t / 1e6 for _, t in model_points]

    fig, (ax_delay, ax_tput) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax_delay.plot(model_sizes, model_delay_ms, color="0.6", lw=1.5, label="Model")
    ax_delay.plot(sizes, delays_ms, "o", color="C0", ms=7, label="ns-3 FlowMonitor")
    ax_delay.axhline(PROP_DELAY_S * 1e3, color="0.3", ls=":", lw=1)
    ax_delay.text(70, PROP_DELAY_S * 1e3 - 0.45, "propagation delay (2 ms)", fontsize=8, color="0.3")
    ax_delay.set_ylim(0, max(model_delay_ms) * 1.05)
    ax_delay.set_ylabel("One-way delay (ms)")
    ax_delay.set_title("Delay vs packet size")

    ax_tput.plot(model_sizes, model_tput_mbps, color="0.6", lw=1.5, label="Model")
    ax_tput.plot(sizes, throughput_mbps, "o", color="C1", ms=7, label="ns-3 FlowMonitor")
    ax_tput.axhline(DATA_RATE_BPS / 1e6, color="0.3", ls="--", lw=1)
    ax_tput.text(70, DATA_RATE_BPS / 1e6 - 0.3, "link capacity (5 Mbps)", fontsize=8, color="0.3")
    ax_tput.set_ylabel("Throughput (Mbps)")
    ax_tput.set_ylim(0, DATA_RATE_BPS / 1e6 * 1.1)
    ax_tput.set_title("Throughput vs packet size")

    for ax in (ax_delay, ax_tput):
        ax.set_xscale("log", base=2)
        ax.set_xticks(sizes)
        ax.set_xticklabels([str(s) for s in sizes])
        ax.set_xlabel("UDP payload (bytes)")
        ax.axvline(MTU - IP_HEADER - UDP_HEADER, color="0.8", lw=1)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left" if ax is ax_delay else "lower right", fontsize=8)

    ax_delay.text(MTU - IP_HEADER - UDP_HEADER, ax_delay.get_ylim()[1], " IP fragmentation\n (> 1472 B)",
                  fontsize=8, color="0.45", va="top")

    fig.tight_layout()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print("Saved %s" % args.out)


if __name__ == "__main__":
    main()
