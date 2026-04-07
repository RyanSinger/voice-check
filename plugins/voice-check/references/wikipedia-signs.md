# Wikipedia: Signs of AI Writing

Source: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing

A field guide to writing and formatting conventions typical of AI chatbots like ChatGPT, with real examples from Wikipedia articles and drafts. Originally compiled to help detect undisclosed AI-generated content on Wikipedia, but broadly applicable.

Not all text featuring these indicators is AI-generated — LLMs are trained on human writing, including Wikipedia. This list is descriptive, not prescriptive. These are observations, not rules.

---

## Caveats

### AI detection tools

Don't rely solely on AI content detection tools (GPTZero, etc). They perform better than random chance but have non-trivial error rates. Detectors can be fooled by text modifications (paraphrasing, spacing changes) and models not seen during detector training.

### Your own detection ability

Don't rely too much on your own judgment either. A 2025 preprint shows heavy LLM users can correctly identify AI-generated text about 90% of the time — meaning if you tag 10 pages as AI-generated, you've probably falsely accused one editor. People who don't use LLMs much do only slightly better than random chance.

---

## Content Signs

### Undue emphasis on significance, legacy, and broader trends

**Words to watch:** *stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted...*

LLM writing puffs up the importance of the subject by adding statements about how arbitrary aspects represent or contribute to some broader topic. There's a distinct repertoire of ways it does this.

Example: "The Statistical Institute of Catalonia was officially established in 1989, **marking a pivotal moment** in the evolution of regional statistics in Spain."

LLMs do this even for the most mundane subjects like etymology or population data. Sometimes they add hedging preambles acknowledging the subject is relatively unimportant before talking about its importance anyway.

When writing about biology, LLMs over-emphasize connections to the broader ecosystem, belabor conservation status, and reference preservation efforts even when none exist.

### Undue emphasis on notability, attribution, and media coverage

**Words to watch:** *independent coverage, local/regional/national media outlets, profiled in, written by a leading expert, active social media presence*

LLMs act as if the best way to prove a subject is notable is to hit readers over the head with claims of notability, often listing sources without context about what those sources actually said. They may inaccurately attribute their own superficial analyses to named sources.

LLMs painstakingly emphasize sources in body text even for trivial or uncontroversial facts. They often note that subjects "maintain an active social media presence." Sometimes they create entire sections just to assert notability in a list format.

### Superficial analyses

**Words to watch:** *highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering... (figurative), encompassing..., valuable insights, align/resonate with*

AI chatbots insert superficial analysis of information, often about significance, recognition, or impact. This is usually done by attaching a present participle ("-ing") phrase at the end of sentences, sometimes with vague attributions.

Example: "As of the April 2008 census, the population of Douera stood at approximately 56,998 inhabitants, **creating a lively community within its borders.**"

These are usually synthesis and/or unattributed opinions. Newer chatbots with retrieval-augmented generation may attach these to named sources regardless of whether those sources say anything close.

### Promotional and advertisement-like language

**Words to watch:** *boasts a, vibrant, rich (figurative), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned...*

LLMs have serious problems keeping a neutral tone, especially for anything that could be "cultural heritage" — they constantly remind readers of its importance. This happens even when prompted to use an encyclopedic tone. They also add promotional language to text about companies and products, sounding like a TV commercial transcript.

Example: "**Nestled** within the **breathtaking** region of Gonder in Ethiopia, Alamata Raya Kobo **stands as a vibrant town with a rich cultural heritage**..."

### Vague attributions and overgeneralization of opinions

**Words to watch:** *Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when only few cited), such as (before exhaustive lists)...*

AI chatbots attribute opinions to vague authorities — weasel wording. They also exaggerate the quantity of sources, presenting views from one or two sources as widely held, or implying lists are non-exhaustive when sources give no such indication.

### Outline-like conclusions about challenges and future prospects

**Words to watch:** *Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook...*

Many LLM-generated articles include a "Challenges" section beginning with "Despite its [positive words], [subject] faces challenges..." and ending with a vaguely positive assessment or speculation about how initiatives could help. These usually appear at the end of articles with a rigid outline structure, sometimes with a separate "Future Prospects" section.

Example: "**Despite its industrial and residential prosperity, Korattur faces challenges** typical of urban areas..."

### Leads treating article titles as proper nouns

When generating articles about topics that aren't proper names (like lists), the first sentence may introduce the title as if it were a standalone real-world entity.

Example: "**The 'List of songs about Mexico' is a curated compilation** of musical works..."

### Vague see-also sections

LLMs fill see-also sections with broad, generic terms. An article about a startup might link to "Financial technology." Entries may link to non-existent articles.

---

## Language and Grammar Signs

### Overused "AI vocabulary" words

