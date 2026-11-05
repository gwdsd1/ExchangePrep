import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import app
from models import ResearchResult, Draft
from research import research
from workflow import WorkflowRequest, plan_research


ROOT = Path(__file__).resolve().parent.parent


def settings():
    return WorkflowRequest(destination="United Kingdom", start_date="2028-06-01",
        end_date="2028-08-31", departure_date="2028-06-01", programme_type="summer_school")


def fixture():
    return ResearchResult.model_validate_json((ROOT / "sample.json").read_text(encoding="utf-8"))


class WorkflowTests(unittest.TestCase):
    def test_same_step_ids_in_different_programmes_and_unverified_dates(self):
        result = fixture()
        result.programmes.append(result.programmes[0].model_copy(deep=True))
        result.programmes[1].id = "second_programme"
        step = result.programmes[0].steps[0]
        step.deadline.kind = "fixed"
        step.deadline.date = "2027-01-01"
        step.deadline.state = "historical"
        output = plan_research(result, settings())
        self.assertEqual(len(output["plans"]), 2)
        first = next(e for e in output["plans"][0].entries if e.task_id == step.id)
        self.assertIsNone(first.deadline)
        self.assertTrue(any(c.kind == "unknown_deadline" for c in output["plans"][0].conflicts))
        self.assertTrue(first.sources[0].url.startswith("https://"))

    def test_earliest_schedule_respects_prerequisite_finishes(self):
        plan = plan_research(fixture(), settings())["plans"][0]
        entries = {e.task_id: e for e in plan.entries}
        for entry in plan.entries:
            if not entry.recommended_start:
                continue
            for previous in entry.prerequisites:
                predecessor = entries[previous]
                if predecessor.recommended_start:
                    delta = (entry.recommended_start - predecessor.recommended_start).days
                    self.assertGreaterEqual(delta, predecessor.duration_days)

    def test_sample_needs_no_key_and_produces_real_planner_output(self):
        response = TestClient(app).post("/api/workflow/sample", json=settings().model_dump(mode="json"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["plans"][0]["entries"])
        self.assertIn("offline", response.json()["research"]["provider"])

    def test_concurrent_keys_do_not_mutate_environment_or_export_credentials(self):
        before = dict(os.environ)
        seen = []
        def fake(request, **kwargs):
            seen.append(kwargs["api_key"])
            return fixture()
        def submit(key):
            return TestClient(app).post("/api/workflow", headers={"X-API-Key": key},
                json=settings().model_dump(mode="json"))
        with patch("app.research", side_effect=fake), ThreadPoolExecutor() as pool:
            responses = list(pool.map(submit, ["test-key-one", "test-key-two"]))
        self.assertCountEqual(seen, ["test-key-one", "test-key-two"])
        self.assertEqual(dict(os.environ), before)
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("test-key", response.text)

    def test_failures_do_not_echo_key_and_foreign_origin_rejected(self):
        client = TestClient(app)
        data = settings().model_dump(mode="json")
        with patch("app.research", side_effect=RuntimeError("secret-test-key")):
            response = client.post("/api/workflow", headers={"X-API-Key": "secret-test-key"}, json=data)
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-test-key", response.text)
        response = client.post("/api/workflow", headers={"Origin": "https://foreign.test",
            "X-API-Key": "secret-test-key"}, json=data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(client.post("/api/workflow", json=data).status_code, 400)

    def test_web_provider_dispatch_preserves_openai_and_selects_official_deepseek(self):
        client = TestClient(app)
        for provider, backend in [("deepseek", "deepseek"), ("openai", "openai")]:
            data = settings().model_dump(mode="json")
            data["provider"] = provider
            with patch("app.research", return_value=fixture()) as model:
                response = client.post("/api/workflow", json=data, headers={"X-API-Key":"request-key"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(model.call_args.kwargs["search_backend"], backend)
            self.assertEqual(model.call_args.kwargs["provider"], provider)

    def test_english_sample_and_cross_origin_async_job(self):
        import time
        client=TestClient(app)
        data=settings().model_dump(mode="json")
        data["language"]="en"
        response=client.post("/api/workflow/sample",json=data)
        self.assertEqual(response.status_code,200)
        self.assertIn("Suggested start:",response.json()["markdown"])
        self.assertNotIn("用户",response.json()["assumptions"]["note"])
        origin="https://gwdsd1.github.io"
        response=client.options("/api/workflow/jobs",headers={"Origin":origin,
            "Access-Control-Request-Method":"POST","Access-Control-Request-Headers":"content-type,x-api-key"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers["access-control-allow-origin"],origin)
        with patch("app.research",return_value=fixture()) as model:
            response=client.post("/api/workflow/jobs",headers={"Origin":origin,"X-API-Key":"one-request-key"},json=data)
            self.assertEqual(response.status_code,202)
            job_id=response.json()["job_id"]
            for _ in range(100):
                result=client.get("/api/workflow/jobs/"+job_id)
                if result.json()["status"]!="running":break
                time.sleep(.02)
            self.assertEqual(result.json()["status"],"complete")
            self.assertEqual(model.call_args.args[0].language,"en")
            self.assertNotIn("one-request-key",result.text)
            self.assertEqual(result.headers["cache-control"],"no-store")

    def test_explicit_openai_key_is_used_for_discovery_and_extraction(self):
        request = settings()
        captured = []
        with patch.dict(os.environ, {"OPENAI_API_KEY": "environment-key"}), patch(
                "research.openai_search", return_value=[]) as search, patch(
                "research.read_page", side_effect=ValueError("offline test")), patch(
                "research.extract_with_ai", side_effect=lambda r,p,provider,model,key:
                    captured.append((model,key)) or Draft()), patch("research.openai_search_query", return_value=[]) as refill:
            research(request, provider="openai", api_key="request-key", model="test-model",
                     search_backend="openai")
        self.assertEqual(search.call_args.args[1:], ("request-key", "test-model"))
        self.assertEqual(captured, [("test-model", "request-key")])
        self.assertTrue(all(call.args[1:] == ("request-key", "test-model") for call in refill.call_args_list))


if __name__ == "__main__":
    unittest.main()
