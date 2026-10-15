"""Detect steady resonances in a voice recording and build one soft, smooth cut curve (0..max dB).

Per the audio-and-vocal-mastering skill (Winer: cut resonances first, broad is more natural, small
moves; EQ can't fix a room, only lean it toward neutral):
1. Voiced 85 ms frames (Hann). Each frame's dB spectrum minus its own 1-octave smooth envelope =
   how far each frequency sticks out locally. Formants and pitch move; a room/voice resonance stays.
2. Per frequency, the MEDIAN over all voiced frames: > 0 only if it sticks out in most of the clip.
3. Keep the positive part, smooth it across log frequency (Gaussian, `--smoothing-octaves` wide).
4. Cut = max_cut * min(1, excess / full_excess_db), only inside [low, high] Hz with soft edges.
5. Applied with ffmpeg firequalizer (dense entries every 1/24 octave), then loudness-matched back
   to the source (ebur128 measure + volume), so an A/B compares tone, not level.

Measure on at least ~60 s of speech, and measure once per voice/book: apply the same curve to every
chapter so the tone never changes mid-book. The defaults are the settings a listener preferred in
A/B tests (deepest cut 1.2 dB, full depth at 3 dB excess, 1/3-octave smoothing, 100 Hz-6 kHz).
Writes <output>.filter.txt (the ffmpeg filter) so the same curve can be reused on other files.

Usage: room_resonance_curve.py <source audio> <output mp3|-> [--max-cut-db 1.2]
       [--smoothing-octaves 0.33] [--full-excess-db 3] [--low-hz 100] [--high-hz 6000]
Needs: python3 with numpy, ffmpeg and ffprobe on PATH."""
import argparse
import re
import subprocess

import numpy

parser = argparse.ArgumentParser()
parser.add_argument("source")
parser.add_argument("output")
parser.add_argument("--max-cut-db", type=float, default=1.2)
parser.add_argument("--smoothing-octaves", type=float, default=1 / 3)
parser.add_argument("--full-excess-db", type=float, default=3.0)
parser.add_argument("--low-hz", type=float, default=100.0)
parser.add_argument("--high-hz", type=float, default=6000.0)
arguments = parser.parse_args()

sample_rate = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                                  "stream=sample_rate", "-of", "csv=p=0", arguments.source],
                                 capture_output=True, text=True, check=True).stdout.strip())
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", arguments.source, "-ac", "1", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
samples = numpy.frombuffer(raw, dtype=numpy.float32)
frame_length = 2048 if sample_rate <= 24000 else 4096
frames = numpy.lib.stride_tricks.sliding_window_view(samples, frame_length)[:: frame_length // 2]
frame_db = 20 * numpy.log10(numpy.sqrt((frames ** 2).mean(axis=1)) + 1e-12)
voiced = frames[frame_db > frame_db.max() - 30]
spectra_db = 20 * numpy.log10(numpy.abs(numpy.fft.rfft(voiced * numpy.hanning(frame_length), axis=1)) + 1e-9)
frequencies = numpy.fft.rfftfreq(frame_length, 1 / sample_rate)

high_hz = min(arguments.high_hz, sample_rate * 0.45)
analysed = numpy.flatnonzero((frequencies >= arguments.low_hz / 2) & (frequencies <= high_hz * 1.5))
log_f = numpy.log2(frequencies[analysed])
stick_out = numpy.empty((len(voiced), len(analysed)))
for column, center in enumerate(log_f):
    neighbours = analysed[numpy.abs(log_f - center) <= 0.5]
    stick_out[:, column] = spectra_db[:, analysed[column]] - spectra_db[:, neighbours].mean(axis=1)
steady_excess = numpy.clip(numpy.median(stick_out, axis=0), 0, None)

sigma = arguments.smoothing_octaves / 2.355  # the width given is the Gaussian's full width at half height
smoothed = numpy.array([
    numpy.average(steady_excess, weights=numpy.exp(-0.5 * ((log_f - center) / sigma) ** 2)) for center in log_f
])

grid = arguments.low_hz * 2 ** (numpy.arange(0, numpy.log2(high_hz / arguments.low_hz) + 1e-9, 1 / 24))
excess_on_grid = numpy.interp(numpy.log2(grid), log_f, smoothed)
edge_taper = numpy.clip(numpy.minimum(numpy.log2(grid / arguments.low_hz), numpy.log2(high_hz / grid)) / 0.5, 0, 1)
cut_db = -arguments.max_cut_db * numpy.clip(excess_on_grid / arguments.full_excess_db, 0, 1) * edge_taper

print(f"{arguments.source}: {sample_rate} Hz, {len(voiced)} voiced frames; curve {arguments.low_hz:.0f}-{high_hz:.0f} Hz, "
      f"max {arguments.max_cut_db} dB, smoothing {arguments.smoothing_octaves:.2f} oct")
print("curve (dB), every 1/3 octave: " + "  ".join(
    f"{f:.0f}:{g:+.2f}" for f, g in zip(grid[::8], cut_db[::8])))
deepest = numpy.argsort(cut_db)[:1]
print(f"deepest cut {cut_db.min():+.2f} dB at {grid[deepest[0]]:.0f} Hz")

entries = ";".join(["entry(0,0)"] + [f"entry({f:.1f},{g:.3f})" for f, g in zip(grid, cut_db)]
                   + [f"entry({sample_rate / 2:.0f},0)"])
curve_filter = f"firequalizer=gain_entry='{entries}'"
with open(arguments.output + ".filter.txt" if arguments.output != "-" else "/dev/null", "w") as filter_file:
    filter_file.write(curve_filter)


def integrated_lufs(path, extra_filter=None):
    chain = (extra_filter + "," if extra_filter else "") + "ebur128"
    stderr = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", chain, "-f", "null", "-"],
                            capture_output=True, text=True).stderr
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", stderr[stderr.rfind("Summary:"):]).group(1))


if arguments.output != "-":
    source_lufs = integrated_lufs(arguments.source)
    curved_lufs = integrated_lufs(arguments.source, curve_filter)
    match_gain = source_lufs - curved_lufs
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", arguments.source, "-af",
                    f"{curve_filter},volume={match_gain:.3f}dB", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "256k",
                    arguments.output], check=True)
    print(f"wrote {arguments.output} (loudness matched to the source: {match_gain:+.2f} dB)")
