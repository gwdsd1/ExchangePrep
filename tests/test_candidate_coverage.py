"""Coverage regressions: paid providers are mocked, reading/verification/ordering are exercised."""
from contextlib import ExitStack
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from models import CandidateReview, Draft, Evidence, Programme, ResearchRequest, Source
from research import Page, checked_candidate_reviews, research, verify_draft


class CandidateCoverageTests(unittest.TestCase):
    def request(self, count=3, **kwargs):
        return ResearchRequest(destination="Japan", start_date="2027-06-01", end_date="2027-08-31",
            programme_type="summer_school", major="Computer Science", max_programmes=count, **kwargs)

    def programme(self, number):
        return Programme(id=f"p{number}", name=f"Summer {number}", programme_type="summer_school",
            destination="Japan", official_url=f"https://school{number}.edu/summer")

    def page(self, url, source_id="S1"):
        return Page(source=Source(id=source_id, url=url, title="Summer", publisher_type="host",
            retrieved_at=datetime.now(timezone.utc), read_status="read"),
            text="2027 programme is limited to graduate students. Apply online.", links={})

    def pipeline(self, backend, extract, hits, count=3, details=None):
        events = []
        def read(_client, url, source_id):
            events.append(("read", url))
            return self.page(url, source_id)
        def native(_web, query, purpose, log, **kw):
            events.append((purpose, query))
            return [{"url": u} for u in hits(query, purpose)]
        def legacy(query, purpose, log):
            return native(None, query, purpose, log)
        def other(*args):
            query = args[1] if backend == "brave" else args[0]
            return [h["url"] for h in native(None, query,
                "candidate_replenishment" if "alternative universities" in query or "-site:" in query else "gap_followup", [])]
        def extraction(request, pages, *args):
            events.append(("extract", len(pages)))
            return extract(pages)
        with ExitStack() as stack:
            stack.enter_context(patch.dict("os.environ", {"DEEPSEEK_API_KEY": "synthetic-test-key", "BRAVE_API_KEY": "synthetic-brave-key"}))
            for name, value in {
                "request_knowledge": [], "hku_catalog_search": [],
                "deepseek_browser_search": [self.programme(1).official_url] + ([self.programme(2).official_url] if details else []),
                "openai_search": [self.programme(1).official_url],
                "brave_search": [self.programme(1).official_url],
                "linked_detail_urls": details or [],
            }.items():
                stack.enter_context(patch("research." + name, return_value=value))
            for name, callback in {"read_page": read,
                "read_deepseek_page": lambda c, w, u, i: read(c, u, i),
                "extract_with_ai": extraction, "run_deepseek_search": native,
                "run_browser_search": legacy, "openai_search_query": other,
                "brave_search_query": other}.items():
                stack.enter_context(patch("research." + name, side_effect=callback))
            result = research(self.request(count), provider="openai" if backend == "openai" else "deepseek",
                search_backend=backend, api_key=None if backend == "brave" else "synthetic-test-key")
        return result, events

    def test_one_initial_match_is_replenished_to_three_for_all_search_backends(self):
        for backend in ("deepseek", "openai", "browser", "brave"):
            with self.subTest(backend=backend):
                def extract(pages):
                    urls = {p.source.url for p in pages}
                    return Draft(programmes=[self.programme(n) for n in range(1, 4)
                        if self.programme(n).official_url in urls])
                result, events = self.pipeline(backend, extract,
                    lambda q, purpose: [self.programme(2).official_url, self.programme(3).official_url]
                    if purpose == "candidate_replenishment" else [])
                self.assertEqual(len(result.programmes), 3)
                self.assertIsNone(result.coverage_summary)
                first_extra = next(i for i, e in enumerate(events) if e[0] == "candidate_replenishment")
                first_detail = next((i for i, e in enumerate(events) if e[0] == "gap_followup"), len(events))
                self.assertLess(first_extra, first_detail)

    def test_insufficient_candidates_stop_after_two_rounds_and_explain_without_padding(self):
        def extract(pages):
            bad = next((p for p in pages if p.source.url == self.programme(2).official_url), None)
            return Draft(programmes=[self.programme(1), self.programme(2)] if bad else [self.programme(1)],
                candidate_reviews=[CandidateReview(name="Summer 2", url=bad.source.url, status="excluded",
                    reason="Only graduate students are eligible", evidence=[Evidence(source_id=bad.source.id,
                    quote="limited to graduate students")])] if bad else [])
        result, events = self.pipeline("deepseek", extract, lambda q, purpose: [self.programme(2).official_url])
        self.assertEqual([p.name for p in result.programmes], ["Summer 1"])
        self.assertEqual(len([e for e in events if e[0] == "candidate_replenishment"]), 4)
        self.assertIn("2/2", result.coverage_summary)
        self.assertIn("不代表", result.coverage_summary)
        self.assertEqual(result.candidate_reviews[0].status, "excluded")

    def test_detail_stage_rejection_triggers_reserved_candidate_search(self):
        detail_url = self.programme(2).official_url + "/requirements"
        def extract(pages):
            urls = {p.source.url for p in pages}
            detail = next((p for p in pages if p.source.url == detail_url), None)
            programmes = [self.programme(1), self.programme(2)]
            if self.programme(3).official_url in urls:
                programmes.append(self.programme(3))
            return Draft(programmes=programmes, candidate_reviews=[CandidateReview(name="Summer 2",
                url=self.programme(2).official_url, status="excluded", reason="Graduate students only",
                evidence=[Evidence(source_id=detail.source.id, quote="limited to graduate students")])] if detail else [])
        result, events = self.pipeline("deepseek", extract,
            lambda q, purpose: [self.programme(3).official_url] if purpose == "candidate_replenishment" else [],
            count=2, details=[detail_url])
        self.assertEqual([p.name for p in result.programmes], ["Summer 1", "Summer 3"])
        read_detail = next(i for i,e in enumerate(events) if e == ("read", detail_url))
        refill = next(i for i,e in enumerate(events) if e[0] == "candidate_replenishment")
        self.assertLess(read_detail, refill)

    def test_no_replenishment_when_requested_count_is_met(self):
        result, events = self.pipeline("deepseek", lambda pages: Draft(programmes=[self.programme(1)]),
            lambda q, purpose: [], count=1)
        self.assertFalse(any(e[0] == "candidate_replenishment" for e in events))
        self.assertIsNone(result.coverage_summary)

    def test_duplicate_programme_pages_do_not_fill_slots(self):
        p = self.programme(1)
        duplicate = p.model_copy(update={"id": "duplicate", "official_url": p.official_url + "/apply"})
        selected, _ = verify_draft(Draft(programmes=[p, duplicate, self.programme(2)]), self.request(), [])
        self.assertEqual(len(selected), 2)

    def test_search_summary_or_unread_quote_cannot_justify_rejection(self):
        page = self.page(self.programme(1).official_url)
        review = CandidateReview(name="Summer 1", url=page.source.url, status="excluded",
            reason="Made-up cost", evidence=[Evidence(source_id=page.source.id, quote="Cost 1000000")])
        draft = Draft(programmes=[self.programme(1)], candidate_reviews=[review])
        self.assertEqual(checked_candidate_reviews(draft, [page]), [])
        self.assertEqual(len(verify_draft(draft, self.request(), [page])[0]), 1)
        review.evidence[0].quote = "limited to graduate students"
        page.source.publisher_type = "social"
        self.assertEqual(checked_candidate_reviews(draft, [page]), [])

    def test_unconfirmed_candidate_is_not_counted_as_confirmed_match(self):
        page = self.page(self.programme(1).official_url)
        review = CandidateReview(name="Summer 1", url=page.source.url, status="unconfirmed",
            reason="Undergraduate eligibility unconfirmed", evidence=[Evidence(source_id=page.source.id,
                quote="limited to graduate students")])
        selected, _ = verify_draft(Draft(programmes=[self.programme(1)], candidate_reviews=[review]),
            self.request(), [page])
        self.assertEqual(selected, [])


if __name__ == "__main__":
    unittest.main()
