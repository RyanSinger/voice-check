# Wikipedia: Signs of AI Writing (condensed)

Snapshot as of 2026-08-11 of https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing, condensed for skill use.

## Contents

- Content-level indicators
- Language patterns
- Era-dependent vocabulary
- Formatting and markup tells
- Citation red flags
- Stylistic quirks
- Model-specific signatures
- False positives to avoid

A field guide to writing and formatting conventions typical of AI chatbots, compiled from real examples found in Wikipedia articles and drafts. Descriptive, not prescriptive. Not all text featuring these indicators is AI generated; LLMs are trained on human writing, including Wikipedia, and human writing itself is increasingly influenced by LLM output.

---

## Content-level indicators

### Undue emphasis on significance, legacy, and broader trends

Words to watch: stands as, serves as, is a testament to, is a reminder, a crucial role, a pivotal role, a vital role, a significant role, a key moment, underscores its importance, highlights its significance, reflects broader, symbolizing its ongoing legacy, symbolizing its enduring legacy, contributing to the, setting the stage for, marking the, shaping the, represents a shift, marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted.

LLM writing inflates the importance of mundane subjects (etymology, population counts, minor institutions) by tying them to broader trends. Example pattern, paraphrased from a 2024 draft about a statistics institute: the article states the institute's founding "marked a pivotal moment" and "represented a significant shift" in regional statistics, language that adds no verifiable content. Biology articles get the same treatment: overemphasized ecosystem connections, belabored conservation status, and references to preservation efforts that do not exist in the sourcing.

### Canned emphasis on notability, attribution, and media coverage

Words to watch: independent coverage, local media outlets, regional media outlets, national media outlets, trade publications, profiled in, written by a leading expert, active social media presence, maintains a strong digital presence.

LLMs try to prove notability by listing sources rather than summarizing what those sources say, sometimes attributing analysis to a named outlet that never made the claim. Recent drafts have cited coverage (for example, a claimed ABC News feature) that turned out not to exist at all. Articles about businesses or schools frequently gain a line noting an "active social media presence," which carries no encyclopedic content.

### Superficial analyses via tailing clauses

Words to watch: highlighting, underscoring, emphasizing, ensuring, reflecting, symbolizing, contributing to, cultivating, fostering, encompassing, enhancing, valuable insights, align with, resonate with.

The tell is structural: a factual sentence gets a present participle phrase bolted onto the end, asserting significance without a source. A population count becomes a sentence about the town "creating a lively community within its borders." A railway station description gains a clause about it "holding a pivotal place" in regional transit. These tailing clauses are almost always unsourced synthesis; retrieval augmented chatbots sometimes attach them to a named citation that, on inspection, says nothing of the kind.

### Promotional and advertisement-like language

Words to watch: boasts a, vibrant, rich (used figuratively), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative use), renowned, diverse array, featuring.

LLMs struggle to hold a neutral tone for anything framed as cultural heritage, tourism, or corporate identity, even when explicitly prompted for encyclopedic tone. A representative pattern: a town description opens with the town "nestled" in a "breathtaking" region and "standing as a vibrant town with a rich cultural heritage." Corporate articles pick up similar language: a company's sustainability initiative becomes a "commitment to fostering community development."

### Vague attributions and overgeneralization

Words to watch: industry reports, observers have cited, experts argue, some critics argue, several sources (when only one or two are actually cited), such as (introducing what reads as an exhaustive list but is not sourced as one).

LLMs attribute opinions to unnamed authorities, a weasel wording pattern, and inflate how widely held a view is by citing one or two sources as if they represent consensus.

<!-- voice-check: disable structure -->

### Outline like conclusions about challenges and future prospects

Words to watch: despite its ... faces several challenges, despite these challenges, "Challenges and Legacy" as a heading, "Future Outlook" as a heading.

A recurring template: articles end with a section that opens "Despite its [positive traits], [subject] faces challenges," followed by vague, mildly optimistic speculation about future initiatives. This pattern has appeared across subjects as different as economic law, urban development, and technology drafts, always with the same rigid shape.

<!-- voice-check: enable -->

### Leads treating list titles as proper nouns

