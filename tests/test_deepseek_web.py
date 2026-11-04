import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

from deepseek_web import DeepSeekWeb, DeepSeekWebError, search_query
from models import ResearchRequest
from research import read_deepseek_page, research


class OfficialWebTests(unittest.TestCase):
    def test_search_contract_and_filtering(self):
        calls = []
        def respond(request):
            calls.append(request)
            return httpx.Response(200, json={"results": [
                {"url": "https://example.edu/course", "title": "Course", "snippet": "Discovery only",
                 "summary": "Deadline not verified", "content": "Never use search content as page evidence",
                 "rerank_score": 2.4, "authority": 3, "date": "2026-10-17"},
                {"url": "https://example.edu/course"}, {"url": "javascript:alert(1)"}, None]})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            hits = DeepSeekWeb(client, "request-secret").search("summer school", original_question="HKU " * 100)
        body = json.loads(calls[0].content)
        self.assertEqual(str(calls[0].url), "https://api.deepseek.com/v1/tools/search")
        self.assertEqual(calls[0].headers["authorization"], "Bearer request-secret")
        self.assertFalse(body["need_content"])
        self.assertEqual(body["count"], 8)
        self.assertLessEqual(len(body["ori_question"]), 128)
        self.assertEqual(len(hits), 1)
        self.assertNotIn("content", hits[0])

    def test_long_queries_keep_site_operator_and_unicode_limit(self):
        query = search_query("暑校材料 " * 80 + " site:example.edu after:2026")
        self.assertLessEqual(len(query), 128)
        self.assertTrue(query.startswith("site:example.edu after:2026"))
        with self.assertRaises(ValueError):
            search_query("  \t ")

    def test_transient_retry_does_not_forward_key_to_redirect(self):
        calls = []
        def respond(request):
            calls.append(request)
            return httpx.Response(429 if len(calls) == 1 else 200,
                json={"results": []}, headers={"location": "https://untrusted.example/"})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch("deepseek_web.time.sleep"):
            web = DeepSeekWeb(client, "private-key")
            self.assertEqual(web.search("test"), [])
            self.assertEqual(web.calls["search"], 2)
        self.assertTrue(all(r.url.host == "api.deepseek.com" for r in calls))

    def test_auth_and_balance_errors_are_fatal_sanitized_and_not_retried(self):
        for status in (401, 402):
            calls = []
            def respond(request):
                calls.append(request)
                return httpx.Response(status, json={"error": {"message": "echo secret-key"}})
            with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                with self.assertRaises(DeepSeekWebError) as error:
                    DeepSeekWeb(client, "secret-key").search("test")
            self.assertTrue(error.exception.fatal)
            self.assertNotIn("secret-key", str(error.exception))
            self.assertEqual(len(calls), 1)

    def test_budget_limits_include_retries_and_operations_are_independent(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200,
                json={"results": [], "content": "body"}))) as client:
            web = DeepSeekWeb(client, "key", max_search=1, max_fetch=1)
            web.search("test")
            with self.assertRaises(DeepSeekWebError):
                web.search("test again")
            self.assertEqual(web.fetch("https://example.edu")["content"], "body")
            self.assertEqual(web.calls, {"search": 1, "fetch": 1})

    def test_fetch_markdown_provenance_links_and_evidence_body(self):
        content = "# Course\nApplications close on 1 March 2027. " + "Official eligibility and documents. " * 8
        content += "[Apply](/apply) [Guide](https://example.edu/guide.pdf)"
        with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200,
                json={"title": "Official course", "content": content}))) as client, patch(
                "research.safe_public_url", side_effect=lambda u: u), patch("research.read_page") as direct:
            page = read_deepseek_page(client, DeepSeekWeb(client, "key"), "https://example.edu/course", "S1")
        direct.assert_not_called()
        self.assertEqual(page.source.publisher_type, "host")
        self.assertIn("DeepSeek Fetch", page.source.note)
        self.assertEqual(page.links["Apply"], "https://example.edu/apply")
        self.assertIn("applications close on 1 march 2027", page.text)

    def test_fetch_content_failure_falls_back_without_sending_key_to_website(self):
        calls = []
        def respond(request):
            calls.append(request)
            if request.url.host == "api.deepseek.com":
                return httpx.Response(404, json={"error": {"message": "unsupported page"}})
            self.assertNotIn("authorization", request.headers)
            return httpx.Response(200, text="<html><main>" + "Application details. " * 20 + "</main></html>",
                                  headers={"content-type": "text/html"})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch(
                "research.safe_public_url", side_effect=lambda u: u):
            page = read_deepseek_page(client, DeepSeekWeb(client, "key"), "https://example.edu/course", "S1")
        self.assertEqual(len(calls), 2)
        self.assertIn("Supplementary direct", page.source.note)

    def test_fetch_security_and_auth_rejections_do_not_fall_back(self):
        for status in (401, 402, 403):
            with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status))) as client, patch(
                    "research.safe_public_url", side_effect=lambda u: u), patch("research.read_page") as direct:
                with self.assertRaises(DeepSeekWebError):
                    read_deepseek_page(client, DeepSeekWeb(client, "key"), "https://example.edu/course", "S1")
            direct.assert_not_called()

    def test_known_login_stops_before_fetch_and_pdf_uses_existing_reader(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r: self.fail("Unexpected API call"))) as client, patch(
                "research.safe_public_url", side_effect=lambda u: u):
            web = DeepSeekWeb(client, "key")
            from research import LoginRequiredError, Page
            from models import Source
            from datetime import datetime, timezone
            with self.assertRaises(LoginRequiredError):
                read_deepseek_page(client, web, "https://example.edu/login", "S1")
            original = Page(source=Source(id="S1",url="https://example.edu/rules.pdf",title="Rules",
                publisher_type="host", retrieved_at=datetime.now(timezone.utc),read_status="read"),
                text="PDF original text",links={})
            with patch("research.read_page",return_value=original) as direct:
                page=read_deepseek_page(client,web,"https://example.edu/rules.pdf","S1")
            direct.assert_called_once()
            self.assertIn("direct PDF",page.source.note)

    def test_fetch_login_content_is_not_application_evidence(self):
        from research import LoginRequiredError
        with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200,
                json={"title":"Sign in", "content":"Enter your password to authenticate. " * 8}))) as client, patch(
                "research.safe_public_url", side_effect=lambda u:u), patch("research.read_page") as direct:
            with self.assertRaises(LoginRequiredError):
                read_deepseek_page(client,DeepSeekWeb(client,"key"),"https://example.edu/portal","S1")
        direct.assert_not_called()

    def test_native_pipeline_no_browser_and_no_summary_self_verification(self):
        api_requests, reads = [], []
        official_url = "https://example.edu/summer"
        text = "Apply online. Applications close on 1 March 2027. " + "Official summer programme 2027 details. " * 10
        def respond(request):
            self.assertEqual(request.url.host, "api.deepseek.com")
            data = json.loads(request.content)
            api_requests.append(data)
            if request.url.path.endswith("/search"):
                return httpx.Response(200,json={"results":[{"title":"Summer","url":official_url,
                    "snippet":"A search summary claim that is not in the page", "summary":"Discovery lead only"}]})
            reads.append(data["url"])
            return httpx.Response(200,json={"title":"Official programme","content":text})
        def reply(content=None, tools=None):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content,tool_calls=tools))])
        search_call = SimpleNamespace(id="search",function=SimpleNamespace(name="search_web",
            arguments=json.dumps({"query":"site:example.edu summer 2027"})))
        read_call = SimpleNamespace(id="read",function=SimpleNamespace(name="read_web",
            arguments=json.dumps({"url":official_url})))
        replies = iter([reply(tools=[search_call]),reply(tools=[read_call]),reply(json.dumps({"selected_urls":[official_url]})),
            reply(json.dumps({"programmes":[{"id":"p","name":"Summer","programme_type":"summer_school",
                "destination":"UK","official_url":official_url,"eligibility":[{"value":"Unverified claim",
                "evidence":[{"source_id":"S1","quote":"A search summary claim that is not in the page"}]}],
                "steps":[{"id":"apply","title":"Apply","category":"host_application","action":{"value":"Apply online",
                "evidence":[{"source_id":"S1","quote":"Apply online"}]}}]}]}))])
        fake_model=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:next(replies))))
        real_client=httpx.Client
        with patch("research.httpx.Client",side_effect=lambda **kw:real_client(transport=httpx.MockTransport(respond))), patch(
                "research.OpenAI",return_value=fake_model), patch("research.safe_public_url",side_effect=lambda u:u), patch(
                "research.browser_search_query",side_effect=AssertionError("Chromium must not run")), patch(
                "research.hku_catalog_search",side_effect=AssertionError("No legacy discovery")), patch(
                "research.request_knowledge",return_value=[]):
            result=research(ResearchRequest(destination="United Kingdom",start_date="2027-06-01",end_date="2027-08-31",
                programme_type="summer_school",max_programmes=1),provider="deepseek",api_key="request-key",search_backend="deepseek")
        self.assertIn("search:deepseek",result.provider)
        self.assertEqual(reads.count(official_url),1)  # agent read is reused by the extraction stage
        self.assertTrue(all(len(r["query"])<=128 for r in api_requests if "query" in r))
        self.assertEqual(result.programmes[0].eligibility[0].state,"needs_review")
        self.assertEqual(result.programmes[0].steps[0].action.state,"verified")
        self.assertTrue(all("DeepSeek" in (s.note or "") for s in result.sources))
