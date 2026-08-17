#!/usr/bin/env python3
"""Run locked whisper.cpp and emit raw Chinese plus a timestamp map."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from runtime import StrategyCError, atomic_json, atomic_text, load_ready, managed_root, sha256_file


def seconds(segment: dict, side: str) -> float:
    offsets = segment.get("offsets", {})
    if side in offsets:
        return float(offsets[side]) / 1000.0
    stamp = segment.get("timestamps", {}).get("from" if side == "from" else "to")
    if not isinstance(stamp, str):
        raise StrategyCError("Whisper segment has no usable timestamp")
    parts = stamp.replace(",", ".").split(":")
    if len(parts) != 3:
        raise StrategyCError("Whisper timestamp format is invalid")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("media", type=Path)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    media = args.media.expanduser().resolve()
    project = args.project.expanduser().resolve()
    if not media.is_file() or not project.is_dir():
        raise StrategyCError("media file or project directory is missing")
    ready = load_ready(managed_root())
    whisper = ready["whisper"]
    model = Path(whisper["model_absolute_path"])
    executable = Path(whisper["executable_absolute_path"])
    if sha256_file(model) != whisper["model_sha256"] or sha256_file(executable) != whisper["executable_sha256"]:
        raise StrategyCError("Whisper model or executable hash changed")
    with tempfile.TemporaryDirectory(prefix="mpi-strategy-c-media-") as directory:
        temporary = Path(directory)
        wav = temporary / "audio.wav"
        converted = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", str(media), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-y", str(wav)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if converted.returncode:
            raise StrategyCError("FFmpeg audio extraction failed")
        output_base = temporary / "whisper"
        recognized = subprocess.run(
            [str(executable), "-m", str(model), "-f", str(wav), "-l", "zh", "-ojf", "-of", str(output_base)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if recognized.returncode:
            raise StrategyCError("whisper.cpp transcription failed")
        payload_path = output_base.with_suffix(".json")
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StrategyCError("whisper.cpp did not produce valid JSON") from exc
    transcription = payload.get("transcription")
    if not isinstance(transcription, list) or not transcription:
        raise StrategyCError("Whisper transcription is empty")
    lines: list[str] = []
    segments: list[dict] = []
    ambiguities: list[dict] = []
    for segment in transcription:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        lines.append(text)
        start = seconds(segment, "from")
        end = seconds(segment, "to")
        if end <= start:
            raise StrategyCError("Whisper segment has non-positive duration")
        segments.append({"id": f"S{len(segments) + 1}", "start": start, "end": end, "source_line": len(lines)})
        reasons = []
        if number(segment.get("avg_logprob")) < -1.0:
            reasons.append("low_average_log_probability")
        if number(segment.get("no_speech_prob")) > 0.5:
            reasons.append("high_no_speech_probability")
        if "[" in text or "？" in text:
            reasons.append("transcript_uncertainty_marker")
        if reasons:
            ambiguities.append({"segment_id": segments[-1]["id"], "start": start, "end": end, "text": text, "reasons": reasons, "user_resolution": None})
    if not lines:
        raise StrategyCError("Whisper transcription contains no text")
    raw = project / "whisper-raw.txt"
    atomic_text(raw, "\n".join(lines) + "\n")
    atomic_json(project / "source-map.json", {"schema_version": 1, "media_sha256": sha256_file(media), "segments": segments})
    atomic_json(project / "transcription-ambiguities.json", {"schema_version": 1, "items": ambiguities})
    print(f"Transcribed {len(lines)} timestamped Chinese segments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
