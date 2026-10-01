from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import Config
from .models import Job
from .pipeline import STAGES, run_pipeline


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="clipfactory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the pipeline")
    r.add_argument("--job", help="job.json (video, srt, drama_name, source_status, options)")
    r.add_argument("--video")
    r.add_argument("--srt")
    r.add_argument("--drama", default="")
    r.add_argument("--source-status", default=None, choices=["licensed", "permitted", "unknown"])
    r.add_argument("--workdir", default="work")
    r.add_argument("--from-stage", default="ingest", choices=STAGES)
    r.add_argument("--clips", type=int, help="number of clips")
    r.add_argument("--modes", help="comma list: blur,wide")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.job:
        data = json.load(open(args.job, encoding="utf-8"))
        job = Job(video=data["video"], srt=data.get("srt"), drama_name=data.get("drama_name", ""),
                  source_status=data.get("source_status", "unknown"), options=data.get("options", {}))
    elif args.video:
        job = Job(video=args.video, srt=args.srt, drama_name=args.drama)
    else:
        ap.error("give --job or --video")
    if args.source_status:
        job.source_status = args.source_status
    if args.clips:
        job.options["clip_count"] = args.clips
    if args.modes:
        job.options["modes"] = args.modes

    try:
        report = run_pipeline(job, Config.from_overrides(job.options), args.workdir, args.from_stage)
    except Exception as e:  # clean one-line failure instead of a traceback
        msg = str(e).strip().splitlines()
        print(f"ERROR: {msg[-1] if msg else e.__class__.__name__}", file=sys.stderr)
        print("       (re-run with the same --workdir and --from-stage to resume)", file=sys.stderr)
        return 2
    return 0 if report["summary"]["rendered_ok"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
