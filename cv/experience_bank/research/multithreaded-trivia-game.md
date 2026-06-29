---
category: research
title: Multithreaded Client–Server Trivia Game
org: Ben-Gurion University (Data Networking course)
dates: "2024"
tags: [software-engineering, concurrency, multithreading, client-server, sockets, tcp, udp, networking, python, oop, distributed-systems, synchronization, fault-tolerance]
priority: 1
---

## One-line summary
Built a multithreaded client–server trivia game in Python over TCP/UDP, synchronizing concurrent players with locks, events, and barriers.

## Full description
Designed and implemented a real-time, multi-player trivia game as a networked client–server system in Python. The server advertises games over a UDP broadcast, accepts multiple TCP client connections, and handles each connected player in its own thread. Used locks, events, and barriers to coordinate shared game state safely across threads, and handled a wide range of network and timing exceptions (disconnects, timeouts, race conditions). Includes a bot client that plays automatically, and a clean object-oriented split across server, client, question-manager, statistics, and input components.

## Variations

**Short**
Multithreaded TCP/UDP client–server trivia game in Python, with one thread per player synchronized via locks, events, and barriers.

**Medium**
Implemented a real-time multiplayer trivia game as a Python client–server system: UDP broadcast for discovery, TCP for play, one thread per connected client, and locks/events/barriers to keep shared game state consistent. Handled disconnects, timeouts, and race conditions defensively, with a bot client for automated play.

**Long**
Designed and built a real-time multiplayer trivia game as a networked client–server system in Python. The server advertises games over UDP broadcast, accepts concurrent TCP client connections, and handles each player on a dedicated thread, using locks, events, and barriers to keep shared game state consistent. Engineered defensive handling of network faults (disconnects, timeouts, races) and structured the code into clear object-oriented components (server, client, bot, question manager, statistics, timed input).

## Technologies
Python, sockets (TCP/UDP), threading, locks/events/barriers, object-oriented design

## Outcomes
- Working multiplayer game supporting concurrent clients plus an automated bot client
- Robust handling of network faults (disconnects, timeouts) and thread races
- Demonstrates concurrency, networked services, and OOD — directly relevant to distributed/scalable systems
