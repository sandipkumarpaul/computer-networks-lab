#!/usr/bin/env python3
"""
Point-to-point UDP echo simulation with per-flow FlowMonitor statistics (ns-3).

    n0 10.1.1.1 ------ 5 Mbps / 2 ms ------ n1 10.1.1.2
    UDP echo client                         UDP echo server (port 9)

Extends the ns-3 tutorial script examples/tutorial/first.py with FlowMonitor
so that every flow reports bytes, packets, loss, mean delay and throughput.

Run from inside the ns-3 shell (ns-3.40, Python bindings enabled):

    ./ns3 shell
    python3 udp_echo_flowmon.py --packet-size 1024
    python3 udp_echo_flowmon.py --packet-size 512 --csv results/run.csv
"""

import argparse
import csv
import os

from ns import ns

ECHO_PORT = 9
PROTOCOLS = {6: "TCP", 17: "UDP"}
CSV_FIELDS = [
    "packet_size", "flow_id", "protocol",
    "src_addr", "src_port", "dst_addr", "dst_port",
    "tx_bytes", "rx_bytes", "tx_packets", "rx_packets", "lost_packets",
    "mean_delay_s", "throughput_bps",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="ns-3 point-to-point UDP echo simulation with FlowMonitor stats")
    parser.add_argument("--packet-size", type=int, default=1024,
                        help="UDP payload size in bytes (default: 1024)")
    parser.add_argument("--packets", type=int, default=1,
                        help="number of echo requests the client sends (default: 1)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="seconds between echo requests (default: 1.0)")
    parser.add_argument("--data-rate", default="5Mbps",
                        help="link data rate (default: 5Mbps)")
    parser.add_argument("--delay", default="2ms",
                        help="link propagation delay (default: 2ms)")
    parser.add_argument("--csv", metavar="PATH",
                        help="append one row per flow to this CSV file")
    return parser.parse_args()


def flow_metrics(stats):
    """Mean one-way delay (s) and throughput (bit/s) of a flow, or None if nothing arrived."""
    if stats.rxPackets == 0:
        return None, None
    mean_delay = stats.delaySum.GetSeconds() / stats.rxPackets
    # Throughput over the flow's active time (first packet sent -> last packet
    # received), not over a fixed window, so it reflects what the link delivered.
    duration = stats.timeLastRxPacket.GetSeconds() - stats.timeFirstTxPacket.GetSeconds()
    throughput = stats.rxBytes * 8 / duration if duration > 0 else None
    return mean_delay, throughput


def append_csv(path, rows):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()

    ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
    ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)

    # Topology: two nodes joined by a point-to-point link.
    nodes = ns.network.NodeContainer()
    nodes.Create(2)

    point_to_point = ns.point_to_point.PointToPointHelper()
    point_to_point.SetDeviceAttribute("DataRate", ns.core.StringValue(args.data_rate))
    point_to_point.SetChannelAttribute("Delay", ns.core.StringValue(args.delay))
    devices = point_to_point.Install(nodes)

    stack = ns.internet.InternetStackHelper()
    stack.Install(nodes)

    address = ns.internet.Ipv4AddressHelper()
    address.SetBase(ns.network.Ipv4Address("10.1.1.0"),
                    ns.network.Ipv4Mask("255.255.255.0"))
    interfaces = address.Assign(devices)

    # Applications: echo server on n1, echo client on n0.
    echo_server = ns.applications.UdpEchoServerHelper(ECHO_PORT)
    server_apps = echo_server.Install(nodes.Get(1))
    server_apps.Start(ns.core.Seconds(1.0))
    server_apps.Stop(ns.core.Seconds(10.0))

    server_address = interfaces.GetAddress(1).ConvertTo()
    echo_client = ns.applications.UdpEchoClientHelper(server_address, ECHO_PORT)
    echo_client.SetAttribute("MaxPackets", ns.core.UintegerValue(args.packets))
    echo_client.SetAttribute("Interval", ns.core.TimeValue(ns.core.Seconds(args.interval)))
    echo_client.SetAttribute("PacketSize", ns.core.UintegerValue(args.packet_size))

    client_apps = echo_client.Install(nodes.Get(0))
    client_apps.Start(ns.core.Seconds(2.0))
    client_apps.Stop(ns.core.Seconds(10.0))

    flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
    monitor = flowmon_helper.InstallAll()

    ns.core.Simulator.Stop(ns.core.Seconds(20.0))
    ns.core.Simulator.Run()

    monitor.CheckForLostPackets()
    classifier = flowmon_helper.GetClassifier()

    rows = []
    for flow_id, stats in monitor.GetFlowStats():
        t = classifier.FindFlow(flow_id)
        proto = PROTOCOLS.get(t.protocol, str(t.protocol))
        mean_delay, throughput = flow_metrics(stats)

        print("FlowID: %i (%s %s/%s --> %s/%s)" % (
            flow_id, proto, t.sourceAddress, t.sourcePort,
            t.destinationAddress, t.destinationPort))
        print("  Tx Bytes:     ", stats.txBytes)
        print("  Rx Bytes:     ", stats.rxBytes)
        print("  Tx Packets:   ", stats.txPackets)
        print("  Rx Packets:   ", stats.rxPackets)
        print("  Lost Packets: ", stats.lostPackets)
        if mean_delay is not None:
            print("  Mean Delay:    %.7f s" % mean_delay)
        if throughput is not None:
            print("  Throughput:    %.3f kbps" % (throughput / 1e3))

        rows.append({
            "packet_size": args.packet_size,
            "flow_id": flow_id,
            "protocol": proto,
            "src_addr": str(t.sourceAddress),
            "src_port": t.sourcePort,
            "dst_addr": str(t.destinationAddress),
            "dst_port": t.destinationPort,
            "tx_bytes": stats.txBytes,
            "rx_bytes": stats.rxBytes,
            "tx_packets": stats.txPackets,
            "rx_packets": stats.rxPackets,
            "lost_packets": stats.lostPackets,
            "mean_delay_s": "" if mean_delay is None else "%.9f" % mean_delay,
            "throughput_bps": "" if throughput is None else "%.2f" % throughput,
        })

    if args.csv:
        append_csv(args.csv, rows)

    ns.core.Simulator.Destroy()


if __name__ == "__main__":
    main()
