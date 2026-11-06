"""Reproducible local retrieval evaluation; no external AI or user data."""
import json
import platform
import statistics
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from .config import ROOT, Settings
from .main import create_app


def main():
    cases = json.loads((ROOT / "docs/evaluation-cases.json").read_text())
    results = []
    with tempfile.TemporaryDirectory() as directory:
        settings = replace(Settings(), database=str(Path(directory) / "evaluation.sqlite3"),
                           secure_cookie=False, demo=True, llm_url="", llm_key="", embedding_model="",
                           admin_email="", admin_password="", employee_email="", employee_password="")
        with TestClient(create_app(settings)) as client:
            for case in cases:
                identity = client.post("/api/auth/demo", json={"role": case["role"]}).json()
                start = time.perf_counter()
                response = client.post("/api/chat", json={"question": case["question"]},
                                       headers={"X-CSRF-Token": identity["csrf_token"]})
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                response.raise_for_status()
                answer = response.json()
                source_ids = [s["document_id"] for s in answer["sources"]]
                passed = answer["status"] == case["status"] and (not case.get("document") or case["document"] in source_ids)
                results.append({**case, "actual_status": answer["status"], "actual_documents": source_ids,
                                "passed": passed, "latency_ms": duration_ms})
    summary = {"run_at_utc": datetime.now(UTC).isoformat(), "python": platform.python_version(),
               "mode": "local extractive / char-bigram TF-IDF", "provider_calls": 0,
               "cases": len(results), "passed": sum(r["passed"] for r in results),
               "median_ms": round(statistics.median(r["latency_ms"] for r in results), 2),
               "results": results}
    output = ROOT / "docs/evaluation-results.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"{summary['passed']}/{summary['cases']} passed; median {summary['median_ms']} ms; provider calls: 0")
    for case in results:
        if not case["passed"]:
            print(f"FAIL: {case['question']} -> {case['actual_status']} / {case['actual_documents']}")


if __name__ == "__main__":
    main()
