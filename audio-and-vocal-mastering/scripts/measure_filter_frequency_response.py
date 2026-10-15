"""Frequency response of an ffmpeg filter chain: white noise in, spectra out vs in, printed in
1/3-octave bands (dB change). A neutral chain must print ~0 everywhere.
Usage: measure_filter_frequency_response.py "<filter chain>" | @<file holding the chain> [label] [sample rate]
Rule 5 of the skill: run it with every amount at neutral first (must print ~0.00), then with the
real settings to see what the chain actually does."""
import subprocess
import sys

import numpy

chain = open(sys.argv[1][1:]).read().strip() if sys.argv[1].startswith("@") else sys.argv[1]
label = sys.argv[2] if len(sys.argv) > 2 else chain[:60]
RATE = int(sys.argv[3]) if len(sys.argv) > 3 else 24000
noise = (numpy.random.default_rng(1).standard_normal(RATE * 30) * 0.05).astype(numpy.float32)
out = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-", "-af", chain,
                      "-ac", "1", "-f", "f32le", "-"], input=noise.tobytes(), capture_output=True, check=True).stdout
processed = numpy.frombuffer(out, dtype=numpy.float32)
length = min(len(noise), len(processed))


def band_powers(samples):
    spectrum = numpy.abs(numpy.fft.rfft(samples[:length])) ** 2
    frequencies = numpy.fft.rfftfreq(length, 1 / RATE)
    centers = [63 * 2 ** (i / 3) for i in range(30) if 63 * 2 ** (i / 3) * 2 ** (1 / 6) < RATE / 2]
    return centers, [spectrum[(frequencies >= c / 2 ** (1 / 6)) & (frequencies < c * 2 ** (1 / 6))].sum()
                     for c in centers]


centers, before = band_powers(noise)
_, after = band_powers(processed)
changes = [10 * numpy.log10(a / b) for a, b in zip(after, before)]
print(f"{label}: range {min(changes):+.2f} .. {max(changes):+.2f} dB")
print("  " + "  ".join(f"{c:.0f}:{d:+.2f}" for c, d in zip(centers, changes)))