**Words to watch:** *Additionally (especially beginning sentences), align with, crucial, delve (pre-2025), emphasizing, enduring, enhance, fostering, garner, highlight (as verb), interplay, intricate/intricacies, key (as adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (as verb), valuable, vibrant*

Studies show LLMs overuse specific words that appeared far more frequently in text after 2023. They often co-occur — where there's one, there are likely others. The distribution varies by chatbot and changes over time ("delve" was famously overused by ChatGPT in 2023-2024, then dropped sharply in 2025). One or two may be coincidental, but an edit introducing lots of them is one of the strongest tells.

### Avoidance of basic copulatives ("is"/"are" phrases)

**Words to watch:** *serves as/stands as/marks/represents [a], boasts/features/offers [a]*

LLM-generated text substitutes constructions like "serves as a" for simpler "is." One study documented over 10% decrease in "is" and "are" usage in academic writing in 2023. This is particularly visible in AI copyedits, which "improve" text this way.

### Negative parallelisms

Parallel constructions involving "not," "but," or "however" — like "Not only... but..." or "It is not just about..., it's..." — are common in LLM writing to appear balanced and thoughtful. Also constructions that explicitly negate primary properties: "not..., it's..." or "no..., no..., just..."

### Rule of three

LLMs overuse the rule of three: "adjective, adjective, adjective" or "short phrase, short phrase, and short phrase." They use this to make superficial analyses appear more comprehensive.

Example: "The event features **keynote sessions, panel discussions, and networking opportunities**."

### Elegant variation

Generative AI has a repetition-penalty code that discourages reusing words. Output might give a character's name then repeatedly use different synonyms (protagonist, key player, eponymous character). This creates stilted, unnatural variation.

### False ranges

LLMs like using "from... to..." constructions figuratively, but often the endpoints are loosely related or unrelated things with no meaningful scale between them. They do this because such language is used in persuasive writing to impress, and LLMs are heavily influenced by persuasive writing training data.

Example: "From problem-solving and tool-making **to** scientific discovery, artistic expression, and technological innovation" — no coherent scale exists between these endpoints.

---

## Style Signs

### Title case

In section headings, AI chatbots strongly capitalize all main words.

### Overuse of boldface

AI chatbots display phrases in boldface for emphasis in an excessive, mechanical manner — emphasizing every instance of a chosen word or phrase in a "key takeaways" fashion. Inherited from readmes, fan wikis, how-tos, sales pitches, slide decks, and listicles.

### Inline-header vertical lists

AI output often includes vertical lists where each item has a boldfaced inline header followed by a colon and descriptive text. Instead of proper formatting, bullets may appear as bullet characters (•), hyphens, en dashes, hash symbols, or emoji.

### Emoji

AI chatbots often use emoji, particularly decorating section headings or bullet points by placing emoji in front of them.

### Overuse of em dashes

LLM output uses em dashes (—) more often than nonprofessional human-written text, and in places where humans would use commas, parentheses, colons, or hyphens. LLMs use them in a formulaic way, often mimicking "punched up" sales-like writing. Most useful when combined with other indicators.

### Unusual use of tables

AIs create unnecessary small tables that could be better represented as prose.

### Curly quotation marks and apostrophes

ChatGPT and DeepSeek use curly quotation marks ("...") instead of straight ones ("..."), and curly apostrophes. They may do this inconsistently. Note: Gemini and Claude typically don't use curly quotes. Microsoft Word and macOS/iOS also have smart quotes features.

### Subject lines

AI-generated messages sometimes begin with text intended for a subject field, like "Subject: Request for Permission to Edit Wikipedia Article."

---

## Communication Signs (meant for the user, not the article)

### Collaborative communication

**Words to watch:** *I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., is there anything else, let me know, more detailed breakdown, here is a...*

Editors sometimes paste text from a chatbot that was meant as correspondence or advice rather than content. Chatbots may explicitly state the text is meant for Wikipedia and mention various policies in output.

### Knowledge-cutoff disclaimers

**Words to watch:** *as of [date], Up to my last training update, While specific details are limited/scarce..., not widely available/documented/disclosed, based on available information*

LLMs output disclaimers about their information potentially being incomplete. If an LLM can't find sources, it often states information is "not documented" and speculates about what that information "likely" may be — this is entirely speculative. When unknown info is about a person's personal life, the disclaimer often claims they "maintain a low profile" or "keep personal details private."

### Phrasal templates and placeholder text

AI may generate fill-in-the-blank templates that users forget to fill in. Examples: "[Describe the specific section...]", "PASTE_SPOTIFY_TRACK_URL_HERE", placeholder dates like "2025-XX-XX."

---

## Markup Signs

### Use of Markdown

LLMs default to Markdown instead of wikitext (Wikipedia's markup). They use asterisks for bold/italic instead of single quotes, hash symbols for headings instead of equals signs, parentheses around URLs instead of square brackets. Mixed Markdown and wikitext is a strong indicator. However, Markdown alone isn't conclusive — developers and technical writers use it routinely.

### Broken wikitext

AI chatbots produce faulty wikitext syntax since they're not proficient in it. Particularly common with AfC submission templates.

### turn0search0

ChatGPT may include "citeturn0search0" at sentence ends, with incrementing numbers. These are placeholder citations from ChatGPT's interface that weren't properly converted. First observed February 2025.

### Reference markup bugs: contentReference, oaicite, oai_citation

Due to bugs, ChatGPT may add code like "contentReference[oaicite:0]{index=0}" in place of references. DeepSeek Grok may add XML-styled grok_card tags. These are strong indicators of specific AI tool usage.

### Non-existent categories and templates

LLMs hallucinate non-existent categories and templates, sometimes for generic concepts that seem like plausible titles. These appear as red links.

---

## Citation Signs

### Broken external links

If a new article has multiple citations with broken links not found in web archives, it's a strong sign of AI generation. Most links break over time, but never having worked is different.

### Invalid DOIs and ISBNs

Checksums can verify ISBNs. Unresolvable DOIs and invalid ISBNs indicate hallucinated references.

### Outdated access-dates

Citations may include access-dates unexpectedly old relative to when the edit was made. If many citations share the same old access-date, it's a sign.

### DOIs that lead to unrelated articles

LLMs generate references to non-existent scholarly articles with DOIs that appear valid but are assigned to unrelated articles.

### Book citations without page numbers or URLs

LLMs generate book citations without page numbers. The book may exist and be topically relevant, but without page numbers the citation is unverifiable. Some include page numbers but the cited pages don't verify the text.

### Incorrect reference syntax

AI tools make incorrect attempts at reference formatting — wrong syntax for reusing references, irrelevant sources with PMIDs that happen to match generated numbers, footnote indicators like "↩" characters.

### utm_source parameters

ChatGPT adds "utm_source=openai" or "utm_source=chatgpt.com" to URLs. Microsoft Copilot adds "utm_source=copilot.com." Grok uses "referrer=grok.com." Note: this proves chatbot involvement in finding the citation but not necessarily that the writing was generated.

---

## Miscellaneous Signs

### Sudden shift in writing style

Unexpectedly flawless grammar compared to an editor's other communication. A mismatch of user location and English variety (e.g., an Indian writer using American English for an Indian topic — LLMs default to American English).

### Overwhelmingly verbose edit summaries

AI-generated edit summaries are unusually long, written as formal first-person paragraphs without abbreviations, and conspicuously itemize conventions.

### Pre-placed maintenance templates

LLMs sometimes create drafts that already include review templates set to "declined" or include maintenance tags and protection templates that shouldn't be there.

---

## Signs of Human Writing

### Age of text relative to ChatGPT launch

ChatGPT launched November 30, 2022. Text added before this date was almost certainly not AI-generated.

### Ability to explain editorial choices

Editors should be able to explain why they made an edit or mistake. If someone can supply the correct link and explain a mix-up as human error, that points to an ordinary mistake.

---

## Ineffective Indicators (Things that DON'T reliably indicate AI)

- **Perfect grammar** — Many editors are skilled writers or come from professional writing backgrounds.
- **Mixed casual and formal registers** — May indicate someone technical, young, playful, or neurodivergent. Or just multiple editors.
- **"Bland" or "robotic" prose** — Modern LLMs actually tend toward effusive and verbose, not bland.
- **"Fancy," academic, or unusual words** — LLMs favor certain words but the correlation doesn't extend to all sophisticated prose. Low-frequency and unusual words are actually less likely in AI writing.
- **Letter-like writing (in isolation)** — Letters have been written formally long before LLMs.
- **Conjunctions (in isolation)** — LLMs overuse connecting words but so does essay-like human writing.
- **Bizarre wikitext** — Random-seeming errors are more likely from browser extensions or editing tool bugs than AI.

---

## Historical Indicators (less common in newer models)

### Didactic disclaimers (2022-2024)

Older LLMs added disclaimers like "it's important/critical/crucial to note/remember/consider" and "worth noting." Safety-related advice to imagined readers, disambiguation of topics varying by jurisdiction.

### Section summaries

Older LLMs added sections titled "Conclusion" and restated core ideas at the end of paragraphs.

### Prompt refusal

Chatbots occasionally declined prompts with apologies and reminders that they are AI language models. Increasingly rare.

### Abrupt cutoffs

AI tools used to stop generating content after hitting a token limit, requiring users to select "continue generating."
