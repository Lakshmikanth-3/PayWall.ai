"""Meterless H-MEM engine (vendored reference, run through the Node bridge): save, then recall by similarity."""
import shutil

import pytest

from app import hmem_bridge


@pytest.mark.skipif(shutil.which("node") is None, reason="H-MEM runs on Node 22+")
def test_hmem_saves_and_recalls_a_purchase_decision(tmp_path, monkeypatch):
    monkeypatch.setenv("PAYWALL_HMEM_DIR", str(tmp_path))
    mid = hmem_bridge.save("Intent: running shoes under 5000 -> Running Shoes 4799 INR from MER-001; Guard ALLOW", ["sports", "allow"], "paywall:test")
    assert mid.startswith("mem-")
    hmem_bridge.save("Intent: weekly groceries -> Weekly Grocery Pack 899 INR from MER-003; Guard ALLOW", ["groceries", "allow"], "paywall:test")
    recalled = hmem_bridge.recall("running shoes for a marathon")
    assert recalled and "Running Shoes" in recalled[0]["content"]
