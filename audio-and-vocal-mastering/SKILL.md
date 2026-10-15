---
name: audio-and-vocal-mastering
description: Studio basics for EQ, compression, limiting, loudness and room resonances, for audio in general and spoken voice / narration (including TTS) in particular, grounded in Ethan Winer's writing, plus measured ffmpeg pitfalls. Load before proposing, building or judging any audio post-processing (mastering chains, EQ or resonance curves, compressor settings, loudness targets, A/B samples).
---

# Audio and vocal mastering: EQ, compression, limiting, loudness

The reference is **Ethan Winer** (ethanwiner.com; *The Audio Expert*, ch. 9 Dynamics
Processors, ch. 10 Frequency Processors). Lean on him first. Other sources fill gaps only, and
are marked as such. Quotes below are from his articles, fetched 2026-10-15.

## Ground rules (how to work on audio here)

1. **The user's ears are the fact.** I can't listen. A measurement that disagrees with what the
   user hears means my measurement is incomplete. Look wider; never argue.
2. **Small moves.** Mastering is "final touch EQ'ing" (Winer, *Second Guessing Mastering
   Engineers*). His own mastering move there: "I boosted 5 KHz and above by 1 dB". Broad tonal
   moves stay at 1–1.5 dB. The exception is a cut on a **measured, steady resonance**: it may be as
   deep as the resonance sticks out (up to 6 dB in the room resonance fix below), because it
   removes something that shouldn't be there. A tool that moves bands by several dB *without* such
   evidence is broken, not "strong".
3. **Do nothing unless it is needed.** "Every track or complete mix does not need compression!"
   (*Compressors*). Decide *why* each stage is there.
4. **Compare fairly.** Level-match every A/B: "people will generally pick the brighter (or just
   louder) version as sounding better", and "Just because something sounds 'better,' it is not
   necessarily higher fidelity" (*Dispelling Popular Audio Myths*). Winer: the switch "be performed
   very quickly", in under a second, not minutes apart. So give the listener **alternating A/B
   files**, not separate files:
   - one file that switches between raw and processed every **4 s**, **raw first** (2 s was too
     short to judge);
   - processed time-aligned to raw by cross-correlation (filters can add delay);
   - **a quiet beep marks each switch**, mixed over the audio: one **660 Hz** beep (200 ms) going
     into processed, beep beep (150 ms, 150 ms gap, 150 ms) going back to raw, **10 dB under the
     speech level**, 10 ms fades. Nothing is muted or inserted, so the file keeps the source's
     length. (Tried and dropped: crossfades hide the switch; muted cuts are missed when the speech
     pauses, and shorter cuts sound like glitches; inserted gaps feel jolting.)
   - **Loudness matching for a cut-only fix: match about 75%, not 100%.** When a fix removes boom,
     full matching turns the processed side up so far that it "FEELS like you made the person
     louder" (the listener). For other processing, start from a full match.

   Say what changed, and which segment is which.

   Script: `scripts/make_alternating_ab.py <raw> <processed> <out.mp3> [--segment-seconds 4]
   [--frequency 660] [--below-speech-db 10]`. Give it a processed file that is already
   loudness-matched; `room_resonance_fix.py` writes one.
5. **Measure the tool before trusting it.** Before any filter chain is used, run white or pink noise
   through it with every processing amount at zero (ratio 1:1, gain 0) and print the response in
   1/3 octaves. A neutral setting must come out within ~0.5 dB everywhere. Only then judge
   what the actual settings do. Script: `scripts/measure_filter_frequency_response.py "<chain>"`
   (or `@file`).
6. **Look it up, don't recall it.** Frequency ranges, ffmpeg filter behaviour and standards are
   checked against a source before they are stated as fact.

## EQ (Winer, *The Art of Equalization*; *Phase Shift in Equalizers*)

- **Cut resonances first:** "Eliminating these midrange resonances will often improve the sound
  and minimize a need to boost highs and/or lows."
- **Finding a problem frequency:** boost a narrow band a lot (he says 10–15 dB) and sweep
  ~100 Hz–2 kHz to find the worst spot, then *cut* there in small steps. (For automatic work,
  the measurement replaces the sweep; the small cut stays.)
- **Bandwidth:** broad "is often more natural sounding than narrow bandwidths". Avoid narrow
  boosts. Narrow is for a specific ringing resonance.
