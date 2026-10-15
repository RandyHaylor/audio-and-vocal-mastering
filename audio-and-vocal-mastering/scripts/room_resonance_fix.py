"""Room resonance fix: detect a voice recording's steady resonances and cut them with a few real
parametric bell filters (ffmpeg `equalizer`, RBJ peaking biquads).

Detection — a resonance is a frequency that STAYS HIGH while the content changes:
1. Voiced frames only (frame RMS within 30 dB of the loudest), read from the files in order until
   60 s of speech.
2. Cut into 3 s stretches. Each stretch's frames are averaged into one power spectrum (time
   smoothing), put on a log-spaced grid (1/48 octave), and compared with its SURROUNDINGS: the mean
   of the medians of the two flanks, 1/3 to 1 octave below and above. The middle third-octave is
   left out, so a resonance can't raise its own baseline. Then a light 1/12-octave smoothing.
3. A frequency counts only if it sticks out >= 0.5 dB in >= 90% of the stretches. Its strength is
   its 20th percentile across them, so a few loud moments can't inflate it.
   Checks: pink noise, white noise, and pink noise in bursts give 0 bands; a +4 dB bell added to
   pink noise at 500 Hz is found at ~500 Hz with the right width.

Bands:
4. Peaks are found on a 1/3-octave smoothed copy (shape and width: half-height, 1/6..1.5 octave);
   depth is read from the 1/12-octave copy so smoothing doesn't shrink it. The strongest `--bands`
   peaks between --low-hz and --high-hz are kept. Cut = -min(max, strength x multiplier).
5. A close pair (bells overlapping a lot) becomes one wide cut over both plus one narrow, weaker
   POSITIVE bell at the dip between them, fitted to the measured need. The pair is a net dip.
6. Net checks over 20 Hz-20 kHz: never a net boost (positive bells scaled down), and overlapping
   tails never stack past the max (cuts scaled down).

Use: measure ONCE per voice/book (>= 60 s of speech) and apply the same chain to every chapter.
Output: the bands printed, `<out>.filter.txt` (the ffmpeg chain, to reuse), and `<out>` processed
and loudness-matched 75%, so it doesn't feel louder than the raw.
Make the A/B with make_alternating_ab.py.

Usage: room_resonance_fix.py <out.mp3> <wav> [<wav> ...] [--max-cut-db 6] [--multiplier 1]
       [--low-hz 100] [--high-hz 6000] [--bands 5] [--loudness-match 0.75]
Needs: python3 with numpy; ffmpeg and ffprobe on PATH."""
import argparse
import re
import subprocess

import numpy

parser = argparse.ArgumentParser()
parser.add_argument("output")
parser.add_argument("sources", nargs="+")
parser.add_argument("--max-cut-db", type=float, default=6.0)
parser.add_argument("--multiplier", type=float, default=1.0)
parser.add_argument("--low-hz", type=float, default=100.0)
parser.add_argument("--high-hz", type=float, default=6000.0)
parser.add_argument("--bands", type=int, default=5)
parser.add_argument("--loudness-match", type=float, default=0.75)
arguments = parser.parse_args()
MAX_CUT = max(0.0, arguments.max_cut_db)
MULTIPLIER = max(0.0, arguments.multiplier)
SPEECH_SECONDS, STRETCH_SECONDS, PERSISTENCE, PERCENTILE, STICKS_OUT_DB = 60.0, 3.0, 0.9, 20, 0.5
MIN_BW, MAX_BW, POINTS_PER_OCTAVE = 1 / 6, 1.5, 48


def sample_rate_of(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                               "stream=sample_rate", "-of", "csv=p=0", path],
                              capture_output=True, text=True, check=True).stdout.strip())


