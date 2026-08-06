"""
Step 2c: Merge dialogue + scene-change + audio-spike signals, then call
Gemini to pick the best curiosity-gap short-form clip moments.

Usage:
    python scripts/gemini_moment_detect.py \
        parsed_dialogue.json scenes.json audio_spikes.json \
        moments_output.json "<drama name>"

Requires env var: GEMINI_API_KEY
"""
import json
import os
import sys

import google.generativeai as genai

CURIOSITY_GAP_PROMPT = """You are selecting short-form clip moments from a K-drama episode.

You are given:
1. DIALOGUE: timestamped subtitle lines (what's being said and when)
2. SCENE_CHANGES: timestamps (seconds) where the visual scene changes sharply
   (these can mark silent/dialogue-free dramatic moments)
3. AUDIO_SPIKES: timestamps (seconds) where the audio gets notably loud
   (shouting, music swells, dramatic cues)

Drama: {drama_name}

GOAL: Each clip must trap the viewer's curiosity so strongly they feel
forced to watch the next episode or clip. Prioritize moments that:
1. End on an unresolved emotional peak (mid-confrontation, right before a
   reveal, right before a reaction shot) - NEVER end on resolution/calm
2. Trigger strong emotion within the first 3 seconds - the hook must land
   immediately
3. Contain a "what happens next" gap - the viewer must NOT get the full
   answer within the clip
4. Combine signals where possible - a moment where dialogue intensity AND
   a scene-change AND an audio-spike all cluster together is a very strong
   candidate, even if you'd miss it from dialogue alone

For each candidate moment (should be 15-45 seconds long), score:
- hook_score (1-10): how strong is the first-3-second grab
- cliffhanger_score (1-10): how unresolved/incomplete does it feel at the
  cut point
- emotion_type: one of (betrayal / romance / shock / grief / suspense /
  comedy)

Return 5-8 candidates. Return ONLY valid JSON, no markdown fences, no
commentary:
[
  {{"start": "HH:MM:SS.mmm", "end": "HH:MM:SS.mmm", "reason": "...",
    "hook_score": 8, "cliffhanger_score": 7, "emotion_type": "betrayal"}},
  ...
]

DIALOGUE:
{dialogue_json}

SCENE_CHANGES (seconds):
{scene_json}

AUDIO_SPIKES (seconds):
{audio_json}
"""


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_moments(dialogue_path, scenes_path, audio_path, drama_name):
    dialogue = load_json(dialogue_path)
    scenes = load_json(scenes_path).get("scene_change_timestamps", [])
    audio = load_json(audio_path).get("audio_spike_timestamps", [])

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY env var not set.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.5-flash")

    prompt = CURIOSITY_GAP_PROMPT.format(
        drama_name=drama_name,
        dialogue_json=json.dumps(dialogue, ensure_ascii=False),
        scene_json=json.dumps(scenes),
        audio_json=json.dumps(audio),
    )

    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    # strip markdown fences if the model added them anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]

    try:
        moments = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"ERROR: could not parse Gemini output as JSON:\n{raw_text}", file=sys.stderr)
        sys.exit(1)

    # filter: only keep strong candidates
    filtered = [
        m for m in moments
        if m.get("hook_score", 0) >= 7 and m.get("cliffhanger_score", 0) >= 6
    ]
    return filtered


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(
            "Usage: python gemini_moment_detect.py <dialogue.json> <scenes.json> "
            "<audio_spikes.json> <output.json> <drama_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    moments = detect_moments(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[5])
    with open(sys.argv[4], "w", encoding="utf-8") as f:
        json.dump(moments, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(moments)} strong candidate moments -> {sys.argv[4]}")
