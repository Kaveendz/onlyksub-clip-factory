"""
Step 3d: Generate 3 platform-tuned captions (Facebook, TikTok, Instagram)
for a clip, using its moment context (reason, emotion_type, drama name).

Usage:
    python scripts/generate_captions.py \
        "<drama_name>" "<reason>" "<emotion_type>" captions_output.json
"""
import json
import os
import sys
import time

from google import genai
from google.genai.errors import ClientError

CAPTION_PROMPT = """You are writing short-form social captions for a K-drama clip.

Drama: {drama_name}
Clip content: {reason}
Emotion: {emotion_type}

Write 3 captions, each under 150 characters, plus one comment-bait
question to encourage replies:

1. facebook: CTA-heavy, encourages watching the full episode on
   OnlyKSub (mention "watch the full episode on OnlyKSub" naturally)
2. tiktok: slang-heavy, punchy, trend-aware tone
3. instagram: slightly more polished/aesthetic tone
4. comment_bait: one short question about this moment to prompt comments

Return ONLY valid JSON, no markdown fences, no commentary:
{{"facebook": "...", "tiktok": "...", "instagram": "...", "comment_bait": "..."}}
"""


def generate_captions(drama_name: str, reason: str, emotion_type: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY env var not set.", file=sys.stderr)
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    prompt = CAPTION_PROMPT.format(drama_name=drama_name, reason=reason, emotion_type=emotion_type)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

    last_err = None
    response = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except ClientError as e:
            last_err = e
            if getattr(e, "code", None) == 429:
                wait = 20 * (attempt + 1)
                print(f"Rate limited, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    if response is None:
        print(f"ERROR: Gemini call failed after retries: {last_err}", file=sys.stderr)
        sys.exit(1)

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"ERROR: could not parse Gemini output as JSON:\n{raw_text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python generate_captions.py <drama_name> <reason> <emotion_type> <output.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    captions = generate_captions(sys.argv[1], sys.argv[2], sys.argv[3])
    with open(sys.argv[4], "w", encoding="utf-8") as f:
        json.dump(captions, f, ensure_ascii=False, indent=2)
    print(f"OK: captions written -> {sys.argv[4]}")
