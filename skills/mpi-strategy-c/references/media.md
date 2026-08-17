# Audio and video route

Use the document workflow after transcription, with these additions:

1. Verify `READY.json` binds the selected model filename and SHA-256. Extract
   audio with FFmpeg when the input is video.
2. Invoke `transcribe_media.py` through `strategy_c.py run-media` so the
   whisper.cpp executable, selected model hash, media input hash, output hash,
   timing, and exit code are receipted. The wrapper may call FFmpeg and
   whisper.cpp only; it contains no speech recognizer.
3. Preserve raw timestamped Chinese and uncertainty markers. Ask the user only
   about materially ambiguous segments, and record their answers. Never invent
   missing speech.
4. Run toolkit `source2dj.py` as `source_extraction` and freeze
   `source-map.json` before Flash.
5. After the final target, run toolkit `gen-subtitles.py` as
   `subtitle_generation`, then `check-subtitles.py --strict` as `subtitle_qa`.
6. Finalize with `--input-type media`. Deliver Chinese, English, and bilingual
   SRT/VTT in addition to the normal document outputs.
