#!/usr/bin/env python3
"""Select and hash-verify the one supported Whisper model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime import LOCK_PATH, StrategyMError, atomic_json, load_json, sha256_file


def select_file() -> Path:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    value = filedialog.askopenfilename(
        title="Select whisper-medium-2512-ft-best-ggml.bin",
        filetypes=(("GGML model", "*.bin"), ("All files", "*.*")),
    )
    root.destroy()
    if not value:
        raise StrategyMError("Whisper model selection was cancelled")
    return Path(value).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = load_json(LOCK_PATH)["whisper"]
    path = args.path.expanduser().resolve() if args.path else select_file()
    if path.name != lock["model_filename"]:
        raise StrategyMError(f"wrong model filename: {path.name}")
    digest = sha256_file(path)
    if digest != lock["model_sha256"]:
        raise StrategyMError("Whisper model SHA-256 does not match the release lock")
    record = {"absolute_path": str(path), "filename": path.name, "sha256": digest, "bytes": path.stat().st_size}
    atomic_json(args.output, record)
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
