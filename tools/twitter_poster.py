"""
PredictHub — Twitter/X Auto-Poster
Usage:
    python tools/twitter_poster.py post "Your tweet text here"
    python tools/twitter_poster.py post "Text" --image path/to/image.png
    python tools/twitter_poster.py thread "Tweet 1" "Tweet 2" "Tweet 3"
    python tools/twitter_poster.py schedule path/to/posts.json
"""

import tweepy
import json
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def get_client():
    return tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_SECRET')
    )

def get_api_v1():
    """V1 API needed for media uploads"""
    auth = tweepy.OAuth1UserHandler(
        os.getenv('TWITTER_API_KEY'),
        os.getenv('TWITTER_API_SECRET'),
        os.getenv('TWITTER_ACCESS_TOKEN'),
        os.getenv('TWITTER_ACCESS_SECRET')
    )
    return tweepy.API(auth)

def post_tweet(text, image_path=None):
    """Post a single tweet, optionally with an image"""
    client = get_client()
    media_ids = None

    if image_path and os.path.exists(image_path):
        api_v1 = get_api_v1()
        media = api_v1.media_upload(image_path)
        media_ids = [media.media_id]

    response = client.create_tweet(text=text, media_ids=media_ids)
    tweet_id = response.data['id']
    print(json.dumps({
        "status": "posted",
        "tweet_id": tweet_id,
        "url": f"https://x.com/i/status/{tweet_id}",
        "text": text[:50] + "...",
        "timestamp": datetime.now().isoformat()
    }, indent=2))
    return tweet_id

def post_thread(tweets):
    """Post a thread (list of tweet texts)"""
    client = get_client()
    previous_id = None
    posted = []

    for i, text in enumerate(tweets):
        response = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=previous_id
        )
        previous_id = response.data['id']
        posted.append({"index": i, "tweet_id": previous_id, "text": text[:50]})
        if i < len(tweets) - 1:
            time.sleep(2)

    print(json.dumps({"status": "thread_posted", "tweets": posted}, indent=2))
    return posted

def schedule_from_file(filepath):
    """Post tweets from a JSON file with delays"""
    with open(filepath, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    results = []
    for post in posts:
        text = post.get('text', '')
        image = post.get('image', None)
        delay = post.get('delay_seconds', 3600)

        if not text:
            continue

        tweet_id = post_tweet(text, image)
        results.append({"tweet_id": tweet_id, "text": text[:50]})

        if post != posts[-1]:
            print(f"Waiting {delay}s before next post...")
            time.sleep(delay)

    return results

def generate_market_tweet(market_data):
    """Generate a tweet about a prediction market"""
    q = market_data.get('question', 'Unknown market')
    yes = market_data.get('yes_price', 0)
    vol = market_data.get('volume', 0)

    pct = int(float(yes) * 100)
    tweet = f"📊 {q}\n\nMarket says: {pct}% chance\n"
    if vol:
        tweet += f"Volume: ${vol:,.0f}\n"
    tweet += "\nTrade it → polymarket.com"
    return tweet

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python twitter_poster.py [post|thread|schedule] [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'post':
        text = sys.argv[2]
        image = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--image' else None
        post_tweet(text, image)

    elif cmd == 'thread':
        tweets = sys.argv[2:]
        post_thread(tweets)

    elif cmd == 'schedule':
        filepath = sys.argv[2]
        schedule_from_file(filepath)

    else:
        print(f"Unknown command: {cmd}")
