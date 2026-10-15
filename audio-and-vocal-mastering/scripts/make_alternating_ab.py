"""Alternating A/B file with audible markers: raw (A) and processed (B) take turns every 2 s, raw
first, on one continuous timeline (the file is exactly as long as the source; nothing is inserted).
Each switch is marked by muting the audio already there:
  into B:  the first 200 ms of the B segment is muted (one cut);
  into A:  the first 450 ms of the A segment is 150 ms muted, 150 ms heard, 150 ms muted (two cuts).
Mute edges get 5 ms fades so the cuts don't click. Shorter or inserted markers sounded like
glitches. The processed file is aligned to the raw by cross-correlation (FIR filters add delay);
loudness-match it to the raw first.
Usage: make_alternating_ab.py <raw> <processed> <output.mp3> [segment s=2] [single ms=200] [double part ms=150]"""
import subprocess
import sys

import numpy

RATE = 44100
raw_path, processed_path, output_path = sys.argv[1:4]
segment_samples = int(RATE * (float(sys.argv[4]) if len(sys.argv) > 4 else 2.0))
single_cut_samples = int(RATE * (float(sys.argv[5]) if len(sys.argv) > 5 else 200.0) / 1000)
double_part_samples = int(RATE * (float(sys.argv[6]) if len(sys.argv) > 6 else 150.0) / 1000)
edge_samples = int(RATE * 0.005)


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

time_index = numpy.arange(length)
playing_processed = (time_index // segment_samples) % 2 == 1
combined = numpy.where(playing_processed, processed[:length], raw[:length])

gain = numpy.ones(length, dtype=numpy.float32)
for segment_start in range(segment_samples, length, segment_samples):
    if (segment_start // segment_samples) % 2 == 1:  # into processed: one cut
        muted_spans = [(segment_start, segment_start + single_cut_samples)]
    else:  # back to raw: cut, heard, cut
        muted_spans = [(segment_start, segment_start + double_part_samples),
                       (segment_start + 2 * double_part_samples, segment_start + 3 * double_part_samples)]
    for start, stop in muted_spans:
        if start >= length:
            continue
        stop = min(stop, length)
        gain[start:stop] = 0
        fade_out_start = max(0, start - edge_samples)  # 1 -> 0 just before the mute
        gain[fade_out_start:start] = numpy.minimum(
            gain[fade_out_start:start], numpy.linspace(1, 0, edge_samples, dtype=numpy.float32)[-(start - fade_out_start):])
        fade_in_stop = min(length, stop + edge_samples)  # 0 -> 1 just after it
        gain[stop:fade_in_stop] = numpy.minimum(
            gain[stop:fade_in_stop], numpy.linspace(0, 1, edge_samples, dtype=numpy.float32)[:fade_in_stop - stop])
combined = combined * gain

subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-",
                "-c:a", "libmp3lame", "-b:a", "256k", output_path], input=combined.tobytes(), check=True)
print(f"{output_path}: raw first; one cut = processed, two cuts = raw (processed aligned by {best_shift} samples)")
