"""
PredictHub — Video Generator (Script → Voice → Video)
Usage:
    python tools/video_maker.py voice "Text to speak" output.mp3
    python tools/video_maker.py video script.txt slides_dir/ output.mp4
    python tools/video_maker.py full "Top 5 Markets This Week"       (end-to-end)
"""

import sys
import os
import json
from datetime import date
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content')

def text_to_audio(text, output_path="output.mp3"):
    """Convert text to speech using ElevenLabs"""
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

    audio = client.text_to_speech.convert(
        text=text,
        voice_id=os.getenv('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB'),  # Default: Adam
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(json.dumps({"status": "audio_created", "path": output_path}))
    return output_path

def make_video_from_slides(audio_path, slides_dir, output_path="final.mp4"):
    """Combine audio with slide images into a video"""
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips

    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    # Get all images sorted
    image_files = sorted([
        os.path.join(slides_dir, f)
        for f in os.listdir(slides_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    ])

    if not image_files:
        print("ERROR: No images found in slides directory")
        return None

    # Calculate duration per slide
    duration_per_slide = audio_duration / len(image_files)

    clips = []
    for img_path in image_files:
        clip = ImageClip(img_path).set_duration(duration_per_slide).resize(width=1920)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(audio)
    video.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        preset='medium'
    )

    print(json.dumps({"status": "video_created", "path": output_path, "duration": audio_duration}))
    return output_path

def make_text_video(text, output_path="text_video.mp4", duration=None):
    """Create a simple video with text overlay on dark background"""
    from moviepy.editor import TextClip, CompositeVideoClip, AudioFileClip, ColorClip

    # Generate audio first
    audio_path = output_path.replace('.mp4', '.mp3')
    text_to_audio(text, audio_path)

    audio = AudioFileClip(audio_path)
    if duration is None:
        duration = audio.duration

    # Dark background
    bg = ColorClip(size=(1920, 1080), color=(15, 14, 23)).set_duration(duration)

    # Split text into chunks for display
    words = text.split()
    chunks = []
    for i in range(0, len(words), 8):
        chunks.append(' '.join(words[i:i+8]))

    chunk_duration = duration / max(len(chunks), 1)
    text_clips = []

    for i, chunk in enumerate(chunks):
        try:
            txt = TextClip(
                chunk,
                fontsize=48,
                color='white',
                font='Arial',
                size=(1600, None),
                method='caption'
            ).set_position('center').set_start(i * chunk_duration).set_duration(chunk_duration)
            text_clips.append(txt)
        except Exception:
            pass  # Skip if TextClip fails (ImageMagick not installed)

    if text_clips:
        video = CompositeVideoClip([bg] + text_clips)
    else:
        video = bg

    video = video.set_audio(audio)
    video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')

    # Clean up temp audio
    if os.path.exists(audio_path):
        os.remove(audio_path)

    print(json.dumps({"status": "text_video_created", "path": output_path}))
    return output_path

def generate_market_script(topic="Top 5 Markets This Week"):
    """Generate a video script about prediction markets"""
    # This would ideally be done by Claude, but here's a template
    script = f"""
{topic}

Hey everyone, let's look at the hottest prediction markets this week.
    """.strip()

    # Try to load real market data
    markets_file = os.path.join(os.path.dirname(__file__), '..', 'reports', 'daily-markets.json')
    if os.path.exists(markets_file):
        with open(markets_file, 'r') as f:
            markets = json.load(f)
        for i, m in enumerate(markets[:5], 1):
            q = m.get('question', 'Unknown')
            yes = float(m.get('yes_price', 0))
            pct = int(yes * 100)
            script += f"\n\nNumber {i}: {q}. The market currently prices this at {pct} percent."

    script += "\n\nThose are the top markets this week. If you want to start trading, check the link in the description for a ten dollar sign-up bonus on Polymarket. See you next time."

    os.makedirs(CONTENT_DIR, exist_ok=True)
    script_path = os.path.join(CONTENT_DIR, f"script-{date.today()}.txt")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    print(f"Script saved: {script_path}")
    return script, script_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python video_maker.py [voice|video|full] [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'voice':
        text = sys.argv[2] if len(sys.argv) > 2 else "Hello, this is a test."
        output = sys.argv[3] if len(sys.argv) > 3 else "output.mp3"
        text_to_audio(text, output)

    elif cmd == 'video':
        if len(sys.argv) < 5:
            print("Usage: python video_maker.py video script.txt slides_dir/ output.mp4")
            sys.exit(1)
        with open(sys.argv[2], 'r') as f:
            text = f.read()
        audio_path = sys.argv[4].replace('.mp4', '.mp3')
        text_to_audio(text, audio_path)
        make_video_from_slides(audio_path, sys.argv[3], sys.argv[4])

    elif cmd == 'full':
        topic = sys.argv[2] if len(sys.argv) > 2 else "Top 5 Prediction Markets This Week"
        script, script_path = generate_market_script(topic)
        output = os.path.join(CONTENT_DIR, f"video-{date.today()}.mp4")
        make_text_video(script, output)

    else:
        print(f"Unknown command: {cmd}")
