# CaddAI PRFAQ — v0.1
**Status:** Working draft
**Purpose:** Define the customer problem, product promise, principles, and long-term vision before implementation choices harden around them.

> **Relationship to other CaddAI documents:** this PRFAQ describes the
> long-term customer experience and product principles CaddAI is working
> towards — it is the product **north star**, not a description of current
> implementation status. [docs/prd.md](prd.md) defines what the product
> must actually do at each milestone; [docs/architecture.md](architecture.md)
> and [docs/adr/](adr/) define how the system is designed;
> [docs/roadmap.md](roadmap.md) defines when capabilities are built. Where
> this document describes capabilities in the present tense (following
> standard Amazon-style PRFAQ convention of writing as if already launched),
> that is aspirational framing, not a claim that the functionality exists
> today — see [docs/roadmap.md](roadmap.md) for what is actually
> implemented. This document must not override an explicit ADR or architectural constraint
> (in particular the deterministic-strategy principle,
> [ADR 0001](adr/0001-deterministic-strategy-engine.md), and the
> offline-first active-round principle,
> [ADR 0005](adr/0005-offline-first-active-round-architecture.md)); any
> apparent conflict should be escalated (`NEEDS_DECISION`, see `AGENTS.md`
> §14), not silently resolved in either document's favour.

---

# Press Release

## CaddAI launches a golf GPS that tells you what shot to hit — not just how far away the green is
**CaddAI combines GPS, course geometry, a golfer's personal performance data, playing conditions, and intelligent shot modelling to provide personalised caddie advice throughout a round.**

Golf GPS devices are excellent at answering questions such as *“How far is it to the green?”*

CaddAI is designed to answer a different question:

> **“What do you like here?”**
Standing over a shot, a golfer doesn't only need the yardage. They need to decide which club to hit, where to aim, what hazards matter, how the lie affects the shot, whether the wind changes the decision, and what kind of miss they can afford.

A human caddie considers all of these factors.

CaddAI aims to do the same.

For example, instead of simply reporting:

> 162 yards to the centre.
CaddAI might advise:

> **“I'd hit 7-iron. It's playing slightly longer into the wind, and the bunker short-right brings your usual miss into play. Aim just left of centre.”**
The recommendation is based on the individual golfer rather than generic club-distance assumptions.

CaddAI can understand information such as:

- the golfer's actual carry distances
- carry variability
- left/right dispersion
- typical miss
- current position
- green geometry
- bunkers and water
- distance required to carry hazards
- lie
- wind
- elevation
- temperature and environmental conditions
CaddAI evaluates the situation and recommends a club, target and strategy.

## Built around the golfer
CaddAI develops a model of how the golfer actually plays.

A 7-iron is not simply recorded as a “160-yard club.”

CaddAI can represent it more realistically:

> Average carry: 158 yards
> Carry variation: ±7 yards
> Typical lateral dispersion: 11 yards
> Typical bias: 4 yards right
Over time, CaddAI can use round data to better understand the player's real performance and provide increasingly personalised recommendations.

The objective is not to tell every golfer the statistically perfect way to play golf.

It is to recommend the best shot **for that golfer**.

## More than distance
CaddAI combines three forms of understanding.

### The course
CaddAI understands the shape of the hole, including greens, fairways and hazards rather than treating the course as a collection of GPS points.

### The golfer
CaddAI understands how far the player actually hits each club and how their shots are distributed.

### The current shot
CaddAI considers the circumstances of the shot, including position, lie, elevation, wind and other relevant conditions.

Together, these allow CaddAI to evaluate alternative shots rather than simply return a distance.

## Designed to work on a golf course
Golf courses frequently have unreliable mobile reception.

CaddAI therefore follows an offline-first principle:

> **The core caddie must work even when there is no internet connection.**
During a round, CaddAI is designed to remain capable of:

