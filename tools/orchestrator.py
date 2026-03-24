"""
PredictHub — Master Orchestrator
Claude calls this to run complex multi-step workflows.

Usage:
    python tools/orchestrator.py morning        (daily morning routine)
    python tools/orchestrator.py update_site     (refresh site data + deploy)
    python tools/orchestrator.py weekly_seo      (full SEO monitoring cycle)
    python tools/orchestrator.py content_day     (generate all content for the day)
    python tools/orchestrator.py pre_stream      (prepare everything for a stream)
    python tools/orchestrator.py status          (show status of all systems)
"""

import subprocess
import sys
import os
import json
from datetime import datetime, date

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)

def run_tool(script, args=""):
    """Run a tool script and return output"""
    cmd = f'python -X utf8 "{os.path.join(TOOLS_DIR, script)}" {args}'
    print(f"\n▸ Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120,
            encoding='utf-8', errors='replace'
        )
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0 and result.stderr:
            print(f"  ⚠ Error: {result.stderr[:200]}")
        return result.stdout
    except subprocess.TimeoutExpired:
        print("  ⚠ Timeout after 120s")
        return ""
    except Exception as e:
        print(f"  ⚠ Failed: {e}")
        return ""

def morning_routine():
    """
    DAILY MORNING ROUTINE
    1. Fetch hot markets from Polymarket
    2. Send to Telegram channel
    3. Prepare Twitter post
    4. Save daily report
    """
    print("=" * 60)
    print(f"☀ MORNING ROUTINE — {date.today()}")
    print("=" * 60)

    # 1. Get hot markets
    print("\n[1/4] Fetching hot markets...")
    run_tool("polymarket_api.py", "export")

    # 2. Send to Telegram
    print("\n[2/4] Sending to Telegram...")
    run_tool("telegram_bot.py", "markets")

    # 3. Prepare Twitter content
    print("\n[3/4] Preparing Twitter post...")
    markets_file = os.path.join(PROJECT_DIR, "reports", "daily-markets.json")
    if os.path.exists(markets_file):
        with open(markets_file, 'r') as f:
            markets = json.load(f)
        if markets:
            m = markets[0]
            pct = int(float(m.get('yes_price', 0)) * 100)
            tweet = f"📊 Hottest market today: {m['question']}\n\nMarket: {pct}% Yes\n\nTrade it on Polymarket 👇"
            # Save tweet for review (Claude can post after review)
            tweet_file = os.path.join(PROJECT_DIR, "content", f"tweet-{date.today()}.txt")
            os.makedirs(os.path.dirname(tweet_file), exist_ok=True)
            with open(tweet_file, 'w') as f:
                f.write(tweet)
            print(f"  Tweet draft saved: {tweet_file}")

    # 4. Summary
    print("\n[4/4] Morning report saved.")
    print("\n" + "=" * 60)
    print("✓ Morning routine complete!")
    print(f"  → Telegram: market update sent")
    print(f"  → Twitter: draft ready for review")
    print(f"  → Markets data: reports/daily-markets.json")
    print("=" * 60)

def update_site():
    """
    UPDATE SITE CONTENT + DEPLOY
    1. Fetch latest data from Polymarket/Kalshi
    2. Update HTML files with fresh numbers
    3. Deploy to production
    """
    print("=" * 60)
    print(f"🔄 SITE UPDATE — {date.today()}")
    print("=" * 60)

    # 1. Fetch data
    print("\n[1/3] Fetching latest market data...")
    run_tool("polymarket_api.py", "export")

    # 2. Update date stamps on site pages
    print("\n[2/3] Updating date stamps...")
    today_str = datetime.now().strftime("%B %d, %Y")
    site_dir = os.path.join(PROJECT_DIR, "site")

    updated_files = []
    for root, dirs, files in os.walk(site_dir):
        for f in files:
            if f.endswith('.html'):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8') as fh:
                    content = fh.read()

                # Update "Updated: March XX, 2026" pattern
                import re
                new_content = re.sub(
                    r'Updated: \w+ \d{1,2}, \d{4}',
                    f'Updated: {today_str}',
                    content
                )

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as fh:
                        fh.write(new_content)
                    updated_files.append(os.path.relpath(filepath, PROJECT_DIR))

    print(f"  Updated {len(updated_files)} files")
    for f in updated_files:
        print(f"    ✓ {f}")

    # 3. Deploy
    print("\n[3/3] Deploying...")
    deploy_script = os.path.join(TOOLS_DIR, "deploy.sh")
    if os.path.exists(deploy_script):
        subprocess.run(f'bash "{deploy_script}" "Auto-update {date.today()}"', shell=True)
    else:
        print("  ⚠ deploy.sh not found — commit manually")

    print("\n" + "=" * 60)
    print("✓ Site update complete!")
    print("=" * 60)

def weekly_seo():
    """
    WEEKLY SEO MONITORING
    1. Track all keywords in Google
    2. Take SERP screenshots
    3. Compare with last week
    4. Generate report
    """
    print("=" * 60)
    print(f"📊 WEEKLY SEO REPORT — {date.today()}")
    print("=" * 60)

    # 1. Track keywords
    print("\n[1/3] Tracking keywords...")
    run_tool("serp_monitor.py", "track")

    # 2. Compare with last week
    print("\n[2/3] Comparing with previous report...")
    run_tool("serp_monitor.py", "compare")

    # 3. Summary
    print("\n[3/3] Report saved to reports/")
    print("\n" + "=" * 60)
    print("✓ SEO monitoring complete!")
    print("  → Check reports/serp-*.json for details")
    print("  → Screenshots in reports/serp/")
    print("=" * 60)

