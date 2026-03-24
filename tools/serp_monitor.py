"""
PredictHub — SERP Monitor & Screenshot Tool
Usage:
    python tools/serp_monitor.py screenshot "polymarket promo code"
    python tools/serp_monitor.py track                                (track all target keywords)
    python tools/serp_monitor.py compare                              (compare with last report)
"""

import sys
import os
import json
import re
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

REPORTS_DIR = os.getenv('REPORTS_DIR', os.path.join(os.path.dirname(__file__), '..', 'reports'))

# Keywords we want to track
TARGET_KEYWORDS = [
    "polymarket promo code",
    "polymarket referral code",
    "kalshi promo code",
    "kalshi referral code",
    "polymarket vs kalshi",
    "best prediction market apps",
    "is polymarket legal in india",
    "polymarket sign up bonus",
    "prediction markets 2026",
]

def screenshot_serp(query, country="us"):
    """Take a screenshot of Google SERP for a query"""
    from playwright.sync_api import sync_playwright

    output_dir = os.path.join(REPORTS_DIR, 'serp')
    os.makedirs(output_dir, exist_ok=True)

    safe_query = re.sub(r'[^\w\s-]', '', query)[:40].strip().replace(' ', '_')
    filename = f"{date.today()}_{safe_query}.png"
    filepath = os.path.join(output_dir, filename)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        # Set cookie to bypass consent
        context.add_cookies([{
            "name": "CONSENT",
            "value": "PENDING+987",
            "domain": ".google.com",
            "path": "/"
        }, {
            "name": "SOCS",
            "value": "CAISHAgBEhJnd3NfMjAyNTAxMTUtMA",
            "domain": ".google.com",
            "path": "/"
        }])
        page = context.new_page()
        url = f"https://www.google.com/search?q={query}&gl={country}&hl=en&num=10"
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path=filepath, full_page=False)
        browser.close()

    print(json.dumps({"status": "screenshot_saved", "path": filepath, "query": query}))
    return filepath

def extract_serp_results(query, country="us"):
    """Extract top 10 results from Google SERP"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        url = f"https://www.google.com/search?q={query}&gl={country}&hl=en&num=10"
        page.goto(url)
        page.wait_for_timeout(2000)
        try:
            accept_btn = page.locator('button:has-text("Accept all")')
            if accept_btn.is_visible(timeout=2000):
                accept_btn.click()
                page.wait_for_timeout(2000)
        except Exception:
            pass

        results = page.evaluate("""
            () => {
                const items = document.querySelectorAll('div.g');
                return Array.from(items).slice(0, 10).map((el, i) => {
                    const link = el.querySelector('a');
                    const title = el.querySelector('h3');
                    return {
                        position: i + 1,
                        title: title ? title.innerText : '',
                        url: link ? link.href : '',
                        domain: link ? new URL(link.href).hostname : ''
                    };
                });
            }
        """)
        browser.close()

    return results

def track_all_keywords():
    """Track all target keywords and save report"""
    report = {
        "date": str(date.today()),
        "timestamp": datetime.now().isoformat(),
        "keywords": {}
    }

    for kw in TARGET_KEYWORDS:
        print(f"Tracking: {kw}...")
        try:
            results = extract_serp_results(kw)
            screenshot_serp(kw)
            report["keywords"][kw] = {
                "results": results,
                "our_position": None
            }
            # Check if our site is in the results
            site_url = os.getenv('SITE_URL', 'yoursite.com').replace('https://', '').replace('http://', '')
            for r in results:
                if site_url in r.get('domain', ''):
                    report["keywords"][kw]["our_position"] = r['position']
                    break
        except Exception as e:
            report["keywords"][kw] = {"error": str(e)}

    # Save report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"serp-{date.today()}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print(f"SERP REPORT — {date.today()}")
    print("=" * 60)
    for kw, data in report["keywords"].items():
        pos = data.get("our_position", "Not found")
        print(f"  [{pos:>4}] {kw}")
    print("=" * 60)
    print(f"Saved: {report_path}")

    return report

def compare_reports():
    """Compare latest report with previous one"""
    reports = sorted([
        f for f in os.listdir(REPORTS_DIR)
        if f.startswith('serp-') and f.endswith('.json')
    ])

    if len(reports) < 2:
        print("Need at least 2 reports to compare. Run 'track' first.")
        return

    with open(os.path.join(REPORTS_DIR, reports[-1]), 'r') as f:
        current = json.load(f)
    with open(os.path.join(REPORTS_DIR, reports[-2]), 'r') as f:
        previous = json.load(f)

    print(f"\nComparing: {reports[-2]} → {reports[-1]}")
    print("=" * 60)

    for kw in TARGET_KEYWORDS:
        curr_pos = current.get("keywords", {}).get(kw, {}).get("our_position")
        prev_pos = previous.get("keywords", {}).get(kw, {}).get("our_position")

        curr_str = str(curr_pos) if curr_pos else "—"
        prev_str = str(prev_pos) if prev_pos else "—"

        if curr_pos and prev_pos:
            diff = prev_pos - curr_pos
            arrow = f"↑{diff}" if diff > 0 else f"↓{abs(diff)}" if diff < 0 else "="
        else:
            arrow = "new" if curr_pos and not prev_pos else ""

        print(f"  {prev_str:>4} → {curr_str:>4}  {arrow:>5}  {kw}")

    print("=" * 60)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python serp_monitor.py [screenshot|track|compare] [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'screenshot':
        query = sys.argv[2] if len(sys.argv) > 2 else "polymarket promo code"
        screenshot_serp(query)

    elif cmd == 'track':
        track_all_keywords()

    elif cmd == 'compare':
        compare_reports()

    else:
        print(f"Unknown command: {cmd}")
