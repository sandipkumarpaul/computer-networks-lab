#!/usr/bin/env python3
"""
Run udp_echo_flowmon.py once per packet size and collect all flows in one CSV.

Run from inside the ns-3 shell (./ns3 shell), then plot with plot_results.py:

    python3 sweep.py
    python3 sweep.py --sizes 64 128 256 512 1024 1472 1473 2048 4096
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIMULATION = os.path.join(HERE, "udp_echo_flowmon.py")
DEFAULT_CSV = os.path.join(HERE, "results", "packet_size_sweep.csv")


def main():
    parser = argparse.ArgumentParser(description="Packet-size sweep for udp_echo_flowmon.py")
    parser.add_argument("--sizes", type=int, nargs="+", default=[128, 256, 512, 1024, 2048],
                        help="UDP payload sizes in bytes (default: 128 256 512 1024 2048)")
    parser.add_argument("--csv", default=DEFAULT_CSV,
                        help="output CSV (overwritten; default: results/packet_size_sweep.csv)")
    args = parser.parse_args()

    if os.path.exists(args.csv):
        os.remove(args.csv)

    # One process per run: ns-3 keeps global simulator state, so separate
    # interpreters guarantee every run starts from a clean slate.
    for size in args.sizes:
        print("=== packet size %d bytes ===" % size, flush=True)
        subprocess.run([sys.executable, SIMULATION,
                        "--packet-size", str(size), "--csv", args.csv], check=True)

    print("\nResults written to %s" % args.csv)


if __name__ == "__main__":
    main()
