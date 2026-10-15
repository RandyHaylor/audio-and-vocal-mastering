# audio-and-vocal-mastering

A Claude Code skill that gives an AI agent working studio basics before it touches audio: EQ,
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
- Level-match every A/B comparison.
- Test any filter chain with noise at neutral settings before trusting it.
- Look up ranges and tool behaviour instead of recalling them.

## Install

```bash
git clone https://github.com/RandyHaylor/audio-and-vocal-mastering.git
# all projects:
ln -s "$PWD/audio-and-vocal-mastering/audio-and-vocal-mastering" ~/.claude/skills/audio-and-vocal-mastering
# or one project:
ln -s "$PWD/audio-and-vocal-mastering/audio-and-vocal-mastering" <project>/.claude/skills/audio-and-vocal-mastering
```

The skill is `audio-and-vocal-mastering/SKILL.md`.
