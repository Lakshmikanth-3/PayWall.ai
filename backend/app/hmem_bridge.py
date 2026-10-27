"""Meterless H-MEM engine (vendored TypeScript reference in engines/hmem) called through its Node CLI bridge."""
import json
import os
import subprocess

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engines", "hmem", "cli.ts")


def _call(payload: dict) -> dict:
    r = subprocess.run(["node", "--experimental-transform-types", "--no-warnings", ENGINE],
                       input=json.dumps(payload), capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200] or "H-MEM bridge failed")
    return json.loads(r.stdout.strip().splitlines()[-1])


def recall(query: str, top_n: int = 3) -> list[dict]:
    return _call({"op": "recall", "query": query, "topN": top_n}).get("memories", [])


def save(content: str, tags: list[str], source: str) -> str:
    return _call({"op": "save", "content": content, "tags": tags, "source": source})["id"]