- determining the golfer's location
- reading course geometry
- reading the player's profile
- computing distances
- simulating shots
- recommending a shot
- recording decisions and outcomes
without requiring a network request.

Internet connectivity can improve the experience through course downloads, synchronisation, updated weather information and optional cloud AI, but losing connectivity should not prevent the golfer from receiving a recommendation.

## The AI does not decide the golf shot
CaddAI separates golf decision-making from conversational AI.

A deterministic golf engine evaluates the course, golfer and shot and produces a structured recommendation.

For example:

```
Club: 7 Iron
Target: 6 metres left of green centre
Playing distance: 148 metres
Primary risk: bunker short-right
Confidence: 84%
```
A language model may then communicate that recommendation naturally:

> “I'd hit 7-iron and favour the left half. The bunker short-right makes your normal miss the thing we want to avoid.”
The language model explains the decision.

It does not make it.

If the language-model layer is unavailable, CaddAI can still provide the underlying recommendation.

## Software first, hardware later
CaddAI will initially prove the caddie experience in software.

Only after the recommendation system has been tested during real rounds will CaddAI commit to dedicated hardware.

A future CaddAI device could combine:

- high-accuracy GNSS
- camera
- barometer
- compass
- IMU
- microphone
- environmental sensing
- local AI acceleration
The purpose of these sensors is to improve CaddAI's understanding of the current situation.

For example:

```
Camera
   ↓
Lie assessment
   ↓
CaddAI shot model
```
or:

```
GNSS + barometer
   ↓
Elevation
   ↓
CaddAI shot model
```
The hardware observes.

**The CaddAI engine decides.**

## A product you can own
CaddAI is being designed around another principle:

> **Buying the product should not mean committing to another permanent monthly subscription.**
Core GPS, course, player and strategy functionality should remain useful without recurring payments.

Optional cloud-intensive functionality may eventually be offered through prepaid usage — for example, purchasing a number of enhanced CaddAI rounds — rather than requiring golfers to pay every month simply to continue using something they already bought.

The aim is simple:

> **Buy your caddie. Keep your caddie.**

---

# Frequently Asked Questions

## What problem is CaddAI solving?
Existing golf GPS products are primarily information tools.

They tell golfers things such as:

- distance to the front of the green
- distance to the centre
- distance to the back
- distance to hazards
But golfers still have to turn that information into a decision.

CaddAI aims to bridge that gap.

Instead of only answering:

> “How far?”
it should answer:

> **“What should I actually do?”**

---

## Isn't this just a GPS with ChatGPT added?
No.

Conversational AI is not the core product.

The valuable part of CaddAI is the underlying golf decision system:

```
Course
+
Player
+
Current conditions
+
Shot simulation
        ↓
Golf strategy engine
        ↓
Recommendation
```
Natural-language AI is an interface to that system.

Adding a chatbot to a traditional GPS would not create CaddAI.

---

## Why should a golfer trust CaddAI?
Trust must be earned through transparent and consistently useful recommendations.

CaddAI should be capable of explaining important parts of its reasoning.

For example:

> “You can reach with 5-wood, but your dispersion brings the water into play too often. Hybrid leaves you around 95 yards, which is the better expected outcome.”
The golfer should be able to understand *why* a recommendation was made.

CaddAI should also show uncertainty where appropriate rather than presenting weak information as certainty.

Ultimately, trust will need to be validated through real on-course testing.

---

## What is the key product success metric?
The most important question is:

> **Would a golfer actually follow CaddAI's recommendation?**
Technical accuracy alone is not enough.

A successful system must produce recommendations golfers:

1. understand,
2. believe,
3. can execute,
4. find useful enough to change their decisions.
Longer term, recommendation quality can also be evaluated against outcomes such as expected strokes and strokes gained.

---

## Who is CaddAI for?
The initial target is the serious amateur golfer who already thinks about:

- club selection
- carry distances
- misses
- hazards
- course management
but does not have a human caddie.

This includes golfers ranging from competent recreational players to low-handicap players.

