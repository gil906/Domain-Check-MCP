import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import mcp_domain_check as server


class DomainCheckTests(unittest.TestCase):
    def test_available_domain_and_registry_selection(self):
        response = SimpleNamespace(stdout="Domain not found", stderr="")
        with patch.object(server.subprocess, "run", return_value=response) as run:
            result = server.check_domain("example.dev")
        self.assertEqual(result, {
            "domain": "example.dev", "available": True, "status": "AVAILABLE",
        })
        run.assert_called_once_with(
            ["whois", "-h", "whois.nic.google", "example.dev"],
            capture_output=True, text=True, timeout=10,
        )

    def test_taken_domain(self):
        with patch.object(server, "_whois_lookup", return_value="Domain Name: EXAMPLE.COM"):
            result = server.check_domain("example.com")
        self.assertEqual(result, {
            "domain": "example.com", "available": False, "status": "taken",
        })

    def test_timeout(self):
        with patch.object(
            server.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["whois"], timeout=10),
        ):
            result = server.check_domain("example.com")
        self.assertEqual(result, {
            "domain": "example.com", "available": None,
            "status": "timeout - try again",
        })

    def test_unknown_tld_uses_system_whois(self):
        response = SimpleNamespace(stdout="", stderr="No match")
        with patch.object(server.subprocess, "run", return_value=response) as run:
            result = server.check_domain("example.test")
        self.assertTrue(result["available"])
        self.assertEqual(run.call_args.args[0], ["whois", "example.test"])

    def test_bulk_preserves_order_and_statuses(self):
        with patch.object(
            server, "_whois_lookup",
            side_effect=["No match", "Domain Name: EXAMPLE.NET", "TIMEOUT"],
        ):
            results = server.check_domains_bulk(
                ["example.com", "example.net", "example.org"],
            )
        self.assertEqual(results, [
            {"domain": "example.com", "available": True, "status": "AVAILABLE"},
            {"domain": "example.net", "available": False, "status": "taken"},
            {"domain": "example.org", "available": None, "status": "timeout"},
        ])

    def test_across_tlds_defaults_and_explicit_selection(self):
        with patch.object(server, "check_domains_bulk", return_value=[]) as bulk:
            server.check_name_across_tlds("example")
            bulk.assert_called_with([
                f"example.{tld}"
                for tld in ["com", "net", "org", "io", "co", "dev", "app", "ai", "me", "xyz"]
            ])
            server.check_name_across_tlds("example", ["com", "net"])
            bulk.assert_called_with(["example.com", "example.net"])
            server.check_name_across_tlds("example", [])
            bulk.assert_called_with([])

    def test_suggestions_generate_variations_and_filter_results(self):
        results = [
            {"domain": "samplebrand.com", "available": True, "status": "AVAILABLE"},
            {"domain": "sample-brand.com", "available": False, "status": "taken"},
            {"domain": "getsamplebrand.com", "available": None, "status": "timeout"},
        ]
        with patch.object(server, "check_domains_bulk", return_value=results) as bulk:
            suggestions = server.suggest_domains(["sample", "brand"], ["com"])
        candidates = set(bulk.call_args.args[0])
        self.assertTrue({
            "samplebrand.com", "sample-brand.com", "brandsample.com",
            "getsamplebrand.com", "samplebrandhub.com",
        }.issubset(candidates))
        self.assertTrue(all(domain.endswith(".com") for domain in candidates))
        self.assertEqual(suggestions, [results[0]])

    def test_suggestions_with_empty_tlds(self):
        with patch.object(server, "check_domains_bulk", return_value=[]) as bulk:
            self.assertEqual(server.suggest_domains(["sample"], []), [])
        bulk.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
