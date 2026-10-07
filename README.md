# Domain Check MCP

A Python Model Context Protocol (MCP) server that checks domain availability
using WHOIS and generates domain name suggestions. It uses FastMCP with
Streamable HTTP transport.

## Run with Docker

```sh
docker build -t domain-check-mcp .
docker run --rm --name domain-check-mcp \
  -p 127.0.0.1:8083:8083 domain-check-mcp
```

Connect an MCP client to `http://127.0.0.1:8083/mcp`. This is an MCP protocol
endpoint, not a REST API or a web interface.

The application requires no API keys or personal configuration. WHOIS queries
require outbound network access, normally TCP port 43.

## Run locally

Use Python 3.11 and install the system `whois` utility. On Debian or Ubuntu:

```sh
sudo apt-get update
sudo apt-get install whois ca-certificates
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python mcp_domain_check.py
```

**Security:** The Python process listens on `0.0.0.0:8083` and has no built-in
authentication. The Docker example publishes only to loopback. Restrict access
with a firewall or authenticated reverse proxy; do not expose the server
directly to the public internet. Domain queries are sent to WHOIS services.

## Tools

| Tool | Arguments | Result |
|------|-----------|--------|
| `check_domain` | `domain: str` | One availability result |
| `check_domains_bulk` | `domains: list[str]` | Results for the supplied domains |
| `check_name_across_tlds` | `name: str`, optional `tlds: list[str]` | Results for a base name across TLDs |
| `suggest_domains` | `keywords: list[str]`, optional `tlds: list[str]` | Available keyword variations |

Across-TLD checks default to `com`, `net`, `org`, `io`, `co`, `dev`, `app`,
`ai`, `me`, and `xyz`. Suggestions default to `com`, `io`, `dev`, and `co`.
Pass an explicit TLD list to limit queries; an empty list performs no checks.

Each result contains `domain`, `available`, and `status`. `available` is
`true` or `false`, or `null` on timeout. For example:

```json
{"domain": "example.com", "available": false, "status": "taken"}
```

## Limitations

Availability is a **heuristic, not a registration guarantee**. The server
matches phrases in WHOIS output; unsupported servers, rate limits, connection
errors, or changed response formats can incorrectly report a domain as taken.
In particular, `.app`, `.dev`, and `.co` results can be unreliable. Confirm any
result with a registrar before making registration decisions.

Queries run sequentially with a 10-second timeout per domain. Suggestions can
take several minutes and their order is not stable. They omit unavailable and
timed-out results. Inputs are not normalized or validated; provide plain domain
names and TLDs, not URLs or WHOIS options.

## Tests

Tests mock WHOIS responses and require no network access:

```sh
python -m unittest -v
```

Or run them in the built image:

```sh
docker run --rm --network none \
  -v "$PWD/test_domain_check.py:/app/test_domain_check.py:ro" \
  domain-check-mcp python -m unittest -v
```