The system should eventually adapt its advice to ability rather than assume every player can execute the same shot.

---

## Will CaddAI tell everyone to play conservatively?
No.

The recommendation should reflect the individual golfer and the consequences of each option.

For one golfer:

> Driver may be the correct play.
For another:

> A hybrid may produce a better expected result.
Risk strategy can eventually take into account both statistical outcomes and player preferences, but the system should clearly distinguish between **ability** and **risk preference**.

Risk preference is also distinct from the strategic situation on a given
hole. A golfer may generally prefer conservative golf, but still need a
birdie on a particular hole because of the state of their round. CaddAI
should be able to explain the trade-off between options and recommend a
riskier shot when the golfer's objective makes that the rational choice —
for example, favouring a lower-percentage line that offers a realistic
birdie when a birdie is needed, rather than always defaulting to the
statistically safest shot. The underlying model of how the golfer actually
hits the ball does not change when the objective changes — only the
strategy layered on top of it does.

---

## How does CaddAI know how far I hit each club?
Initially, the golfer can enter their own club performance information.

For example:

```
7 Iron
Average carry: 145 metres
Carry standard deviation: 6 metres
Lateral dispersion: 9 metres
Typical bias: 2 metres right
```
Later versions may estimate and continuously update these values from recorded shots.

CaddAI should not require sophisticated launch-monitor data to become useful.

---

## Why model dispersion instead of just club distance?
Because golf decisions depend on misses.

Two golfers may both average 150 yards with a 7-iron.

But one might have a narrow dispersion pattern while the other regularly misses 15 yards right.

Those players should not necessarily receive the same recommendation when there is water right of the green.

---

## How will CaddAI model shots?
The long-term strategy engine will evaluate candidate shots using statistical simulation.

Conceptually:

```
Possible club + target
        ↓
Player shot distribution
        ↓
Thousands of simulated outcomes
        ↓
Course-relative outcomes (green / rough / bunker / water / penalty)
        ↓
Resulting golf states
        ↓
Expected strokes / scoring distribution
        ↓
Strategy objective (risk preference + situation)
        ↓
Recommendation
```
CaddAI can then compare multiple strategies rather than relying on simple rules such as “choose the nearest club distance.”

The simulation should preserve enough detail about each candidate shot's
outcomes — not just its average result — to support questions such as how
often a shot finds trouble, how often it produces a very good result, and
how it compares on scoring terms (e.g. birdie-or-better, par-or-better,
bogey-or-worse). This lets CaddAI reason about risk and reward, not only
about the lowest mean expected strokes.

---

## Does CaddAI need mobile reception?
Core active-round functionality should not.

Before a round, CaddAI may download information such as:

- selected course
- course geometry
- player profile
- relevant updates
During the round, those resources should be available locally.

Cloud connectivity can enhance the experience, but losing reception should not stop CaddAI from functioning as a golf caddie.

---

## What happens when there is no weather connection?
CaddAI should degrade gracefully.

It may use:

- recently cached weather
- device sensors
- course/environment information
- manually entered conditions
rather than simply failing.

Weather accuracy and local wind estimation will require further research.

---

## How does CaddAI understand the lie?
Initially, the golfer may select a simple lie classification such as:

- fairway
- first cut
- light rough
- heavy rough
- bunker
- recovery lie
This creates a known input to the strategy engine.

Future dedicated hardware could use a camera and computer-vision model to assess characteristics including:

- grass length
- whether the ball is sitting up or down
- slope
- surface type
- likely strike quality
The resulting assessment would populate the same CaddAI lie model used by manual input.

---

## Why not build the camera/device now?
Because the necessary hardware requirements are not yet known.

The software needs to establish:

- which information materially improves recommendations
- required GPS accuracy
- required response latency
- computational workload
- battery requirements
- whether golfers want voice, screen or both
- how often lie analysis is useful
- how golfers actually interact with the product during a round
Those questions should be answered through software prototypes and real rounds before committing to custom hardware.

