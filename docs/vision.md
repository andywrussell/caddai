# Vision

## What CaddAI is

CaddAI is an AI-powered golf caddie. It combines course geometry, GPS
location, player ability, club performance, lie, wind, elevation,
environmental conditions, shot dispersion, and statistical simulation to
recommend golf shots — the way a good human caddie combines local knowledge,
observation, and experience.

The target end-state experience: a player stands over a shot, asks **"What
do you like here?"**, and receives a concise, caddie-style recommendation —
club, target, and the reasoning behind it — grounded in course geometry,
conditions, and the player's own demonstrated ability.

## Why it's needed

Good caddies are expensive, rare, and only available on the course. Most
golfers play without one and rely on incomplete information (a yardage
number, a gut feeling) to make decisions that materially affect their score:
which club, which target, how much risk to take on. Existing range-finder
and GPS apps report distance; they don't reason about strategy, dispersion,
or risk the way a caddie does.

## Who it's for

Golfers who want better on-course decisions than "pick the number on the
sign" — from mid-to-high handicap players who most need strategic help, to
better players who want a second opinion grounded in their own statistics.

## Product principle: decision engine, not chatbot

CaddAI's core value is a **deterministic, explainable decision** — not a
conversational experience. The recommendation must be traceable to concrete
inputs (geometry, player statistics, conditions, simulation) so it can be
trusted, tested, and improved over time. Natural-language explanation is a
presentation layer over that decision, added deliberately late in the
roadmap (see [roadmap.md](roadmap.md)) — never a substitute for it. See
[adr/0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).

## What CaddAI is not (yet, and maybe ever)

- Not a general golf chatbot or rules-question assistant.
- Not a swing-coaching or biomechanics tool.
- Not dependent on a specific hardware GPS device — the domain model is
  device-agnostic; integrations come later (see roadmap M7).
- Not reliant on an LLM for any part of the actual shot decision.

## Current status

This repository is at milestone **M0**: repository architecture,
documentation, agent development team, and a minimal Python package
skeleton. No golf strategy, course import, player modelling, or LLM
functionality is implemented yet. See [roadmap.md](roadmap.md).
