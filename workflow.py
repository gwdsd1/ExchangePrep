"""Request-local research credentials and the live research-to-planner bridge."""
from datetime import date
from datetime import datetime, timezone, timedelta
from typing import Literal

from pydantic import Field, model_validator
from models import ResearchRequest, ResearchResult
from planner.schema import (PlanningAnchor, StudentProfile, TaskSpec, DurationEstimate,
                            adapt_research_result)
from planner.timeline import build_plan, render_markdown


class WorkflowRequest(ResearchRequest):
    provider: Literal["deepseek", "openai"] = "deepseek"
    model: str = Field(default="", max_length=100, pattern=r"^[a-zA-Z0-9._:/-]*$")
    departure_date: date
    duration_days: int = Field(default=7, ge=1, le=180)
    buffer_days: int = Field(default=3, ge=0, le=60)

    @model_validator(mode="after")
    def check_departure(self):
        if self.departure_date > self.end_date:
            raise ValueError("出发日期不能晚于意向项目结束日期")
        return self


def plan_research(result: ResearchResult, settings: WorkflowRequest) -> dict:
    """Plan each programme independently: step IDs need not be globally unique."""
    plans, markdown = [], []
    today = datetime.now(timezone(timedelta(hours=8))).date()
    for index, programme in enumerate(result.programmes):
        subset = result.model_copy(update={"programmes": [programme]})
        specs = {step.id: TaskSpec(task_id=step.id, buffer_days=settings.buffer_days,
                 duration=DurationEstimate(min_days=settings.duration_days,
                     max_days=settings.duration_days, basis="inferred_convention"))
                 for step in programme.steps}
        manifest = adapt_research_result(subset, task_specs=specs,
            anchors=[PlanningAnchor(kind="departure", label="User's expected departure date" if settings.language == "en" else "用户填写的预计出发日期",
                anchor_date=settings.departure_date, state="stated")],
            profile=StudentProfile(year_of_study=settings.year_of_study,
                programme_of_study=settings.major), as_of=today, case_id=f"live_{index + 1}")
        manifest.programme_id = programme.id
        manifest.programme_name = programme.name
        manifest.programme_type = programme.programme_type
        sources = {source.id: source for source in result.sources}
        steps = {step.id: step for step in programme.steps}
        for task in manifest.tasks:
            step = steps[task.id]
            # The legacy adapter maps historical deadlines to inferred dates;
            # live workflow must never schedule those as current official dates.
            if step.deadline.state != "verified" or step.deadline.kind in {"window", "rolling"}:
                task.deadline = None
                task.deadline_basis = "unknown"
                task.deadline_state = "unknown"
            task.deadline_timezone_known = bool(step.deadline.timezone)
            task.notes.append(f"User estimate: {settings.duration_days} days per step and {settings.buffer_days} buffer days; not official processing time." if settings.language == "en" else f"用户排期估算：每步 {settings.duration_days} 天，缓冲 {settings.buffer_days} 天；不是官方处理时间。")
            for evidence in task.evidence:
                if evidence.source_id in sources:
                    source = sources[evidence.source_id]
                    evidence.url = source.url
                    evidence.retrieved_at = source.retrieved_at.isoformat()
        plan = build_plan(manifest)
        # Present the dependency-consistent earliest schedule as the initial plan.
        # Independent AHP interpolation can put a successor before a predecessor's
        # recommended finish. Latest windows and priority scores remain available.
        for entry in plan.entries:
            entry.recommended_start = entry.earliest_start if entry.state != "infeasible" else None
        if settings.language == "en":
            plan.notes_plain = ["Start dates respect prerequisite order. Durations and buffers are user estimates, not official processing times."]
            for conflict in plan.conflicts:
                conflict.detail_plain = conflict.detail
            for entry in plan.entries:
                entry.state_plain = entry.state.replace("_", " ")
                entry.deadline_source_plain = entry.deadline_source
                entry.blocking_plain = list(entry.blocking_conflicts)
                entry.warnings_plain = list(entry.warnings)
        else:
            plan.notes_plain.append("建议从可开始日期动手；耗时与缓冲为用户统一估算。未核实日期不作为官方截止，冲突步骤需先处理。")
        plans.append(plan)
        markdown.append(english_markdown(plan) if settings.language == "en" else render_markdown(plan))
    return {"research": result, "plans": plans, "markdown": "\n\n---\n\n".join(markdown),
            "assumptions": {"departure_date": settings.departure_date,
                "duration_days": settings.duration_days, "buffer_days": settings.buffer_days,
                "note": "Durations are user estimates. Start and latest-start dates are calculated, not official deadlines." if settings.language == "en" else "耗时是用户估算；可开始／最晚开始是排期计算值，不是官方 DDL。"}}


def english_markdown(plan):
    lines = [f"# {plan.programme_name}", "", f"Planning date: {plan.as_of}",
        f"Status: {plan.feasibility}", "", "Durations and buffers are user estimates. Dates require official confirmation where marked unknown.", ""]
    for entry in plan.entries:
        lines += [f"## {entry.order}. {entry.title}", "", entry.action or "",
            f"Suggested start: {entry.recommended_start or 'To confirm'}",
            f"Latest start (calculated): {entry.latest_start or 'To confirm'}",
            f"Official deadline: {entry.deadline or 'To confirm'}",
            f"Prerequisites: {', '.join(entry.prerequisites) or 'None stated'}",
            f"Documents: {', '.join(entry.documents) or 'To confirm'}", entry.channel or "", ""]
        for source in entry.sources:
            lines += [f"> {source.quote}", f"Source: {source.url or source.source_id}", ""]
    if plan.conflicts:
        lines += ["## Checks to resolve", ""] + [f"- {conflict.detail}" for conflict in plan.conflicts]
    return "\n\n".join(lines)


def english_sample(result):
    """Translate the bundled fixed workflow; never call a model for offline mode."""
    result = result.model_copy(deep=True)
    result.request.language = "en"
    result.warnings = ["Fixed offline example; no live search was performed. Check current requirements with official sources."]
    programme = result.programmes[0]
    programme.name = "HKU SAO short-term study workflow (example, not a specific programme)"
    programme.destination = "Depends on the chosen programme"
    programme.unresolved_questions = ["Confirm the current programme's application links, deadlines, documents and personal eligibility."]
    texts = {
        "host_application": ("Apply to the host institution", "Submit your programme application directly to the host institution."),
        "hku_registration_open": ("Start your HKU SAO registration", "You can start the registration when you plan to apply for a summer programme."),
        "offer_received": ("Receive the host institution's offer", "Wait for and obtain your admission letter."),
        "hku_registration_submit": ("Submit the HKU SAO registration", "After receiving admission, submit your HKU registration as instructed."),
        "funding": ("Check HKU SAO funding eligibility", "Check whether you qualify for a scholarship or allowance."),
        "visa_check": ("Confirm visa and entry requirements", "Check the destination government's rules for your nationality and programme.")}
    for step in programme.steps:
        step.title, step.action.value = texts[step.id]
        step.notes = ["Example guidance only. Confirm the actual programme's requirements."]
        step.applies_if = "You are using the SAO route and meet the applicable eligibility conditions."
        if step.channel.value:
            step.channel.value = "Follow the official SAO guidance: https://intlaffairs.hku.hk/backend/faqs/sao-application/"
        if step.deadline.raw:
            step.deadline.raw = "Confirm the actual deadline and any offer-dependent trigger with the official provider."
        step.deadline.trigger = None
        for document in step.documents:
            document.name = "Admission evidence and supporting documents as required by the official application"
            document.detail = None
    return result