When an LLM generates an article about something that is not a proper name, such as a list, it sometimes introduces the title itself as a standalone entity in the first sentence: "The 'List of songs about Mexico' is a curated compilation of musical works," rather than describing the subject the list covers.

### Vague see also sections and generic linking

LLMs fill "See also" sections with broad, generic terms loosely related to the topic (a startup article linking to "Financial technology") and occasionally link to articles that do not exist.

---

## Language patterns

### Overused AI vocabulary

Studies show specific words spiked in frequency across written English after the 2022 release of ChatGPT, and these words tend to co occur: an edit with one is more likely to have several more. One or two instances may be coincidental; a cluster is one of the strongest available tells. See Era dependent vocabulary below for the words themselves and how the list has shifted over time.

### Avoidance of basic copulatives

Words to watch: serves as, stands as, marks, functions as, operates as, represents (in place of "is"), boasts, features, maintains, offers (in place of "has"), refers to.

A 2023 study documented more than a ten percent drop in "is" and "are" usage in academic writing after LLM adoption; Wikipedia edits show a similar pattern once lead paragraph conventions are controlled for. This shows up clearly in AI assisted copyedits: "is LAAA's exhibition arm" becomes "serves as LAAA's exhibition space"; "is the first" becomes "holds the distinction of being."

<!-- voice-check: disable structure -->

### Contrast reframes (negative parallelisms)

Three related constructions, all used to make a claim sound more balanced or insightful than it is:

Not just X, but also Y: for example, a sentence recast as "not only dismissive but also unnecessarily harsh," or "isn't just sourcing, it's framing."

Not X, but Y: a more absolute version, such as "not grounded in visual mastery, but in [claim]," or a chained form like "not a mirror but a portal, not a representation of self, but a mechanism."

X rather than Y: associated particularly with Grok output, for example a sentence describing a historical actor as "prioritizing empirical consolidation of power amid fragmented loyalties rather than ideological purity."

All three patterns explicitly negate a simpler framing before asserting a more complex one, a rhetorical move that reads as insight but usually adds nothing sourced.

<!-- voice-check: enable -->

### Rule of three

LLMs default to three item lists, either as adjectives or short parallel phrases, to make an analysis feel more thorough than it is: "the event features keynote sessions, panel discussions, and networking opportunities" is a representative shape, regardless of subject.

### Elegant variation

A repetition penalty built into generation makes models avoid reusing a word, so a subject's name gets replaced across a paragraph with synonyms (protagonist, key player, eponymous figure, or, for a person, repeated descriptive epithets instead of a pronoun). The result reads as stilted rather than varied.

### False ranges

LLMs like the "from X to Y" construction for rhetorical effect, but the two ends are often only loosely related, with no real scale connecting them: "from problem solving and tool making to scientific discovery, artistic expression, and technological innovation" names four unrelated domains, not a spectrum.

---

## Era-dependent vocabulary

The specific words that spike vary by model generation and shift over time as chatbot providers tune output and public awareness of earlier tells grows. Treat these as approximate windows, not hard cutoffs.

2023 to mid-2024 (GPT-4 era): delve, intricate, intricacies, pivotal, testament, additionally (especially opening a sentence), boasts, bolstered, crucial, emphasizing, enduring, garner, interplay, key (as an adjective), landscape (as an abstract noun), meticulous, meticulously, tapestry (as an abstract noun), underscore (as a verb), valuable, vibrant. "Delve" is the signature word of this window: heavily overused through 2023 and early 2024, then it declined through the rest of 2024 and dropped sharply in 2025.

Mid-2024 to mid-2025 (GPT-4o era): align with, enhance, fostering, showcasing, plus continuing use of bolstered, crucial, emphasizing, enduring, highlighting, pivotal, underscore, vibrant. GPT-4o output in this window reads as more subtly positive than GPT-4, avoiding the most obviously superlative claims while keeping the same vocabulary skew.

Mid-2025 onward (GPT-5 era and later): emphasizing, enhance, highlighting, showcasing remain common, alongside a newer cluster built around quietly, shift, matters, and signal, for example a subject "quietly" gaining relevance, a development that "signals" a shift, or a claim that something "matters" without specifying to whom or why. This cluster compounds the same way earlier ones did: seeing one of these words raises the likelihood of finding the others nearby. Caveat: this quietly/shift/matters/signal cluster comes from secondary 2026 reporting on AI writing tells, not from the Wikipedia article this file snapshots, so treat it as unconfirmed against the source page until a later snapshot corroborates it directly.

