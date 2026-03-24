"""
PredictHub — Telegram Channel Bot
Usage:
    python tools/telegram_bot.py send "Message text"
    python tools/telegram_bot.py markets              (sends daily hot markets)
    python tools/telegram_bot.py report               (sends weekly report)
    python tools/telegram_bot.py listen                (runs bot in listen mode for commands)
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

async def get_bot():
    from telegram import Bot
    return Bot(token=BOT_TOKEN)

async def send_message(text, parse_mode="HTML"):
    """Send a message to the channel"""
    bot = await get_bot()
    msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode=parse_mode,
        disable_web_page_preview=False
    )
    print(json.dumps({
        "status": "sent",
        "message_id": msg.message_id,
        "chat": str(CHANNEL_ID),
        "timestamp": datetime.now().isoformat()
    }, indent=2))
    return msg.message_id

async def send_daily_markets(markets=None):
    """Send daily hot markets to channel"""
    if markets is None:
        # Load from file if available
        markets_file = os.path.join(os.path.dirname(__file__), '..', 'reports', 'daily-markets.json')
        if os.path.exists(markets_file):
            with open(markets_file, 'r', encoding='utf-8') as f:
                markets = json.load(f)
        else:
            markets = [
                {"question": "Sample market — update with real data", "yes_price": 0.65, "volume": 1000000}
            ]

    text = "🔥 <b>Hot Markets Today</b>\n\n"

    for i, m in enumerate(markets[:5], 1):
        q = m.get('question', 'Unknown')
        yes = m.get('yes_price', 0)
        vol = m.get('volume', 0)
        pct = int(float(yes) * 100)

        text += f"{i}. <b>{q}</b>\n"
        text += f"   📈 Market: {pct}% Yes"
        if vol:
            text += f" | Vol: ${vol:,.0f}"
        text += "\n\n"

    text += '━━━━━━━━━━━━━━━━━━\n'
    text += '🎁 Get $10 free on Polymarket:\n'
    text += f'<a href="{os.getenv("SITE_URL", "https://yoursite.com")}/polymarket/promo-code.html">Claim bonus →</a>\n\n'
    text += '📊 Also grab $10 on Kalshi:\n'
    text += f'<a href="{os.getenv("SITE_URL", "https://yoursite.com")}/kalshi/promo-code.html">Kalshi bonus →</a>'

    return await send_message(text)

async def send_weekly_report(report_data=None):
    """Send weekly performance report"""
    text = "📊 <b>Weekly Report</b>\n\n"

    if report_data:
        text += f"📈 Site visits: {report_data.get('visits', 'N/A')}\n"
        text += f"🔍 Google clicks: {report_data.get('clicks', 'N/A')}\n"
        text += f"💰 Referrals: {report_data.get('referrals', 'N/A')}\n"
        text += f"📊 Revenue: {report_data.get('revenue', 'N/A')}\n"
    else:
        text += "No data provided — run with report data.\n"

    text += f"\n<i>Report date: {datetime.now().strftime('%B %d, %Y')}</i>"

    return await send_message(text)

async def send_trade_alert(trade_data):
    """Send trade execution alert"""
    side = trade_data.get('side', 'BUY')
    market = trade_data.get('market', 'Unknown')
    price = trade_data.get('price', 0)
    amount = trade_data.get('amount', 0)

    emoji = "🟢" if side == "BUY" else "🔴"
    text = f"{emoji} <b>Trade Executed</b>\n\n"
    text += f"Market: {market}\n"
    text += f"Side: {side}\n"
    text += f"Price: ${price}\n"
    text += f"Amount: {amount} shares\n"
    text += f"Total: ${price * amount:.2f}\n"
    text += f"\n<i>{datetime.now().strftime('%H:%M:%S')}</i>"

    return await send_message(text)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python telegram_bot.py [send|markets|report] [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'send':
        text = sys.argv[2] if len(sys.argv) > 2 else "Test message from PredictHub bot"
        asyncio.run(send_message(text))

    elif cmd == 'markets':
        data = None
        if len(sys.argv) > 2:
            with open(sys.argv[2], 'r') as f:
                data = json.load(f)
        asyncio.run(send_daily_markets(data))

    elif cmd == 'report':
        data = None
        if len(sys.argv) > 2:
            with open(sys.argv[2], 'r') as f:
                data = json.load(f)
        asyncio.run(send_weekly_report(data))

    else:
        print(f"Unknown command: {cmd}")
