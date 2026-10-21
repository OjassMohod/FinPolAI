"""Optional real-browser smoke test. Requires playwright and a Chromium installation."""

import os

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"),
        headless=True,
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.getenv("POLICYGUARD_URL", "http://127.0.0.1:8000"))
    page.wait_for_selector('#sample option[value="exception"]', state="attached")
    page.screenshot(path="/tmp/policyguard-dashboard.png", full_page=True)
    for sample, outcome in [
        ("compliant", "PASS"),
        ("over-limit", "FLAGGED"),
        ("incomplete", "NEEDS INFORMATION"),
        ("high-value", "REVIEW REQUIRED"),
        ("exception", "PASS"),
    ]:
        page.click('a[data-nav="dashboard"]')
        page.select_option("#sample", sample)
        page.click("#verify-button")
        page.wait_for_url("**/#details")
        assert page.locator("#report-content .report-banner .badge").inner_text() == outcome
        assert page.locator(".trace-item").count() >= 5
    page.screenshot(path="/tmp/policyguard-report.png", full_page=True)
    page.click('a[data-nav="history"]')
    page.wait_for_selector(".history-link")
    page.click(".history-link >> nth=0")
    page.wait_for_url("**/#details")
    page.click('a[data-nav="policies"]')
    page.wait_for_selector("[data-policy]")
    page.fill("#policy-query", "scholarship tuition exception")
    page.click("#search-form button")
    page.wait_for_selector("#search-results .evidence-card")
    assert (
        "POLICY-EXCEPTION-07" in page.locator("#search-results .evidence-card").first.inner_text()
    )
    page.set_input_files(
        "#policy-file",
        {
            "name": "browser-note.md",
            "mimeType": "text/markdown",
            "buffer": b"# Browser source\nScholarship support guidance for synthetic demo transfers.",
        },
    )
    page.click("#upload-button")
    page.wait_for_function(
        "() => document.querySelector('#upload-status').textContent.includes('No rules activated')"
    )
    page.click('[data-policy="POLICY-EXCEPTION-07"]')
    page.wait_for_selector("#policy-detail .source-text")
    page.screenshot(path="/tmp/policyguard-policies.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.click('a[data-nav="dashboard"]')
    page.screenshot(path="/tmp/policyguard-mobile.png", full_page=True)
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"), (
        "Mobile overflow"
    )
    assert not errors, errors
    print(
        "PASS: five form scenarios, real verification, report, trace, history restore, policy search, upload, rule details, mobile layout; no JavaScript errors."
    )
    browser.close()
