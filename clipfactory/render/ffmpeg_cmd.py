from __future__ import annotations

from ..config import Config
from ..models import VideoInfo
from ..util import esc_filter_path
from .layout import Layout


def build_cmd(info: VideoInfo, start: float, end: float, layout: Layout, ass_path: str,
              fonts_dir: str, out_path: str, cfg: Config) -> list[str]:
    """ONE ffmpeg pass: seek + cut + (black-bar crop) + layout + subtitles + audio
    normalisation + encode. No intermediate files, so no generation loss."""
    crop = f"crop={info.crop}," if info.crop else ""
    ass = f"ass=filename='{esc_filter_path(ass_path)}':fontsdir='{esc_filter_path(fonts_dir)}'"

    if layout.mode == "blur" and layout.blur_bg:
        graph = (
            f"[0:v]{crop}setsar=1,split=2[a][b];"
            f"[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
            f"gblur=sigma=4:steps=2,scale=1080:1920:flags=bicubic,eq=brightness=-0.10[bg];"
            f"[b]scale=1080:-2:flags=lanczos[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{ass},format=yuv420p[v]"
        )
    elif layout.mode == "blur":  # portrait source: just fill the frame
        graph = (
            f"[0:v]{crop}setsar=1,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop=1080:1920,{ass},format=yuv420p[v]"
        )
    else:  # wide: keep original aspect ratio
        graph = (
            f"[0:v]{crop}setsar=1,scale={layout.out_w}:{layout.out_h}:flags=lanczos,"
            f"{ass},format=yuv420p[v]"
        )

    cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", f"{start:.3f}", "-i", info.path,
           "-t", f"{end - start:.3f}", "-filter_complex", graph, "-map", "[v]"]
    if info.has_audio:
        af = "aresample=48000"
        if cfg.normalize_audio:
            af = "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
        cmd += ["-map", "0:a:0", "-af", af, "-c:a", "aac", "-b:a", cfg.audio_bitrate]
    cmd += ["-c:v", "libx264", "-preset", cfg.preset, "-crf", str(cfg.crf),
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    return cmd
