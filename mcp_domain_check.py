import subprocess
import re
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="Domain Availability Checker")

# WHOIS servers per TLD
WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
    "io": "whois.nic.io",
    "co": "whois.nic.co",
    "dev": "whois.nic.google",
    "app": "whois.nic.google",
    "ai": "whois.nic.ai",
    "me": "whois.nic.me",
    "xyz": "whois.nic.xyz",
    "tech": "whois.nic.tech",
    "info": "whois.afilias.net",
    "biz": "whois.nic.biz",
    "us": "whois.nic.us",
}

NOT_FOUND_PATTERNS = re.compile(
    r"No match|NOT FOUND|No Data Found|Domain not found|"
    r"No entries found|is free|DOMAIN NOT FOUND|Status: AVAILABLE",
    re.IGNORECASE,
)


def _whois_lookup(domain: str) -> str:
    tld = domain.rsplit(".", 1)[-1].lower()
    server = WHOIS_SERVERS.get(tld)
    cmd = ["whois", "-h", server, domain] if server else ["whois", domain]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"


def _is_available(whois_output: str) -> bool:
    return bool(NOT_FOUND_PATTERNS.search(whois_output))


@mcp.tool()
def check_domain(domain: str) -> dict:
    """Check if a single domain name is available for registration.

    Args:
        domain: Full domain name to check (e.g. 'mybrand.com')

    Returns:
        dict with domain, available (bool), and status message
    """
    output = _whois_lookup(domain)
    if output == "TIMEOUT":
        return {"domain": domain, "available": None, "status": "timeout - try again"}
    available = _is_available(output)
    return {
        "domain": domain,
        "available": available,
        "status": "AVAILABLE" if available else "taken",
    }


@mcp.tool()
def check_domains_bulk(domains: List[str]) -> List[dict]:
    """Check availability of multiple domain names at once.

    Args:
        domains: List of full domain names (e.g. ['mybrand.com', 'mybrand.io'])

    Returns:
        List of dicts, each with domain, available (bool), and status
    """
    results = []
    for domain in domains:
        output = _whois_lookup(domain)
        if output == "TIMEOUT":
            results.append({"domain": domain, "available": None, "status": "timeout"})
        else:
            available = _is_available(output)
            results.append({
                "domain": domain,
                "available": available,
                "status": "AVAILABLE" if available else "taken",
            })
    return results


@mcp.tool()
def check_name_across_tlds(
    name: str,
    tlds: Optional[List[str]] = None,
) -> List[dict]:
    """Check a base name across multiple TLDs.

    Args:
        name: Base name without TLD (e.g. 'mybrand')
        tlds: List of TLDs to check (e.g. ['com', 'io', 'dev']).
              Defaults to com, net, org, io, co, dev, app, ai, me, xyz.

    Returns:
        List of dicts, each with domain, available (bool), and status
    """
    if tlds is None:
        tlds = ["com", "net", "org", "io", "co", "dev", "app", "ai", "me", "xyz"]
    domain_list = [f"{name}.{tld}" for tld in tlds]
    return check_domains_bulk(domain_list)


@mcp.tool()
def suggest_domains(
    keywords: List[str],
    tlds: Optional[List[str]] = None,
) -> List[dict]:
    """Generate domain name variations from keywords and check availability.

    Combines keywords with common patterns (hyphens, prefixes, suffixes)
    and checks which are available.

    Args:
        keywords: List of keywords to combine (e.g. ['smart', 'home'])
        tlds: TLDs to check. Defaults to ['com', 'io', 'dev', 'co'].

    Returns:
        List of available domain suggestions with domain and status
    """
    if tlds is None:
        tlds = ["com", "io", "dev", "co"]

    prefixes = ["get", "try", "use", "go", "my", "the"]
    suffixes = ["app", "hub", "lab", "hq", "ly", "ify"]

    base = "".join(keywords)
    hyphenated = "-".join(keywords)

    candidates = set()
    candidates.add(base)
    candidates.add(hyphenated)
    for p in prefixes:
        candidates.add(f"{p}{base}")
    for s in suffixes:
        candidates.add(f"{base}{s}")
    # Two-keyword combos in both orders
    if len(keywords) >= 2:
        candidates.add(keywords[1] + keywords[0])

    domains = [f"{c}.{tld}" for c in candidates for tld in tlds]
    results = check_domains_bulk(domains)
    return [r for r in results if r["available"]]


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8083
    mcp.run(transport="streamable-http")