---

## What might a future CaddAI device contain?
Potentially:

- GNSS
- camera
- barometric pressure sensor
- compass
- IMU
- microphone
- speaker
- touchscreen or simple display
- Bluetooth/Wi-Fi
- local storage
- AI-capable processor
This is intentionally not yet a product specification.

The final hardware should be determined by the validated software experience.

---

## Could CaddAI just remain a mobile app?
Yes.

A dedicated device is a long-term possibility, not a predetermined outcome.

If a mobile implementation provides the right experience, accuracy, reliability and economics, that could remain the primary product.

---

## Why might dedicated hardware eventually be better?
Dedicated hardware could offer:

- better battery life
- easier access during a round
- improved GPS
- dedicated sensors
- camera positioning optimised for lie analysis
- better sunlight visibility
- physical controls
- predictable compute hardware
- deeper offline integration
Whether those advantages justify manufacturing hardware needs to be demonstrated.

---

## Will CaddAI use an LLM?
Probably, but it is not required for the golf decision.

An LLM could provide:

- conversational explanations
- voice interaction
- follow-up questions
- post-round discussion
For example:

> “Can I get there?”
or:

> “What happens if I hit driver?”
But the structured recommendation should exist independently.

---

## Does the LLM need to run on the device?
Not necessarily.

CaddAI can eventually support several tiers:

```
Deterministic engine
        ↓
always local

Simple explanation
        ↓
potentially local

Advanced conversation
        ↓
local or optional cloud model
```
The correct architecture should be chosen once the computational requirements can be measured.

---

## What happens if the cloud AI is unavailable?
The golfer should still receive the deterministic recommendation.

For example:

```
7 Iron
147 m playing distance
Aim 5 m left of centre
Confidence 84%
```
A cloud service should not be able to make CaddAI incapable of answering the core golf question.

---

## Will CaddAI require a subscription?
The product goal is **no mandatory ongoing subscription for core functionality**.

Potential future commercial models include:

- one-time mobile app purchase
- dedicated hardware purchase
- included cloud usage
- prepaid premium rounds
- optional cloud-enhanced caddie packs
- paid major software upgrades
The exact commercial model is intentionally undecided.

The underlying principle is that golfers should not need to continuously pay simply to retain access to the core product they purchased.

---

## Why might premium rounds cost money?
Some optional capabilities create an ongoing vendor cost, particularly:

- third-party LLM inference
- cloud computation
- premium external data
- advanced cloud analysis
Rather than hiding those costs inside an indefinite subscription, CaddAI may allow golfers to purchase enhanced rounds when they want them.

A golfer who stops purchasing enhanced rounds should still retain the core offline product.

---

## Will CaddAI work for free forever after buying it?
The intention is that the core functionality supplied with the purchased product remains usable.

CaddAI cannot promise indefinite access to third-party services whose costs or availability are outside its control.

This is one reason the core decision path is designed not to depend on them.

---

## Does CaddAI store every shot I hit?
Eventually, CaddAI may maintain a decision journal containing:

- situation
- recommendation
- recommendation rationale
- golfer's actual decision
- shot outcome
- resulting lie
- resulting position
This serves two purposes:

1. helping CaddAI understand the golfer,
2. evaluating whether CaddAI's own recommendations are actually good.
Privacy, retention and synchronisation policies will need to be defined before production use.

---

## Will CaddAI automatically learn my game?
Eventually, that is the goal.

However, automatically updating a player's statistical profile introduces important questions around:

- sample size
- outliers
- old versus recent shots
- weather
- lie
- equipment changes
- abnormal shots
- confidence in the estimate
The initial product should prefer transparent manually supplied or clearly derived player information rather than pretending to understand the golfer from insufficient data.

---

## Will CaddAI account for elevation?
Yes.

Elevation should eventually be another structured input into the shot model.

Initial implementations may use course or GPS elevation.

