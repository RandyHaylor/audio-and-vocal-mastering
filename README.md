# audio-and-vocal-mastering

An agent skill that gives an AI agent working studio basics before it touches audio: EQ,
compression, limiting, loudness and room resonances, for audio in general and spoken voice
(narration, podcasts, TTS) in particular.

It leans on **Ethan Winer**'s writing (ethanwiner.com, *The Audio Expert*): short quotes with
links to his articles. Other sources only fill topics he doesn't cover, and are marked as such.
It also records ffmpeg pitfalls measured on a real audiobook TTS pipeline, such as `loudnorm`
silently switching to dynamic mode and `mcompand` colouring the tone with narrow bands.

## What it makes the agent do

- Treat what the listener hears as the fact; a measurement that disagrees is incomplete.
- Make small moves, capping automatic corrections at 1.5 dB.
- Process only when there's a reason.
- Level-match every A/B comparison, and give it as one file that alternates raw and processed
  every 2 s, with a silence "tic" into processed and "tic tic" back to raw.
- Test any filter chain with noise at neutral settings before trusting it.
- Look up ranges and tool behaviour instead of recalling them.

## Use it

The skill is one plain Markdown file, `audio-and-vocal-mastering/SKILL.md`, with a short
name/description header. It works with any agent or model that can read instructions:

- **Agents with a skills folder** (any tool that loads `SKILL.md` folders): copy or link the
  `audio-and-vocal-mastering/` folder into that tool's skills directory.
- **Any other agent or chat model:** add `SKILL.md` to its instructions, system prompt or
  project files, or tell it to read the file before doing audio work.

```bash
git clone https://github.com/RandyHaylor/audio-and-vocal-mastering.git
# e.g. link it into a skills directory:
ln -s "$PWD/audio-and-vocal-mastering/audio-and-vocal-mastering" <your agent's skills folder>/audio-and-vocal-mastering
```

## Example scripts

In `audio-and-vocal-mastering/scripts/` (python3 + numpy, ffmpeg and ffprobe on PATH):
- `room_resonance_curve.py`: detects a voice's steady resonances and applies a soft 0–1.2 dB
  correction curve, loudness-matched to the source. It's the skill's "detect the room" approach.
- `make_alternating_ab.py`: one A/B file that switches raw/processed every 2 s, raw first, with
  silence markers ("tic" = now processed, "tic tic" = now raw).
- `measure_filter_frequency_response.py`: the frequency response of any ffmpeg filter chain,
  from white noise. Run it before trusting a filter.
