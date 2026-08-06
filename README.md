# onlyksub-clip-factory

Standalone pipeline: drama episode (video link + .srt/.ass) → curiosity-gap
short-form clips, ready for social posting. Independent from the main
subtitle-bot repo — connects to it later via a dispatch step (not yet wired).

## Status: Step 1 + 2 built (download, parse, signal detection, Gemini
moment-detection). Step 3 (cut/reframe/burn/caption) not yet built.

## Setup to test on GitHub Actions

1. Push this repo to GitHub.
2. Repo Settings → Secrets and variables → Actions → add secret:
   `GEMINI_API_KEY` (get one at aistudio.google.com — **use a fresh key,
   never paste a real key into chat**).
3. Go to Actions tab → "Test Clip Pipeline" → Run workflow.
4. Fill in: `video_url` (Pixeldrain link), `srt_url` (a raw subtitle URL —
   e.g. push your .srt to a private Gist and use its raw_url), `drama_name`.
5. Run. Check the job logs and the `pipeline-test-results` artifact for
   parsed dialogue count, scene/audio signal counts, and the final
   Gemini-selected clip moments (JSON with start/end/hook_score/
   cliffhanger_score/emotion_type).

## Scripts

- `scripts/download_video.py` — Pixeldrain/direct video download
- `scripts/download_subtitle.py` — subtitle download from raw URL
- `scripts/parse_subtitle.py` — .srt/.ass → clean timestamped JSON
  (language-agnostic — tested with Sinhala and English)
- `scripts/detect_scenes.py` — FFmpeg scene-change detection (free, local)
- `scripts/detect_audio_spikes.py` — FFmpeg audio volume-spike detection
  (free, local)
- `scripts/gemini_moment_detect.py` — merges all signals, calls Gemini
  3.5 Flash with a curiosity-gap prompt, filters to hook_score>=7 and
  cliffhanger_score>=6

## Not yet built

- Clip cutting (FFmpeg)
- 16:9 → 9:16 reframe with face-tracking (Mediapipe), center-crop fallback
- Subtitle burn with custom font
- Caption generation (FB/TikTok/IG variants)
- Connection back to the main subtitle-bot repo (burn.yml dispatch step)
