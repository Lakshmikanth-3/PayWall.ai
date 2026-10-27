"""Agent trace: one JSON line per step, printed to stdout and written to logs/<run_id>.jsonl."""
import datetime
import json
import os
import sys
import uuid

LOG_DIR = os.environ.get("PAYWALL_LOG_DIR", "logs")


class Trace:
    def __init__(self, input_summary: str):
        self.run_id = f"run-{uuid.uuid4().hex[:10]}"
        self.events: list[dict] = []
        self.input_summary = input_summary[:200]
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            self.path = os.path.join(LOG_DIR, f"{self.run_id}.jsonl")
        except OSError:
            self.path = None

    def log(self, agent_name: str, action: str, status: str, output_summary: str,
            target_agent: str | None = None, model: str | None = None, retry_count: int = 0):
        e = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "run_id": self.run_id,
             "agent_name": agent_name, "action": action, "input_summary": self.input_summary,
             "output_summary": output_summary[:300], "target_agent": target_agent, "model": model,
             "retry_count": retry_count, "status": status}
        self.events.append(e)
        line = json.dumps(e)
        print(line, file=sys.stdout, flush=True)
        if self.path:
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except OSError:
                pass
