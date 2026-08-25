"""Unit tests for tool schemas, docstrings, and guided error handling."""

from __future__ import annotations

import unittest
from src.tools.telemetry_logs import FetchTelemetryLogsTool
from src.tools.service_metrics import QueryServiceMetricsTool
from src.tools.runbook_search import SearchRunbookTool
from src.tools.remediation import ExecuteServiceRemediationTool


class TestToolsSuite(unittest.TestCase):
    """Test cases verifying Tool & Interface Design criteria."""

    def test_tool_docstrings_and_naming(self):
        tools = [
            FetchTelemetryLogsTool(),
            QueryServiceMetricsTool(),
            SearchRunbookTool(),
            ExecuteServiceRemediationTool(),
        ]
        for t in tools:
            self.assertTrue(len(t.name) > 5, f"Tool {t} has a non-descriptive name")
            self.assertTrue(len(t.description) > 20, f"Tool {t.name} has insufficient docstring description")
            self.assertIsNotNone(t.get_json_schema(), f"Tool {t.name} missing JSON schema")

    def test_guided_error_handling_on_invalid_service(self):
        log_tool = FetchTelemetryLogsTool()
        res = log_tool.run({"service_name": "non-existent-cluster-service"})
        
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "ServiceLogExtractionError")
        self.assertIn("recovery_suggestion", res)
        self.assertIn("valid_alternatives", res)
        self.assertIn("checkout-service", res["valid_alternatives"])

    def test_guided_error_handling_on_invalid_metric(self):
        metric_tool = QueryServiceMetricsTool()
        res = metric_tool.run({
            "service_name": "checkout-service",
            "metric_names": ["invalid_custom_metric_xyz"],
        })
        
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["error_code"], "MetricQueryError")
        self.assertIn("recovery_suggestion", res)

    def test_successful_runbook_search(self):
        rb_tool = SearchRunbookTool()
        res = rb_tool.run({"query": "OutOfMemory heap crash"})
        
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreater(res["results_found"], 0)
        self.assertIn("JVM Heap", res["runbooks"][0]["title"])


if __name__ == "__main__":
    unittest.main()
