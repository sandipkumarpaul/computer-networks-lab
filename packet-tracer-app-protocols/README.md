# Packet Tracer: HTTP, SMTP and POP3

This part uses **simulation mode** in Cisco Packet Tracer to follow application-layer traffic step by step. The network has client PCs, two switches, a web server and an email server, with DNS for name resolution. For each exchange, the event list was filtered to one protocol and each PDU was opened to inspect it layer by layer (OSI model view, and inbound/outbound PDU details).

## 1. HTTP: loading a web page

A PC opens the browser and requests the campus website.

| # | Event | What it does |
|---|---|---|
| 1 | DNS query/response | Resolves the site's domain name to the web server's IP address |
| 2 | ARP request/reply | Resolves that IP (or the next hop) to a MAC address so the first Ethernet frame can be addressed |
| 3 | **HTTP request** (PC → switch) | An HTTP **GET**. The inbound PDU details end with the raw request line `GET / HTTP/1.1` and a `Host:` header naming the site |
| 4 | **HTTP response** (server → switch) | Starts with `HTTP/1.1 200 OK` and carries the page's HTML, which the PC's browser then renders |

## 2. SMTP: sending an email

The sending PC composes a message in its email client and clicks *Send*. The event list is filtered to DNS and SMTP.

| # | Event | What it does |
|---|---|---|
| 1 | DNS | Resolves the mail server's domain name to its IP, so the SMTP client knows where to connect |
| 2 | **SMTP** client → server | The client **pushes** the message to its mail server |
| 3 | **SMTP** server → client | The server confirms it received and accepted the message. SMTP replies are three-digit status codes; `250` means OK |

## 3. POP3: receiving the email

The receiving PC clicks *Receive* in its email client. The event list is filtered to DNS and POP3.

| # | Event | What it does |
|---|---|---|
| 1 | DNS | Resolves the POP3 server's domain name to its IP |
| 2 | **POP3** client → server | The client asks to **retrieve** the messages waiting in its mailbox |
| 3 | **POP3** server → client | The server returns the stored messages. POP3 replies start with `+OK` or `-ERR` |

## Takeaways

| Protocol | Transport | Model | Used for |
|---|---|---|---|
| HTTP | TCP 80 | Request/response, client pulls | Fetching web resources |
| SMTP | TCP 25 | Client **pushes** to server | Sending mail (client → server, server → server) |
| POP3 | TCP 110 | Client **pulls** from server | Downloading mail from a mailbox |
| DNS | UDP 53 | Query/response | Name → IP, before each exchange |
| ARP | Link layer | Broadcast request, unicast reply | IP → MAC, before the first frame on the LAN |

- **Every application exchange starts with resolution.** DNS turns a name into an IP, and ARP turns an IP into a MAC, before any HTTP, SMTP or POP3 data moves.
- **Sending and receiving mail use different protocols.** The sender never talks to the recipient directly. SMTP drops the message at the mail server, which stores it until the recipient pulls it with POP3. That asymmetry is why email works when the recipient is offline.
