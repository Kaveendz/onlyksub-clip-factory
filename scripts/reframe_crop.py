"""
Step 3b: Reframe a 16:9 clip to 9:16 for short-form platforms.

Uses Mediapipe face detection to track the most prominent face and
follow it with a smoothed crop window. Falls back to a plain center-crop
if no face is confidently detected (wide shots, action scenes).

Usage:
    python scripts/reframe_crop.py clip_1.mp4 clip_1_vertical.mp4
"""
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np

mp_face = mp.solutions.face_detection

SMOOTHING_WINDOW = 15


def get_video_dims(path: str) -> tuple[int, int, float]:
    cap = cv2.VideoCapture(path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    return w, h, fps


def detect_face_centers(video_path: str, sample_every: int = 3) -> list[tuple[int, float, float]]:
    cap = cv2.VideoCapture(video_path)
    centers = []
    frame_idx = 0

    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as detector:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_every == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = detector.process(rgb)
                if results.detections:
                    best = max(
                        results.detections,
                        key=lambda d: d.location_data.relative_bounding_box.width
                        * d.location_data.relative_bounding_box.height,
                    )
                    box = best.location_data.relative_bounding_box
                    cx = box.xmin + box.width / 2
                    cy = box.ymin + box.height / 2
                    centers.append((frame_idx, cx, cy))
            frame_idx += 1

    cap.release()
    return centers


def smooth_centers(centers: list[tuple[int, float, float]], total_frames: int) -> list[float]:
    if not centers:
        return []

    per_frame = np.full(total_frames, 0.5)
    last_x = 0.5
    ci = 0
    for f in range(total_frames):
        if ci < len(centers) and centers[ci][0] == f:
            last_x = centers[ci][1]
            ci += 1
        per_frame[f] = last_x

    kernel = np.ones(SMOOTHING_WINDOW) / SMOOTHING_WINDOW
    smoothed = np.convolve(per_frame, kernel, mode="same")
    return smoothed.tolist()


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
    detection_rate = len(centers) / max(1, total_frames / 3)

    if detection_rate < 0.15:
        _center_crop(input_path, output_path, w, h)
        return False

    smoothed = smooth_centers(centers, total_frames)

    median_cx_ratio = float(np.median(smoothed)) if smoothed else 0.5
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
