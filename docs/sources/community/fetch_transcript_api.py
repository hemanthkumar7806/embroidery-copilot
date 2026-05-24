"""
Fetch YouTube transcripts via transcriptapi.com (requests).
Usage: set TRANSCRIPT_API_KEY env var, then:
  python fetch_transcript_api.py
  python fetch_transcript_api.py "https://www.youtube.com/watch?v=VIDEO_ID"
"""
import json
import os
import sys
from urllib.parse import quote

import requests

API_KEY = os.environ.get("TRANSCRIPT_API_KEY", "")
BASE = "https://transcriptapi.com/api/v2/youtube/transcript"

VIDEOS = [
    "https://www.youtube.com/watch?v=3xpLqGkHHQM",   # Digitizing 101
    "https://www.youtube.com/watch?v=Pr_Du4rbxDE",   # How to Digitize a Logo
    "https://www.youtube.com/watch?v=ie9ArCsHtZc",   # Learn to Digitize
    "https://www.youtube.com/watch?v=zwfIuDRhN2k",  # Line Art Embrilliance
]

def fetch(video_url: str) -> dict | None:
    url = f"{BASE}?video_url={quote(video_url, safe='')}&format=json"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    r = requests.get(url, headers=headers, timeout=90)
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return None
    try:
        return r.json()
    except json.JSONDecodeError:
        print(f"  Invalid JSON: {r.text[:200]}", file=sys.stderr)
        return None

def extract_text(data) -> str:
    if not data:
        return ""
    if isinstance(data, dict) and "transcript" in data:
        parts = [seg.get("text", "") for seg in data["transcript"] if isinstance(seg, dict)]
        return " ".join(parts).replace("\n", " ").strip()
    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, dict):
                text = item.get("text") or item.get("utf8") or ""
                if isinstance(item.get("segs"), list):
                    for seg in item["segs"]:
                        parts.append(seg.get("utf8", seg.get("text", "")))
                else:
                    parts.append(text)
        return " ".join(parts).replace("\n", " ").strip()
    if isinstance(data, dict) and "events" in data:
        parts = []
        for ev in data["events"]:
            for seg in ev.get("segs", []):
                u = seg.get("utf8", "")
                if u and u != "\n":
                    parts.append(u)
        return " ".join(parts)
    return str(data)

def main():
    if not API_KEY:
        print("Set TRANSCRIPT_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)
    videos = sys.argv[1:] if len(sys.argv) > 1 else VIDEOS
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for video_url in videos:
        vid = video_url.split("v=")[-1].split("&")[0]
        print(f"Fetching {vid} ...")
        data = fetch(video_url)
        if data is None:
            continue
        text = extract_text(data)
        if not text and isinstance(data, dict):
            text = json.dumps(data)[:5000]
        out_path = os.path.join(out_dir, f"youtube-transcript-{vid}-api.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  Wrote {len(text)} chars -> youtube-transcript-{vid}-api.txt")
        json_path = os.path.join(out_dir, f"youtube-transcript-{vid}-api.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  JSON -> youtube-transcript-{vid}-api.json")

if __name__ == "__main__":
    main()