- **Voice, his chart:** cut "Scratchy at 2 KHz. Nasal at 1 KHz. Popping Ps below 80 Hz."; boost
  "Clarity above 3 KHz", "Body at 200-400 Hz". Harshness: "around 2 to 4 KHz".
- **Other sources, his chart:**
  - piano: cut "Tinny at 1-2 KHz. Boomy at 300 Hz."; boost "Presence at 5 KHz", "Bottom at 100 Hz";
  - acoustic guitar: cut "Tinny at 2-3 KHz. Boomy at 200 Hz."; boost "Sparkle above 5 KHz", "Full at 125 Hz";
  - electric guitar: cut "Muddy below 80 Hz."; boost "Clarity at 3 KHz", "Bottom at 125 Hz";
  - electric bass: cut "Thin at 1 KHz", "Boomy at 125 Hz"; boost "Growl at 600 Hz";
  - string bass: cut "Hollow at 600 Hz. Boomy at 200 Hz.";
  - kick: cut "Floppy at 600 Hz. Boomy below 80 Hz."; boost "Bottom at 60-125 Hz";
  - snare: cut "Annoying at 1 KHz."; boost "Crisp above 2 KHz", "Full at 150-200 Hz";
  - toms: cut "Boomy at 300 Hz."; boost "Bottom at 80-200 Hz";
  - cymbals: cut "Annoying at 1 KHz."; boost "Sparkle above 5 KHz";
  - horns and strings: cut "Scratchy at 3 KHz. Honky at 1 KHz. Muddy below 120 Hz."; boost
    "Clarity above 2 KHz"; strings are "lush at 400-600 Hz".
- **Mixes:** keep bass and kick "a bit on the thin side" so a mix doesn't get tubby when played
  loud.
- **Boxy (gap-filled from other guides, not Winer):** commonly 250–700 Hz, often 300–600 Hz.
  Typical cut 2–3 dB with Q ≈ 2–3, or a dynamic EQ/one band that cuts only when that range swells.
  Over-cutting thins the voice. Winer's own "body" (200–400 Hz) overlaps it, so cut gently.
- **High-pass:** low-cut for proximity boom, plosives, rumble ("below 80 Hz" for voice).
- **Don't boost where there's no content:** "Boosting high treble on an instrument with little
  output in that region will do nothing but add hiss." Check the sample rate first: 24 kHz audio
  (common for TTS) has nothing above 12 kHz.
- **Phase:** "it's the response change that you hear, not the phase shift itself." Ordinary
  (minimum-phase) EQ is fine. Don't reach for linear-phase to fix tone.

## Rooms and resonances (Winer, *Acoustics FAQ*)

