"""Alternating A/B file with audible markers: raw (A) 2 s, ONE 100 ms silence cut, processed (B) 2 s,
then a DOUBLE cut (100 ms silence, 100 ms sound, 100 ms silence), raw again, and so on. Raw first.
One cut = now B, two cuts = now A. (30 ms cuts were too short to hear clearly.) The markers are
inserted (nothing is overwritten); the timeline just continues after them. The processed file is
aligned to the raw by cross-correlation.
Usage: make_alternating_ab.py <raw> <processed> <output.mp3> [segment seconds=2] [marker ms=100]"""
import subprocess
import sys

import numpy

RATE = 44100
raw_path, processed_path, output_path = sys.argv[1:4]
segment_samples = int(RATE * (float(sys.argv[4]) if len(sys.argv) > 4 else 2.0))
marker_samples = int(RATE * (float(sys.argv[5]) if len(sys.argv) > 5 else 100.0) / 1000)


def decode(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return numpy.frombuffer(out, dtype=numpy.float32)


raw = decode(raw_path)
processed = decode(processed_path)
probe = slice(min(RATE * 5, len(raw) // 4), min(RATE * 15, len(raw) // 2))
max_shift = int(RATE * 0.1)
best_shift = max(range(-max_shift, max_shift + 1),
                 key=lambda s: float(numpy.dot(raw[probe], processed[probe.start + s:probe.stop + s])))
processed = numpy.roll(processed, -best_shift)
length = min(len(raw), len(processed))
silence = numpy.zeros(marker_samples, dtype=numpy.float32)

pieces = []
position = 0
playing_processed = False
while position < length:
    source = processed if playing_processed else raw
    pieces.append(source[position:position + segment_samples])
    position += segment_samples
    if position >= length:
        break
    if playing_processed:  # back to raw: silence, 30 ms of the raw audio, silence
        pieces += [silence, raw[position:position + marker_samples], silence]
        position += marker_samples
    else:  # into processed: one silence
        pieces.append(silence)
    playing_processed = not playing_processed

combined = numpy.concatenate(pieces)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-",
                "-c:a", "libmp3lame", "-b:a", "256k", output_path], input=combined.tobytes(), check=True)
print(f"{output_path}: raw first; tic = processed, tic tic = raw (processed aligned by {best_shift} samples)")
