"""Tests for plugin-detector.py — auto-selecting skills/plugins for QRALPH projects."""

import pytest
import tempfile
import os
import json
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_frontend_request_queues_frontend_design():
    from plugin_detector import detect_plugins_for_request
    plugins = detect_plugins_for_request("build a landing page with hero section and pricing table")
    assert "frontend-design" in plugins


def test_payment_request_queues_stripe():
    from plugin_detector import detect_plugins_for_request
    plugins = detect_plugins_for_request("add subscription billing to the SaaS app")
    assert "stripe" in plugins


def test_library_request_queues_context7():
    from plugin_detector import detect_plugins_for_request
    plugins = detect_plugins_for_request("build a React app with TanStack Query for data fetching")
    assert "context7" in plugins


def test_generic_request_returns_minimal_plugins():
    from plugin_detector import detect_plugins_for_request
    plugins = detect_plugins_for_request("fix a typo in the readme")
    assert len(plugins) <= 1


def test_multiple_signals_stack():
    from plugin_detector import detect_plugins_for_request
    plugins = detect_plugins_for_request("build an ecommerce storefront with Stripe checkout and React")
    assert "frontend-design" in plugins
    assert "stripe" in plugins
    assert "context7" in plugins


def test_detect_plugins_from_codebase():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = {"dependencies": {"react": "^18.0.0", "stripe": "^14.0.0"}}
        with open(os.path.join(tmp, "package.json"), "w") as f:
            json.dump(pkg, f)
        from plugin_detector import detect_plugins_from_codebase
        plugins = detect_plugins_from_codebase(tmp)
        assert "context7" in plugins
        assert "stripe" in plugins


def test_detect_all_combines_request_and_codebase():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = {"dependencies": {"react": "^18.0.0"}}
        with open(os.path.join(tmp, "package.json"), "w") as f:
            json.dump(pkg, f)
        from plugin_detector import detect_all_plugins
        plugins = detect_all_plugins("add payment processing", tmp)
        assert "stripe" in plugins  # from request
        assert "context7" in plugins  # from codebase


def test_playwright_detected_from_config():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "playwright.config.ts"), "w") as f:
            f.write("export default {}")
        from plugin_detector import detect_plugins_from_codebase
        plugins = detect_plugins_from_codebase(tmp)
        assert "playwright" in plugins


def test_playwright_detected_from_request():
    from plugin_detector import detect_plugins_for_request
    plugins = detect_plugins_for_request("write e2e browser tests for the login flow")
    assert "playwright" in plugins


def test_codebase_with_no_manifest_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        from plugin_detector import detect_plugins_from_codebase
        plugins = detect_plugins_from_codebase(tmp)
        assert plugins == []


def test_playwright_detected_from_devdependencies():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = {"devDependencies": {"@playwright/test": "^1.40.0"}}
        with open(os.path.join(tmp, "package.json"), "w") as f:
            json.dump(pkg, f)
        from plugin_detector import detect_plugins_from_codebase
        plugins = detect_plugins_from_codebase(tmp)
        assert "playwright" in plugins


def test_context7_detected_from_requirements_txt():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "requirements.txt"), "w") as f:
            f.write("flask==3.0.0\nrequests==2.31.0\n")
        from plugin_detector import detect_plugins_from_codebase
        plugins = detect_plugins_from_codebase(tmp)
        assert "context7" in plugins


def test_detect_all_deduplicates():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = {"dependencies": {"stripe": "^14.0.0"}}
        with open(os.path.join(tmp, "package.json"), "w") as f:
            json.dump(pkg, f)
        from plugin_detector import detect_all_plugins
        plugins = detect_all_plugins("add stripe checkout", tmp)
        assert plugins.count("stripe") == 1
