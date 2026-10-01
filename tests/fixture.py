"""Synthetic 150 s 'episode': 15 hue-shifted 10 s segments (= 14 scene cuts), quiet tone with
loud bursts at 40-45 s / 90-95 s / 140-145 s, and Sinhala dialogue climaxing at those bursts."""
from __future__ import annotations

import subprocess
from pathlib import Path

SRT = """1
00:00:12,000 --> 00:00:15,000
අද උදේ මොකද වුණේ?

2
00:00:30,000 --> 00:00:33,000
ඔයා මොනවද මේ කරන්නේ?

3
00:00:34,000 --> 00:00:37,500
මම ඔයාට හැමදේම කිව්වානේ.

4
00:00:38,500 --> 00:00:41,000
නෑ, ඔයා මට බොරු කිව්වා!

5
00:00:41,500 --> 00:00:44,300
ඒ කාන්තාව ඔයාගේ අම්මා නෙවෙයි...

6
00:00:62,000 --> 00:00:65,000
I need to tell you something.

7
00:01:20,000 --> 00:01:23,000
ඔයාට මතකද අපි මුලින්ම හමු වුණු දවස?

8
00:01:24,000 --> 00:01:27,000
ඔව්... ඒත් දැන් ඒකෙන් වැඩක් නෑ.

9
00:01:28,000 --> 00:01:31,000
මම යනවා. ආයෙත් එන්නේ නෑ.

10
00:01:32,000 --> 00:01:34,800
ඔයා මොකක්ද කිව්වේ? <i>නැවතිය!</i>
"""


def make_video(path: str | Path, dur: int = 150, w: int = 1280, h: int = 720, pad_bars: bool = False) -> str:
    inputs, labels = [], []
    segs = dur // 10
    for i in range(segs):
        # alternate two very different pictures so the cuts are real (a hue shift alone is not a cut)
        src = f"testsrc2=s={w}x{h}:r=25:d=10" if i % 2 == 0 else f"smptebars=s={w}x{h}:r=25:d=10"
        inputs += ["-f", "lavfi", "-i", src]
        labels.append(f"[{i}:v]")
    audio = (f"aevalsrc=0.04*sin(2*PI*220*t)*(1+6*between(mod(t\\,50)\\,40\\,45)):s=48000:d={dur}")
    inputs += ["-f", "lavfi", "-i", audio]
    vf = "".join(labels) + f"concat=n={segs}:v=1:a=0[v0]"
    if pad_bars:  # simulate letterbox: shrink picture and pad with black
        vf += f";[v0]scale={w}:{int(h * 0.75)},pad={w}:{h}:0:{int(h * 0.125)}:black[v]"
    else:
        vf += ";[v0]null[v]"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", vf, "-map", "[v]",
           "-map", f"{segs}:a", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-g", "50",
           "-c:a", "aac", "-shortest", str(path)]
    subprocess.run(cmd, check=True)
    return str(path)


def make_srt(path: str | Path) -> str:
    # fix the intentionally "00:00:62" style times into valid ones
    fixed = SRT.replace("00:00:62,000 --> 00:00:65,000", "00:01:02,000 --> 00:01:05,000")
    Path(path).write_text(fixed, encoding="utf-8")
    return str(path)
