# Korean translation quality

## Scope, authority, and precedence

This is the authoritative shared semantic-quality standard for translating, retranslating, or editing Japanese visual novels and dialogue-heavy games into Korean. Read it **before writing the first semantic draft**, not only during review.

The default decision unit is:

`Japanese source + scene context + speaker + addressee + relationship + story phase -> natural Korean`

Do not reduce the task to `Japanese sentence -> Korean sentence`.

Engine-specific skills and project style guides may add work-specific names, terminology, voice notes, structural constraints, or an explicitly requested artistic exception. They may not weaken this document's first-pass quality, spoken-naturalness, directed-relationship voice, addressee tracking, scene-continuity, or review-role requirements. If another skill or project instruction conflicts, this document takes precedence unless the user explicitly overrides a rule for the current work.

Downstream instructions must link to this file and state only their engine- or project-specific additions. Do not copy these shared rules into multiple files and let them drift.

## Required translation model

Apply the global mandatory translation-model policy in `P:\AI\Codex\AGENTS.md`. Every accepted semantic Korean first draft, retranslation, correction, voice decision, name, term, dialogue line, narration line, and UI label must be authored by the active **Codex internal model**. External or local MT/LLM output is forbidden unless the user explicitly requests that specific service. OCR, STT, extraction, alignment, and validators may recover or check source text but may not supply or auto-approve the accepted Korean wording.

## First pass is a near-final translation

Do not treat the first pass as literal scaffolding, disposable machine-like prose, or a placeholder for a later reviewer. On the first translation of each line, resolve meaning, nuance, speaker, actual addressee, relationship, intimacy, age and seniority, organizational or social hierarchy, ally/enemy stance, current emotion, scene situation, address terms, speech level, first- and second-person usage, character voice, story phase, and relationship change.

Write the most natural and accurate near-final Korean supported by the available context. If essential context is genuinely missing, preserve safe ambiguity and record the unresolved point instead of inventing a specific addressee, pronoun, relationship, or intent.

## Natural spoken Korean by text function

Spoken dialogue must sound like something a Korean person in that character and situation could actually say, unless the scene deliberately calls for archaic, literary, ceremonial, quoted, spell-like, recited, or speechmaking language.

Do not mechanically preserve Japanese word order, sentence structure, ellipsis patterns, or written-style phrasing. Reject translationese such as:

- an unnatural chain of fully closed declarative sentences;
- stiff particles or connectives rarely used in real conversation;
- repeated subjects or objects inherited from Japanese;
- repeated first- or second-person pronouns that Korean would naturally omit;
- needlessly literary predicates caused by literal translation;
- wording that does not sound speakable for the character.

Naturalization does not mean trivializing the meaning, adding unsupported slang, changing intensity, or lowering the register. Preserve meaning, personality, emotion, politeness, and dramatic function while reconstructing natural Korean speech.

Do not apply dialogue colloquialization mechanically to narration, internal monologue, system messages, documents, quoted writing, tutorials, or UI. Give each text lane the Korean register appropriate to its runtime function.

## Voice is speaker-to-addressee, not speaker-only

Never assign one immutable voice to a character. Determine voice at least as a directed relationship:

`speaker -> addressee`

When needed, evaluate:

`speaker x addressee x story phase x situation`

The same speaker may change honorific level, address term, name form, second-person expression, ending, command strength, warmth, distance, courtesy, or hostility with a different addressee. The same pair may change as their relationship develops or deteriorates. Project voice guides must therefore record relationship-specific behavior rather than only a single character-wide sample voice.

### Three-or-more-person dialogue

In scenes with three or more participants, identify the actual recipient of every line. Do not carry the speech level used toward B into a later line addressed to C merely because A remains the speaker.

Use direct names or titles, adjacency and response structure, action description, question-answer linkage, position and behavior, interruption, topic shift, entrance or exit, and whether the line targets the whole group. Re-evaluate speech level, address term, second person, and ending whenever the addressee changes.

If the recipient remains genuinely ambiguous, do not force `너`, `당신`, a name, or another explicit target. Preserve the source ambiguity when natural Korean permits it.

## Scene context and packet continuity