- Boxiness in recordings is mostly **comb filtering** from early reflections ("the boxy sounding
  response peaks and dips known as comb filtering") and small-room reflections ("just make the
  room boxy sounding").
- **EQ cannot really fix a room:** "no single EQ curve can give a flat response everywhere", "EQ
  cut to reduce a peak will not reduce the peak's acoustic ringing"; only "low frequency peaks
  (only) caused by natural room resonance" can be helped a little, in moderation.
- So an automatic "detect the room" fix only **cuts the real, steady resonances, gently**. It is
  not a multiband EQ that flattens everything.

### Room resonance fix: the canonical method (settled in A/B listening tests, 2026-10)

Script: `scripts/room_resonance_fix.py <out.mp3> <wav> [<wav> …] [--max-cut-db 6] [--multiplier 1]
[--low-hz 100] [--high-hz 6000] [--bands 5] [--loudness-match 0.75]`. It prints the bands, writes
the processed file (75% loudness-matched), and saves the ffmpeg chain as `<out>.filter.txt` to
apply unchanged to every other file.

**Detection: a resonance is a frequency that stays high while the content changes.**
1. Voiced frames only (frame RMS within 30 dB of the loudest), read from the files in order until
   **60 s of speech**.
2. Cut into **3 s stretches**. In each, average the frames' power (time smoothing), put it on a
   log-spaced grid (1/48 octave), and compare each frequency with its **surroundings only**: the
   mean of the medians of the two flanks, 1/3 to 1 octave below and above. Then smooth lightly
   (1/12 octave).
3. It counts only if it sticks out ≥ 0.5 dB in **≥ 90% of the stretches**. Its strength is the
   **20th percentile** across stretches, so loud moments can't inflate it.

**Bands: a few real parametric bells** (ffmpeg `equalizer`), not a drawn curve.
4. Peaks and widths come from a 1/3-octave smoothed copy; depth from the 1/12-octave copy. Keep
   the strongest **5** between **100 Hz and 6 kHz**. Cut = −min(**6 dB**, strength × **1**).
5. **Close pairs** (bells overlapping a lot) become one wide cut over both plus one narrow, weaker
   **positive** bell at the dip between them, fitted to the measured need. The pair is a net dip.
6. **Net checks:** never a net boost anywhere, and overlapping tails never stack past the max.

**Using it:**
- Measure **once per book/voice** (≥ 60 s of speech, continuing into later chapters if the first
  is short) and apply the **same chain to every chapter**, so the tone never changes mid-book.
- Always give an alternating A/B (rule 4) before adopting it.
- What the listener hears decides. Change `--multiplier` (strength) or `--low-hz` and listen again.

**Validation (keep these as tests if you change the method):**
- pink noise, white noise, and pink noise in speech-like bursts → **0 bands**;
- a +4 dB bell added to pink noise at 500 Hz → found at ~500 Hz with about the same width;
- the real ffmpeg chain, measured on noise, matches the planned response within ~0.3 dB.

**Mistakes made on the way (don't repeat them):**
- *Median of per-frame stick-out:* found "resonances" in pink noise. Random per-frame variation
  plus a ~0.9 dB bias passed as peaks.
- *Baseline = the whole octave around the frequency:* a resonance's own skirts lifted its baseline,
  so +4 dB measured as about +2.
- *Persistence test before any frequency smoothing, then heavy smoothing:* real peaks broke into
  scattered points and were averaged away, so one voice got no bands.
- *Half-second stretches:* rejected real resonances. 3 s stretches sounded right to the listener.
- *A 3 dB max:* nearly every band stopped at the max, so the limit decided the depth, not the
  detection. 6 dB with ×1 sounded right.
- *A drawn curve with hundreds of points* (`firequalizer`): it isn't what Winer means by EQ, and it
  can follow every bump. Use a few parametric bells.
- *Cutting 3–5 kHz is Winer's clarity range,* but here the listener preferred keeping 100 Hz–6 kHz.
  Listen for dullness.
- *Full cuts at about 100–120 Hz on male voices* may be the voice's own pitch. If it sounds thinner,
  raise `--low-hz` to about 150.

**What it found (five TTS books, four voices):** 2–5 bands per book. Two books read by the same
voice shared their bands. Different voices got different frequencies.

### Example requests (how a user asks an agent)

> "Use the audio-and-vocal-mastering skill. Run the room resonance fix on `chapter-01.wav` and make
> me an A/B comparison file."

> "Detect the room resonances on the first minute of speech from these narration files, apply the
> fix, and give me an A/B so I can hear the difference."

What the agent does:
1. `scripts/room_resonance_fix.py fixed.mp3 chapter-01.wav [chapter-02.wav …]`, then report the
   bands found.
2. `scripts/make_alternating_ab.py chapter-01.wav fixed.mp3 ab.mp3`, then give the user the file and
   explain the beeps (one = processed, two = raw; raw first, every 4 s).
3. The user listens and says what they hear. Re-run with changed settings if asked, for example
   `--multiplier 0.7` or `--low-hz 150`.
4. When it's settled, apply `fixed.mp3.filter.txt` unchanged to every chapter:
   `ffmpeg -i chapter-NN.wav -af "$(cat fixed.mp3.filter.txt)" out-NN.wav`.

## Compression and limiting (Winer, *Compressors*)

- **Threshold:** "Below that volume the compressor does nothing." Lower it until the meter shows
  **~2–6 dB gain reduction on the loud parts**.
- **Ratio:** 2:1 = 2 dB over threshold gives 1 dB out. "5:1 or greater" is a limiter; the ratio is
  "the only distinction between a compressor and a limiter".
- **Attack:** fastest to catch overloads. 20–50 ms keeps the start of notes/words punchy.
- **Release:** "fairly long - one second or more" so it isn't heard. Start 0.5–1 s. Short release
  means pumping/breathing, and "distortion increases at low frequencies".
- **Soft knee** eases in. **Makeup gain** restores level after compression.
- **For voice:** compress only to tame "occasional too-loud passages" (2–6 dB). He prefers
  volume envelopes to "raise soft syllables or lower too-loud parts" (no pumping).
- **Multiband:** Winer's articles don't cover it. A multiband compressor splits the signal with
  crossover filters, and the split itself must sum flat. Test it per rule 5 before use.

## Levels and loudness

- Levels inside a 32-bit float chain don't matter: float math covers a range "exceeding 1,000 dB"
  (Winer, *The Truth About Record Levels*). Normalizing above 0 dBFS mid-chain is safe in float.
  Only the final file must not clip.
- Audibility (Winer, *Artifact Audibility*): people hear down to ~10 dB below the noise floor, not
  40. Listeners are most sensitive at 2–4 kHz.
- **Targets (not Winer):**
  - ACX audiobooks (community-quoted; check acx.com): −23 to −18 dB RMS, peaks ≤ −3 dB, noise
    floor ≤ −60 dB RMS, MP3 ≥ 192 kbps CBR, 44.1 kHz.
  - Podcasts: commonly −16 LUFS stereo / −19 mono, true peak ≤ −1 dBTP.
- **Typical spoken-word order (not Winer):**
  1. high-pass and corrective EQ;
  2. light compression (2–6 dB);
  3. de-ess 5–8 kHz if needed;
  4. small tonal EQ;
  5. limiter last.

  If the limiter takes 5–6 dB off every sentence, fix it earlier in the chain.

## Measured ffmpeg pitfalls (from an audiobook TTS project, 2026-10)

- **`loudnorm` linear mode silently becomes dynamic** when the gain needed would push true
  peak over the TP limit (or the input LRA exceeds the target LRA). Dynamic mode pulled a
  chapter's last ~2 s down ~17 dB. Check `normalization_type` in its JSON. For one fixed gain,
  measure (`ebur128`) and apply `volume=`.
- **`mcompand` with narrow speech bands coloured the tone even at 1:1.** That was measured
  2026-10-15 by band energy on speech, not yet confirmed with a noise sweep (rule 5):
  - 700–900 Hz −14.6 dB, 900–1200 Hz −6.4 dB, lows +1.8 dB;
  - 3 wide bands stayed within ~0.2 dB except −2.7 dB at 3–6 kHz.

  Don't use it for narrow bands. Confirm with noise before any multiband use.
- **`firequalizer` with `scale=loglog`** (and an `entry(0,…)` point) silently applied no change
  at all on ffmpeg 4.4. The default scale (`linlog`) with dense `entry()` points (every 1/24 octave)
  worked: neutral measured 0.00 dB, and a computed 1.2 dB curve measured within 0.1 dB of plan.
- Haas widening (`haas`) changed the band balance by < 0.5 dB on a mono voice.
- Chatterbox TTS peaks were flat-topped (99.9th percentile within 0.1 dB of the max), so peak
  "spike" limiting does little on that material. Measure your own source's peak distribution.
- Run experiments on copies of the audio, never on the originals.

## Sources

Winer: [The Art of Equalization](http://www.ethanwiner.com/equalizers.html) ·
[Compressors](http://www.ethanwiner.com/compressors.html) ·
[Second Guessing Mastering Engineers](http://ethanwiner.com/master_dem.htm) ·
[Phase Shift in Equalizers](http://www.ethanwiner.com/EQPhase.html) ·
[Acoustics FAQ](http://www.ethanwiner.com/acoustics.html) ·
[The Truth About Record Levels](http://www.ethanwiner.com/levels.htm) ·
[Artifact Audibility](http://www.ethanwiner.com/audibility.html) ·
[Dispelling Popular Audio Myths](http://www.ethanwiner.com/myths.html) ·
[Coding an Equalizer](http://www.ethanwiner.com/eq-dsp.htm) ·
[Audio Filters](http://www.ethanwiner.com/filters.html) · [all articles](https://ethanwiner.com/articles.html)

Gap-fillers: [Waves: fix boxy vocals](https://www.waves.com/how-to-fix-boxy-vocals) ·
[Rysup: boxy vocals](https://rysupaudio.com/blogs/news/how-to-fix-boxy-vocals) ·
[Rysup: how to EQ vocals](https://rysupaudio.com/blogs/news/how-to-eq-vocals) ·
[MixingGPT 2026 vocal EQ](https://mixinggpt.com/blog/how-to-eq-vocals-2026) ·
[Sage Audio: mastering dialogue](https://sageaudio.com/articles/mastering-dialogue-for-podcasts) ·
[Violet Recording: mastering a podcast](https://violetrecording.com/how-to-master-a-podcast/) ·
[ACX requirements explained](https://homebrewaudio.com/acx-audio-submission-requirements-what-the-heck-do-they-mean) ·
[ffmpeg-normalize options](https://slhck.info/ffmpeg-normalize/usage/normalization-options/)
