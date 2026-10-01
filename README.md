# OnlyKSub Clip Factory v2

Drama episode (video + subtitle) -> ready-to-post short clips, in **two layouts** per clip:

| Layout | Output | What it is |
|---|---|---|
| `blur` (A) | 1080x1920 | Whole 16:9 picture kept (nothing cropped), centred on a blurred copy of itself. Subtitles sit in the blurred area, above the TikTok/Reels bottom UI. |
| `wide`  (C) | source size, max 1920x1080 | Original aspect ratio, never upscaled. |

## How it picks moments (no guessing)

1. **Signals (free, local):** per-second audio loudness *relative to the episode itself*, scene cuts, speech density -> one "drama heat" curve.
2. **Candidates:** heat peaks -> windows (15-45 s) that **start on a spoken line / scene cut** and **end right after a spoken line** (cliffhanger end, never mid-sentence).
3. **Rank:** Phase 1 = signal score. Phase 2 = Gemini picks among the pre-snapped candidates *by id* (it never invents timestamps).
4. **Render:** one ffmpeg pass per clip (cut + layout + Sinhala subs + hook title + watermark + loudnorm + encode). No intermediate re-encodes.
5. **QA:** size, duration, audio track, not-black check on every file.

## Run locally

```bash
sudo apt install ffmpeg && pip install -r requirements.txt
python -m clipfactory run --video ep.mp4 --srt ep.srt --drama "My Drama" \
    --source-status permitted --clips 6 --modes blur,wide --workdir work
# outputs: work/clips/clip_01_blur.mp4, clip_01_wide.mp4, ... and work/report.json
# re-run only later stages (reuses saved artifacts):  --from-stage render
```
`--video/--srt` accept local paths or URLs (Pixeldrain share links are resolved automatically).

## Source / rights

`source_status` (`licensed` | `permitted` | `unknown`, default `unknown`) is recorded in `report.json`;
anything not `licensed` is flagged `needs_review: true` so the publish step (Phase 3) holds it for manual approval
instead of auto-posting. Only post content you have the right to use.

## Tests

`python -m pytest -q tests` (needs ffmpeg; builds a synthetic episode with real scene cuts, loud bursts and Sinhala subtitles).

## Roadmap

- [x] Phase 1 - engine (ingest, signals, candidates, render A+C, QA, resume)
- [ ] Phase 2 - Gemini rank (schema-validated) + hook text + captions
- [ ] Phase 3 - publish (Pixeldrain/Drive), webhook to web, Telegram, `clip.yml` workflow, web admin page
