"""
Step 3b: Reframe a 16:9 clip to 9:16 for short-form platforms.

Uses OpenCV Haar Cascade face detection to track the most prominent face
and center the crop window on it. Falls back to a plain center-crop if
no face is confidently detected (wide shots, action scenes).

Usage:
    python scripts/reframe_crop.py clip_1.mp4 clip_1_vertical.mp4
"""
import subprocess
import sys

import cv2
import numpy as np

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def get_video_dims(path: str) -> tuple[int, int, float]:
    cap = cv2.VideoCapture(path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    return w, h, fps


def detect_face_centers(video_path: str, sample_every: int = 5) -> list[tuple[int, float, float]]:
    cap = cv2.VideoCapture(video_path)
    centers = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_every == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            faces = FACE_CASCADE.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            if len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                cx = (fx + fw / 2) / w
                cy = (fy + fh / 2) / h
                centers.append((frame_idx, cx, cy))
        frame_idx += 1

    cap.release()
    return centers


def reframe_video(input_path: str, output_path: str) -> bool:
    w, h, fps = get_video_dims(input_path)
    target_w = int(h * 9 / 16)

    if target_w >= w:
        _center_crop(input_path, output_path, w, h)
        return False

    cap = cv2.VideoCapture(input_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    centers = detect_face_centers(input_path)
    sampled_frames = max(1, total_frames // 5)
    detection_rate = len(centers) / sampled_frames

    if detection_rate < 0.15:
        _center_crop(input_path, output_path, w, h)
        return False

    median_cx_ratio = float(np.median([c[1] for c in centers]))
    crop_x = int(median_cx_ratio * w - target_w / 2)
    crop_x = max(0, min(w - target_w, crop_x))

    _crop_at_x(input_path, output_path, crop_x, target_w, h)
    return True


def _center_crop(input_path: str, output_path: str, w: int, h: int) -> None:
    target_w = int(h * 9 / 16)
    crop_x = max(0, (w - target_w) // 2)
    _crop_at_x(input_path, output_path, crop_x, target_w, h)


def _crop_at_x(input_path: str, output_path: str, crop_x: int, crop_w: int, crop_h: int) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR reframing {output_path}:\n{result.stderr[-1000:]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reframe_crop.py <input_clip.mp4> <output_clip.mp4>", file=sys.stderr)
        sys.exit(1)

    used_face_tracking = reframe_video(sys.argv[1], sys.argv[2])
    method = "face-tracking" if used_face_tracking else "center-crop fallback"
    print(f"OK: reframed -> {sys.argv[2]} ({method})")
