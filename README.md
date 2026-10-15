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
- Make small moves; cut deeper only on measured, steady resonances.
- Process only when there's a reason.
- Give every A/B as one file that alternates raw and processed every 4 s, raw first, with a quiet
  beep at each switch (one beep = processed, two = raw), and only partly loudness-matched for
  cut-only fixes.
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
- `room_resonance_fix.py`: detects a voice's steady resonances (frequencies that stay high while
  the speech changes) and cuts them with up to 5 parametric bell filters. It saves the ffmpeg chain
  to reuse on every chapter. Tested: noise gives no bands, and a known resonance is found.
- `make_alternating_ab.py`: one A/B file, raw first, switching every 4 s, with a quiet 660 Hz beep
  at each switch (one = processed, two = raw).
- `measure_filter_frequency_response.py`: the frequency response of any ffmpeg filter chain,
  from white noise. Run it before trusting a filter.

Ask an agent, for example: *"Use the audio-and-vocal-mastering skill. Run the room resonance fix on
`chapter-01.wav` and make me an A/B comparison file."*