Translate by scene and discourse flow whenever possible, not as independent sentence bags. Before drafting, establish the cast, speaker changes, addressee changes, entrances and exits, event flow, immediate preceding context, current relationships, and relevant story phase.

Packets must follow scene, route, branch, and semantic boundaries. If a batch boundary is unavoidable, supply enough preceding and following lines plus speaker/addressee/relationship/story-phase metadata so that voice does not reset at the boundary. Context may overlap between packets, but each stable ID still has exactly one owner.

Do not inherit the previous speaker's voice, politeness, or addressee by accident. When packet data cannot resolve a high-impact ambiguity, flag it for context recovery rather than guessing.

## Mandatory internal decision gate for every line

Before accepting a line, determine internally:

- What does it mean, including implication and emotional force?
- Who is speaking?
- Who is actually being addressed?
- What is their relationship at this story point?
- Which address term and honorific level does this speaker use toward this addressee?
- What are the current emotion and scene situation?
- Would a Korean person in this role actually say it this way?
- Did the line accidentally inherit the preceding speaker's voice or recipient?
- Does it conflict with approved names, terminology, or the relationship-specific voice guide?

This reasoning need not be emitted as verbose commentary. It must be visible in the translation result.

## Translate complete semantic units

- Join adjacent fields into the complete sentence before translating.
- Decide the actor, action, target, effect, referent, and discourse function before choosing Korean wording.
- Split the finished Korean sentence back into the original number of fields without changing control flow.
- Allow identical source fragments to differ when their completed sentences, speakers, addressees, or scenes differ.
- Keep lookup keys separate from displayed text.

## Dialogue and choices

- Write spoken choices as something the player character would naturally think or say in that relationship and moment.
- Separate spoken choices from system/menu choices; do not give menu labels a character voice.
- Preserve deliberate ambiguity, hesitation, interruption, evasion, hostility, affection, and social distance.
- Do not add explicit pronouns or names merely to make an isolated line look grammatically complete.

## Names and terminology

- Keep one canonical spelling for each character, place, faction, skill, status, and attribute.
- Verify whether a word is a proper noun, common noun, adjective, title, address term, or effect name.
- Prefer established game terminology over dictionary-first alternatives.
- Relationship-specific address forms may differ from the canonical glossary label; record the mapping rather than flattening them.

## Items and mechanics

- Read the item name, category, effect commands, status IDs, values, duration, and neighboring description lines together.
- Preserve actor/target scope, chance, amount, duration, stacking, removal, resistance, immunity, and conditional clauses.
- Keep visible abbreviations such as HP only when consistent with the game UI.
- Do not turn an antidote or resistance item into an adjective because an isolated source word is ambiguous.

## Protected content

Preserve exactly:

- format variables and interpolation tokens;
- engine control codes and escape sequences;
- rich-text tags and markup;
- numeric values, percentages, turns, signs, and units;
- deliberate capitalization used as an in-world name or joke.

## Review is QA, not the rescue stage

The first pass must already satisfy this document. Do not design a pipeline in which review must retranslate every line to obtain acceptable Korean.

Post-draft review primarily checks:

- meaning errors, omissions, and unsupported additions;
- mistaken speaker, addressee, relationship, or story-phase judgments;
- voice, speech-level, address-term, or second-person outliers;
- name and terminology inconsistency;
- scene-to-scene continuity and missed relationship changes;
- control codes, structure, encoding, and layout;
- residual Japanese or other untranslated visible source text;
- issues found in actual game screens.

If a packet requires broad line-by-line retranslation because the first pass was literal, context-free, or voice-blind, reject or redo that first-pass stage rather than treating blanket retranslation as normal review.

## Final language QA

Check every frozen target for:

1. nonempty Korean output or an explicitly approved unchanged value;
2. placeholder and control-code parity;
3. glossary and canonical-name consistency;
4. natural grammar, punctuation, and text-function register;
5. correct speaker, actual addressee, relationship, honorific level, and address term;
6. scene continuity, story-phase fit, and relationship-change handling;
7. correct mechanics and referents;
8. UI length and layout risk;
9. residual Japanese or other untranslated user-visible source text;
10. repeated-source differences that are contextual rather than accidental.

Record waivers with a concrete reason. A flag is not a failure if it was deliberately reviewed, but an unexplained flag is not complete.