Model divergence in this window: Grok output continues to overuse causal, empirical, and correlate, and keeps a heavier reliance on underscore than other current models.

Historical, largely obsolete: didactic disclaimers from 2022 through 2024 such as "it's important to note," "it's crucial to remember," and "it's worth noting"; a "Conclusion" section restating the article's main points; occasional prompt refusals with apologies; abrupt generation cutoffs requiring a "continue" prompt. These are now rare in production output but still worth recognizing in older edits.

---

## Formatting and markup tells

### Title case headings

AI chatbots capitalize every main word in section headings, a convention from marketing and slide decks rather than encyclopedic style.

### Overuse of boldface

Phrases get bolded mechanically and repeatedly, in a "key takeaways" style inherited from readmes, listicles, and sales pitches, rather than for genuine emphasis.

### Inline header vertical lists

Bulleted lists where each item opens with a bolded short header followed by a colon and a sentence of description. Bullet characters themselves are sometimes rendered as a dot character, a hash symbol, or an emoji instead of proper wikitext markup.

### Emoji as formatting

Emoji placed in front of section headings or list items as decoration rather than content.

### Unusual use of tables

Small tables built for information that reads more naturally as prose, a habit carried over from chat interface formatting.

### Curly quotation marks and apostrophes

ChatGPT and DeepSeek output curly quotation marks and curly apostrophes, sometimes inconsistently within the same passage. Gemini and Claude typically do not exhibit this. Note that Microsoft Word and macOS or iOS autocorrect also introduce curly quotes, so this is weak evidence alone.

### Skipped heading levels and stray thematic breaks

AI generated wikitext sometimes jumps from a top level heading straight to a sub sub heading, skipping a level, and sometimes inserts a horizontal rule before a heading where none is conventional.

### Markdown instead of wikitext

Asterisks for bold or italic instead of wikitext's quote marks, hash symbols for headings instead of equals signs, square bracket free parenthetical links instead of wikitext's bracket syntax. Mixed Markdown and wikitext in the same edit is a strong tell; Markdown alone is weaker evidence, since technical writers and developers use it routinely outside Wikipedia.

### Broken wikitext and hallucinated markup

Faulty wikitext syntax, especially in AfC submission templates, plus references to categories and templates that sound plausible but do not exist, showing up as red links.

### Subject lines and placeholder text

Pasted chatbot output that begins with a leftover "Subject:" line intended for an email field, and fill in the blank placeholders users forgot to replace, such as bracketed instructions or a literal placeholder date string.

---

## Citation red flags

### Broken external links with no archive history

A new article whose citations link to pages that were never archived anywhere is a strong sign, distinct from ordinary link rot, where a page existed and later went offline.

### Invalid DOIs and ISBNs

ISBNs carry a checksum that can be verified directly; DOIs that fail to resolve, or that resolve to an unrelated paper, indicate a hallucinated or mismatched reference.

### Outdated access dates

Access dates noticeably older than the edit date, especially when many citations in the same edit share one implausible date.

### Book citations without page numbers or verifiable URLs

The cited book may be real and topically relevant, but without a page number the claim cannot be checked; some citations include a page number, but the cited page does not actually support the text.

### Malformed reference syntax

Incorrect syntax for reusing a named reference, footnote style characters left in running text, and PMIDs attached to sources that do not match the numbers cited.

### Tracking parameters revealing chatbot involvement

utm_source=openai and utm_source=chatgpt.com from ChatGPT, utm_source=copilot.com from Microsoft Copilot, referrer=grok.com from Grok. These confirm a chatbot was used to find the source, not necessarily that the prose was AI written.

---

## Stylistic quirks

### Collaborative phrasing meant for the user, not the article

Words to watch: I hope this helps, of course, certainly, you're absolutely right, would you like, is there anything else, let me know, here is a more detailed breakdown.

Occasionally an editor pastes chatbot correspondence directly into an article or talk page instead of the intended content.

### Knowledge cutoff disclaimers

