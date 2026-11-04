"""Build the GitHub Pages frontend and fixed bilingual offline examples."""
import argparse
import json
from pathlib import Path
import shutil

from fastapi.encoders import jsonable_encoder
from models import ResearchResult
from workflow import WorkflowRequest, plan_research, english_sample

ROOT = Path(__file__).resolve().parent


def build(backend_url=""):
    output = ROOT / "docs"
    (output / "static").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "static/workspace.html", output / "index.html")
    for name in ("workspace.css", "workspace.js"):
        shutil.copy2(ROOT / "static" / name, output / "static" / name)
    (output / ".nojekyll").touch()
    config = {"backendUrl": backend_url.rstrip("/") or None}
    (output / "static/config.js").write_text("window.EXCHANGEPREP_CONFIG = " + json.dumps(config) + ";\n", encoding="utf-8")
    for language in ("zh", "en"):
        result = ResearchResult.model_validate_json((ROOT / "sample.json").read_text(encoding="utf-8"))
        if language == "en":
            result = english_sample(result)
        settings = WorkflowRequest(destination="United Kingdom", start_date="2027-06-01",
            end_date="2027-08-31", departure_date="2027-06-01", programme_type="summer_school", language=language)
        result.request = result.request.model_copy(update={"language": language})
        payload = jsonable_encoder(plan_research(result, settings))
        (output / "static" / f"sample-workflow-{language}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"GitHub Pages files built at {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default="")
    build(parser.parse_args().backend_url)