Future hardware may combine:

- GNSS
- terrain data
- barometric pressure
to improve the estimate.

---

## Can CaddAI understand wind accurately?
Wind is one of the harder environmental inputs.

Potential sources include:

- weather services
- cached forecasts
- manual input
- local device sensing
- inference from previous shots
CaddAI should represent wind explicitly while allowing its source and confidence to evolve.

---

## Is CaddAI legal in competition golf?
Competition-rule compliance must be researched before tournament functionality is marketed.

CaddAI may ultimately require different modes depending on the rules governing distance-measuring devices, slope/elevation information, recommendation assistance or other functionality.

Competition legality should not be assumed from the general availability of traditional GPS devices.

---

## What happens when CaddAI is uncertain?
It should communicate that uncertainty.

For example:

> “7-iron is my preference, but 6 and 7 are very close here.”
or:

> “The wind estimate is stale, so I'd treat this as roughly one club rather than an exact adjustment.”
False confidence would reduce trust faster than admitting uncertainty.

---

## Will CaddAI replace golf coaching?
No.

A coach helps improve the golfer's swing and skills.

CaddAI primarily helps the golfer **make better decisions with the game they currently have**.

Those are different problems.

---

## What's different from Garmin, Shot Scope, Arccos or other golf products?
The intended differentiation is not simply more statistics or a prettier GPS map.

The core proposition is:

> **CaddAI turns information into a personalised golf decision.**
Whether that differentiation is strong enough to support a product must be validated through user testing rather than assumed.

---

## What is the first product?
The first meaningful product is a software prototype capable of being used during real rounds.

It should eventually combine:

- real position
- real course geometry
- player profile
- shot modelling
- strategy
- round tracking
The purpose is to validate the recommendation experience before dedicated hardware development begins.

---

## What must be true before dedicated hardware is built?
At minimum, CaddAI should demonstrate that:

1. golfers find the recommendations useful,
2. golfers trust enough recommendations to act on them,
3. personalised recommendations outperform generic GPS information in meaningful situations,
4. the interaction is practical during real rounds,
5. the required sensors are understood,
6. required compute and memory are measurable,
7. acceptable latency is known,
8. offline operation is viable,
9. battery requirements are understood,
10. dedicated hardware would materially improve the experience over a phone.

---

## What would cause us to conclude the product thesis is wrong?
CaddAI should not continue simply because the technology works.

The thesis would be challenged if real-world testing shows that:

- golfers consistently prefer making the decision themselves,
- recommendations are not meaningfully better than raw GPS information,
- golfers do not trust personalised recommendations,
- gathering enough contextual information is too intrusive,
- recommendations require too much interaction during play,
- reliable course/lie/environment data cannot be obtained affordably,
- the system cannot operate reliably offline,
- the cost of providing the experience exceeds customers' willingness to pay.
Any of these should trigger reconsideration of the product rather than additional engineering for its own sake.

---

# Product Principles
The following principles should guide future product and architecture decisions.

### 1. CaddAI is a caddie, not a GPS with a chatbot
The value is the recommendation.

### 2. The golf engine decides
LLMs explain and interact; they do not determine golf strategy.

### 3. Personalisation matters
Recommendations should reflect the individual golfer's ability and tendencies.

### 4. Offline is a core capability
An active round must not depend on internet connectivity.

### 5. Sensors observe; the engine decides
Hardware and AI perception systems should produce structured domain inputs rather than contain strategy logic.

### 6. Software validates hardware
Dedicated hardware should follow proof of the on-course experience.

### 7. Explain important decisions
A golfer should be able to understand why a recommendation was made.

### 8. Admit uncertainty
Confidence should reflect the quality of the available information.

### 9. Build for ownership rather than dependency
Core functionality should not require an indefinite subscription.

### 10. Measure whether golfers actually trust it
Engineering sophistication is not the success metric.

A golfer choosing to follow the advice is.