Words to watch: as of [date], up to my last training update, while specific details are limited, not widely documented, based on available information.

When an LLM cannot find sourcing, it tends to state that information is "not documented" and then speculate about what it "likely" is anyway, which is unsourced guessing dressed as caution. For biographical gaps specifically, the disclaimer often becomes a claim that the person "maintains a low profile" or "keeps personal details private."

### Sudden shift in writing style

Unexpectedly polished grammar relative to an editor's usual communication, or a mismatch between an editor's apparent location and the English variety used in the text, since LLMs default to American English regardless of the topic's regional context.

### Overwordy edit summaries

AI generated edit summaries run unusually long, written as formal first person paragraphs without the abbreviations experienced editors use, and itemize every convention followed.

### Pre placed maintenance templates

Drafts that arrive already containing a review template marked declined, or protection and maintenance tags that would not normally be added by the submitting editor.

---

## Model-specific signatures

Leaked interface artifacts are the strongest tell in this whole guide: they prove a specific tool touched the text, though not necessarily that every sentence around them is AI generated.

ChatGPT: leftover reference markup such as contentReference, oaicite, and oai_citation tags; incrementing placeholder citations like turn0search0; an attributableIndex field occasionally leaking into text; tracking parameters utm_source=openai and utm_source=chatgpt.com. Stylistically, GPT-4 output reads as more blatantly, obviously positive; GPT-4o is more subtly positive and avoids the most superlative phrasing while keeping similar vocabulary.

Gemini: bracketed citation fragments such as a cite marker followed by a number, and span tags like a span_ prefixed identifier paired with a start_span marker, both leftovers from Gemini's internal citation format.

Grok: XML style grok_card tags and the longer grok_render_citation_card_json artifact; the tracking parameter referrer=grok.com; heavy, sustained overuse of causal, empirical, correlate, and underscore, more pronounced than in other current models; the "X rather than Y" contrast construction appears disproportionately in Grok output, including in Grokipedia generated text.

Perplexity: leftover upload artifacts such as ppl-ai-file-upload and attached_file references that belong to its file handling interface, not to article content.

DeepSeek: curly quotation marks and curly apostrophes similar to ChatGPT's, plus occasional lenticular brackets and dagger symbols leaking from its citation formatting.

Microsoft Copilot: tracking parameter utm_source=copilot.com on cited URLs.

Claude and Gemini are both noted as generally not producing the curly quote pattern common to ChatGPT and DeepSeek; no leaked interface tokens specific to Claude have been documented as of this snapshot.

---

## False positives to avoid

### Detection tools are not reliable on their own

Automated detectors such as GPTZero and Pangram perform better than random chance but carry a non trivial error rate, and a high detector score alone is not grounds for deletion or accusation.

### Human judgment is also unreliable

A 2025 study found that people without heavy LLM exposure distinguish AI text from human text little better than random chance; one study of a specific test population found roughly 57 percent accuracy identifying AI text and 64 percent identifying human text. Heavy LLM users fare better, around 90 percent accuracy, which still means roughly one in ten accusations from an experienced reviewer will be wrong. Human writing itself has grown more LLM influenced since 2024, which narrows this gap further over time.

### Signs that do not reliably indicate AI writing

Perfect grammar: many editors are professional or highly skilled writers independent of any AI use.

Mixed casual and formal registers within one piece: consistent with a technical, young, playful, or neurodivergent writer, or simply multiple editors touching the same page.

Bland or robotic prose: modern LLMs actually trend toward effusive, verbose output, not flat or bland prose, so flatness alone points away from AI rather than toward it.

Sophisticated or unusual vocabulary in general: LLMs favor a specific, narrow set of words, not sophistication broadly; genuinely rare or low frequency words are, if anything, less likely in AI writing.

Letter-like writing on its own: formal letter conventions predate LLMs by centuries.

Conjunctions on their own: essay style human writing overuses connectives too.

Bizarre or broken wikitext in isolation: more often explained by a browser extension or editing tool bug than by AI generation.

### Signs that do support human authorship

Text added before ChatGPT's public launch on November 30, 2022 is essentially certain to be human written. An editor who can explain why they made a specific edit, including admitting an honest mistake, is behaving like an ordinary human contributor regardless of prose style.