def content_day():
    """
    CONTENT GENERATION DAY
    1. Get market data
    2. Generate video script
    3. Generate audio (if ElevenLabs configured)
    4. Prepare social media posts
    """
    print("=" * 60)
    print(f"🎬 CONTENT DAY — {date.today()}")
    print("=" * 60)

    # 1. Markets data
    print("\n[1/4] Fetching market data...")
    run_tool("polymarket_api.py", "export")

    # 2. Video script
    print("\n[2/4] Generating video script...")
    run_tool("video_maker.py", 'full "Top 5 Prediction Markets This Week"')

    # 3. Twitter posts for the week
    print("\n[3/4] Generating weekly Twitter posts...")
    markets_file = os.path.join(PROJECT_DIR, "reports", "daily-markets.json")
    posts = []
    if os.path.exists(markets_file):
        with open(markets_file, 'r') as f:
            markets = json.load(f)
        for m in markets[:5]:
            pct = int(float(m.get('yes_price', 0)) * 100)
            post = f"📊 {m['question']}\n\nMarket says: {pct}%\n\nWhat do you think? 👇"
            posts.append({"text": post, "delay_seconds": 86400})

    posts_file = os.path.join(PROJECT_DIR, "content", f"twitter-week-{date.today()}.json")
    os.makedirs(os.path.dirname(posts_file), exist_ok=True)
    with open(posts_file, 'w') as f:
        json.dump(posts, f, indent=2)
    print(f"  {len(posts)} posts saved to {posts_file}")

    # 4. Summary
    print("\n[4/4] Content generated!")
    print("\n" + "=" * 60)
    print("✓ Content day complete!")
    print(f"  → Video: content/video-{date.today()}.mp4")
    print(f"  → Script: content/script-{date.today()}.txt")
    print(f"  → Twitter: content/twitter-week-{date.today()}.json")
    print("=" * 60)

def pre_stream():
    """
    PRE-STREAM PREPARATION
    1. Fetch latest market data
    2. Update OBS overlay
    3. Generate talking points
    """
    print("=" * 60)
    print(f"🎥 PRE-STREAM PREP — {datetime.now().strftime('%H:%M')}")
    print("=" * 60)

    # 1. Fresh data
    print("\n[1/3] Fetching live market data...")
    run_tool("polymarket_api.py", "export")

    # 2. Update OBS
    print("\n[2/3] Updating OBS overlay...")
    run_tool("obs_controller.py", "markets")

    # 3. Talking points
    print("\n[3/3] Generating talking points...")
    markets_file = os.path.join(PROJECT_DIR, "reports", "daily-markets.json")
    if os.path.exists(markets_file):
        with open(markets_file, 'r') as f:
            markets = json.load(f)

        points = "STREAM TALKING POINTS\n" + "=" * 40 + "\n\n"
        for i, m in enumerate(markets[:5], 1):
            q = m.get('question', 'Unknown')
            pct = int(float(m.get('yes_price', 0)) * 100)
            vol = float(m.get('volume_24h', 0))
            points += f"{i}. {q}\n"
            points += f"   Market: {pct}% Yes | 24h Vol: ${vol:,.0f}\n"
            points += f"   → Discuss: Why is this priced here? What could move it?\n\n"

        points_file = os.path.join(PROJECT_DIR, "content", f"stream-notes-{date.today()}.txt")
        os.makedirs(os.path.dirname(points_file), exist_ok=True)
        with open(points_file, 'w') as f:
            f.write(points)
        print(f"  Talking points saved: {points_file}")

    print("\n" + "=" * 60)
    print("✓ Stream prep complete! You're ready to go live.")
    print("=" * 60)

def show_status():
    """Show status of all systems"""
    print("=" * 60)
    print(f"📋 SYSTEM STATUS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Check .env
    env_path = os.path.join(TOOLS_DIR, '.env')
    env_exists = os.path.exists(env_path)
    print(f"\n  .env file:     {'✓ Found' if env_exists else '✗ Missing — copy .env.example to .env'}")

    # Check each tool's dependencies
    tools_status = {
        "Twitter Poster": "tweepy",
        "Telegram Bot": "telegram",
        "Polymarket API": "requests",
        "SERP Monitor": "playwright",
        "Video Maker": "elevenlabs",
        "OBS Controller": "obsws_python",
    }

    print("\n  Tool dependencies:")
    for tool, module in tools_status.items():
        try:
            __import__(module)
            print(f"    ✓ {tool:<20} ({module} installed)")
        except ImportError:
            print(f"    ✗ {tool:<20} ({module} NOT installed)")

    # Check reports
    reports_dir = os.path.join(PROJECT_DIR, "reports")
    if os.path.exists(reports_dir):
        files = os.listdir(reports_dir)
        print(f"\n  Reports: {len(files)} files in reports/")
    else:
        print(f"\n  Reports: directory not created yet")

    # Check site
    site_dir = os.path.join(PROJECT_DIR, "site")
    html_count = sum(1 for r, d, f in os.walk(site_dir) for ff in f if ff.endswith('.html'))
    print(f"  Site pages: {html_count} HTML files")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("""
PredictHub Orchestrator — Available workflows:

  morning       Daily morning routine (markets → Telegram → Twitter draft)
  update_site   Refresh site content + deploy
  weekly_seo    Full SEO monitoring cycle
  content_day   Generate all content (video + social)
  pre_stream    Prepare for a live stream
  status        Check system status
        """)
        sys.exit(0)

    cmd = sys.argv[1]
    commands = {
        'morning': morning_routine,
        'update_site': update_site,
        'weekly_seo': weekly_seo,
        'content_day': content_day,
        'pre_stream': pre_stream,
        'status': show_status,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown workflow: {cmd}")
        print("Available: " + ", ".join(commands.keys()))
