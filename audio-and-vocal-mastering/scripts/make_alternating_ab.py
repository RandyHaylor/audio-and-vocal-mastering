"""Alternating A/B file marked by a quiet sine beep mixed over the audio (nothing is muted or
inserted; the file keeps the source's length). Raw (A) and processed (B) take turns every 4 s,
raw first:
  into B: one beep (200 ms);
  into A: beep beep (150 ms beep, 150 ms gap, 150 ms beep).
Beeps have 10 ms fades and sit `--below-speech-db` under the speech level (the 90th percentile of
50 ms RMS), so they are heard but stay quiet. A beep is heard even in a pause, where a muted cut
is not. The processed file is aligned to the raw by cross-correlation (FIR filters add delay);
loudness-match it to the raw first.
Usage: make_alternating_ab.py <raw> <processed> <output.mp3> [--segment-seconds 4] [--frequency 660]
       [--below-speech-db 10]"""
import argparse
import subprocess

import numpy

parser = argparse.ArgumentParser()
parser.add_argument("raw")
parser.add_argument("processed")
parser.add_argument("output")
parser.add_argument("--segment-seconds", type=float, default=4.0)
parser.add_argument("--frequency", type=float, default=660.0)
parser.add_argument("--below-speech-db", type=float, default=10.0)
parser.add_argument("--single-ms", type=float, default=200.0)
parser.add_argument("--double-part-ms", type=float, default=150.0)
arguments = parser.parse_args()
RATE = 44100


def decode(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return numpy.frombuffer(out, dtype=numpy.float32)


raw = decode(arguments.raw)
processed = decode(arguments.processed)
probe = slice(min(RATE * 5, len(raw) // 4), min(RATE * 15, len(raw) // 2))
max_shift = int(RATE * 0.1)
best_shift = max(range(-max_shift, max_shift + 1),
                 key=lambda s: float(numpy.dot(raw[probe], processed[probe.start + s:probe.stop + s])))
processed = numpy.roll(processed, -best_shift)
length = min(len(raw), len(processed))
segment_samples = int(RATE * arguments.segment_seconds)
playing_processed = (numpy.arange(length) // segment_samples) % 2 == 1
combined = numpy.where(playing_processed, processed[:length], raw[:length]).astype(numpy.float64)

window = RATE // 20
window_rms = numpy.sqrt((raw[: length // window * window].reshape(-1, window).astype(numpy.float64) ** 2).mean(axis=1))
speech_rms = numpy.percentile(window_rms, 90)
beep_peak = speech_rms * 10 ** (-arguments.below_speech_db / 20) * numpy.sqrt(2)


def beep(duration_ms):
    samples = int(RATE * duration_ms / 1000)
    tone = numpy.sin(2 * numpy.pi * arguments.frequency * numpy.arange(samples) / RATE) * beep_peak
    fade = min(int(RATE * 0.01), samples // 2)
    envelope = numpy.ones(samples)
    envelope[:fade] = numpy.linspace(0, 1, fade)
    envelope[-fade:] = numpy.linspace(1, 0, fade)
    return tone * envelope


single = beep(arguments.single_ms)
double_part = int(RATE * arguments.double_part_ms / 1000)
double = numpy.concatenate([beep(arguments.double_part_ms), numpy.zeros(double_part), beep(arguments.double_part_ms)])
for segment_start in range(segment_samples, length, segment_samples):
    marker = single if (segment_start // segment_samples) % 2 == 1 else double
    stop = min(length, segment_start + len(marker))
    combined[segment_start:stop] += marker[:stop - segment_start]

subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-",
                "-c:a", "libmp3lame", "-b:a", "256k", arguments.output],
               input=combined.astype(numpy.float32).tobytes(), check=True)
print(f"{arguments.output}: raw first; beep = processed, beep beep = raw; {arguments.frequency:.0f} Hz, "
      f"{arguments.below_speech_db:.0f} dB under speech")