def voiced_frames(paths):
    rate = sample_rate_of(paths[0])
    frame = 2048 if rate <= 24000 else 4096
    groups = []
    for path in paths:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        samples = numpy.frombuffer(raw, dtype=numpy.float32).astype(numpy.float64)
        if len(samples) >= frame:
            groups.append(numpy.lib.stride_tricks.sliding_window_view(samples, frame)[:: frame // 2])
        frames = numpy.concatenate(groups)
        levels = 20 * numpy.log10(numpy.sqrt((frames ** 2).mean(axis=1)) + 1e-12)
        voiced = frames[levels > levels.max() - 30]
        if len(voiced) * (frame // 2) / rate >= SPEECH_SECONDS:
            break
    return voiced, rate


def persistent_excess(voiced, rate):
    frame = voiced.shape[1]
    per_stretch = max(1, int(STRETCH_SECONDS * rate / (frame // 2)))
    bins = numpy.fft.rfftfreq(frame, 1 / rate)
    log_f = numpy.arange(numpy.log2(arguments.low_hz / 2), numpy.log2(min(arguments.high_hz * 2, rate * 0.48)),
                         1 / POINTS_PER_OCTAVE)
    sigma = (1 / 12) / 2.355 * POINTS_PER_OCTAVE
    offsets = numpy.arange(-int(3 * sigma), int(3 * sigma) + 1)
    kernel = numpy.exp(-0.5 * (offsets / sigma) ** 2)
    kernel /= kernel.sum()
    inner, outer = POINTS_PER_OCTAVE // 3, POINTS_PER_OCTAVE
    window = numpy.hanning(frame)
    stick_outs = []
    for start in range(0, len(voiced) - per_stretch + 1, per_stretch):
        power = (numpy.abs(numpy.fft.rfft(voiced[start:start + per_stretch] * window, axis=1)) ** 2).mean(axis=0)
        db = numpy.interp(log_f, numpy.log2(bins[1:]), 10 * numpy.log10(power[1:] + 1e-20))
        baseline = numpy.array([(numpy.median(db[max(0, i - outer):max(1, i - inner)])
                                 + numpy.median(db[min(len(db) - 1, i + inner):i + outer + 1])) / 2
                                for i in range(len(db))])
        stick_outs.append(numpy.convolve(db - baseline, kernel, mode="same"))
    stick_outs = numpy.array(stick_outs)
    persistent = (stick_outs >= STICKS_OUT_DB).mean(axis=0) >= PERSISTENCE
    strength = numpy.percentile(stick_outs, PERCENTILE, axis=0)
    return log_f, numpy.where(persistent, numpy.clip(strength, 0, None), 0.0)


def bell_db(frequencies, center, q, gain, rate=44100):
    """RBJ cookbook peaking EQ magnitude: what ffmpeg's equalizer (t=q) does."""
    a = 10 ** (gain / 40)
    w0 = 2 * numpy.pi * center / rate
    alpha = numpy.sin(w0) / (2 * q)
    z = numpy.exp(-1j * 2 * numpy.pi * frequencies / rate)
    numerator = (1 + alpha * a) - 2 * numpy.cos(w0) * z + (1 - alpha * a) * z ** 2
    denominator = (1 + alpha / a) - 2 * numpy.cos(w0) * z + (1 - alpha / a) * z ** 2
    return 20 * numpy.log10(numpy.abs(numerator / denominator))


def net_db(frequencies, bands):
    return sum((bell_db(frequencies, f, q, g) for f, q, g in bands), numpy.zeros(len(frequencies)))


def q_for(octaves):
    return numpy.sqrt(2 ** octaves) / (2 ** octaves - 1)


def smoothed(values, log_f, octaves):
    sigma = octaves / 2.355
    return numpy.array([numpy.average(values, weights=numpy.exp(-0.5 * ((log_f - c) / sigma) ** 2)) for c in log_f])


def design(log_f, excess):
    shape, depth = smoothed(excess, log_f, 1 / 3), smoothed(excess, log_f, 1 / 12)
    frequencies = 2 ** log_f
    in_range = (frequencies >= arguments.low_hz) & (frequencies <= arguments.high_hz)
    need = numpy.where(in_range, numpy.minimum(MAX_CUT, depth * MULTIPLIER), 0.0)
    peaks = []
    for i in range(1, len(shape) - 1):
        if in_range[i] and shape[i] >= 0.5 and shape[i] >= shape[i - 1] and shape[i] > shape[i + 1]:
            left = right = i
            while left > 0 and shape[left - 1] > shape[i] / 2 and shape[left - 1] <= shape[left]:
                left -= 1
            while right < len(shape) - 1 and shape[right + 1] > shape[i] / 2 and shape[right + 1] <= shape[right]:
                right += 1
            peaks.append({"i": i, "f": frequencies[i], "strength": float(depth[left:right + 1].max()),
                          "bw": float(numpy.clip(log_f[right] - log_f[left], MIN_BW, MAX_BW))})
    chosen = sorted(sorted(peaks, key=lambda p: -p["strength"])[:arguments.bands], key=lambda p: p["f"])
    bands, paired = [], set()
    for a, b in zip(chosen, chosen[1:]):
        separation = numpy.log2(b["f"] / a["f"])
        if id(a) in paired or id(b) in paired or separation >= 0.75 * (a["bw"] + b["bw"]) / 2:
            continue
        saddle = a["i"] + int(numpy.argmin(shape[a["i"]:b["i"] + 1]))
        wide = (numpy.sqrt(a["f"] * b["f"]), q_for(min(2 * MAX_BW, separation + (a["bw"] + b["bw"]) / 2)))
        narrow = (frequencies[saddle], q_for(max(MIN_BW, separation / 2)))
        span = (frequencies >= a["f"] / 2 ** (a["bw"] / 2)) & (frequencies <= b["f"] * 2 ** (b["bw"] / 2))
        best = None
        for wide_gain in numpy.linspace(-MAX_CUT, 0, 61):
            for positive_gain in numpy.linspace(0, -wide_gain, 31):
                trial = [(*wide, wide_gain), (*narrow, positive_gain)]
                net = net_db(frequencies, trial)
                if net.max() <= 0.0:
                    error = float(((net[span] + need[span]) ** 2).mean())
                    if best is None or error < best[0]:
                        best = (error, trial)
        if best:
            bands += best[1]
            paired.update({id(a), id(b)})
    bands += [(p["f"], q_for(p["bw"]), -min(MAX_CUT, p["strength"] * MULTIPLIER)) for p in chosen if id(p) not in paired]
    check = numpy.geomspace(20, 20000, 2000)
    for _ in range(50):  # never a net boost
        if net_db(check, bands).max() <= 0.0:
            break
        bands = [(f, q, g * 0.9 if g > 0 else g) for f, q, g in bands]
    for _ in range(50):  # overlapping tails never stack past the max
        if net_db(check, bands).min() >= -MAX_CUT - 0.05:
            break
        bands = [(f, q, g * 0.95 if g < 0 else g) for f, q, g in bands]
    return sorted(bands)


def integrated_lufs(path, extra=None):
    stderr = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", (extra + "," if extra else "")
                             + "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", stderr[stderr.rfind("Summary:"):]).group(1))


voiced, rate = voiced_frames(arguments.sources)
log_f, excess = persistent_excess(voiced, rate)
bands = design(log_f, excess)
chain = ",".join(f"equalizer=f={f:.1f}:t=q:w={q:.3f}:g={g:.2f}" for f, q, g in bands) or "anull"
print(f"measured {len(voiced) * (voiced.shape[1] // 2) / rate:.0f} s of speech; {len(bands)} band(s)")
for f, q, g in bands:
    print(f"  {f:7.0f} Hz  Q {q:4.2f}  {g:+.2f} dB")
with open(arguments.output + ".filter.txt", "w") as filter_file:
    filter_file.write(chain)
first = arguments.sources[0]
gain = (integrated_lufs(first) - integrated_lufs(first, chain)) * arguments.loudness_match
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", first, "-af", f"{chain},volume={gain:.3f}dB", "-ar", "44100",
                "-c:a", "libmp3lame", "-b:a", "256k", arguments.output], check=True)
print(f"wrote {arguments.output} (loudness boost {gain:+.2f} dB = {arguments.loudness_match:.0%} of a full match) "
      f"and {arguments.output}.filter.txt")
