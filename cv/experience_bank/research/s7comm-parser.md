---
category: research
title: S7comm Industrial-Protocol Packet Parser
org: Personal project (industrial-control-systems context)
dates: "2025"
tags: [networking, protocols, ics, scada, plc, packet-parsing, cli, python, pandas, wireshark, debugging, systems, data-engineering]
priority: 2
---

## One-line summary
A command-line tool that extracts decoded sensor values from S7comm (PLC↔HMI) network captures using a sensor-to-memory address map.

## Full description
Built a command-line tool that parses S7comm protocol packets from industrial network captures (PCAP/PCAPNG) and decodes raw PLC memory into typed sensor values (Float, Boolean, Long, Word, Int, Byte) using a sensor-to-address mapping file. It drives tshark (Wireshark's command-line engine) to read captures, matches request/response PDUs by reference, computes byte and bit offsets within DB memory blocks, and supports time-range and packet-count filtering with configurable paths and CSV output. Useful for industrial-control-system (ICS) monitoring and offline analysis.

## Variations

**Short**
Python CLI that decodes typed sensor values from S7comm PLC network captures via a memory-address map and tshark.

**Medium**
Built a Python command-line tool that parses S7comm PLC/HMI packets from PCAP captures and decodes raw DB memory into typed sensor values using an address map. Matches request/response PDUs, handles bit/byte offsets, and supports time and packet filters with CSV output.

**Long**
Developed a command-line tool for industrial-control-system analysis that parses S7comm protocol packets from PCAP/PCAPNG captures and decodes raw PLC memory into typed sensor values (Float/Boolean/Long/Word/Int/Byte) from a sensor-to-address mapping. It invokes tshark to read captures, links request and response PDUs by reference, computes byte and bit offsets inside DB blocks, and offers time-range and packet-count filtering with configurable tshark paths and CSV output — turning raw industrial traffic into labeled sensor time series.

## Technologies
Python, pandas, tshark / Wireshark, argparse CLI, S7comm protocol, PCAP

## Outcomes
- Reusable CLI that turns raw ICS captures into labeled sensor time series
- Typed binary-memory decoding with correct bit/byte offset handling
- Protocol-level debugging and systems/networking depth
