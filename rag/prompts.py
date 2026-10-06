"""
Prompt templates for the RAG pipeline.

Contains the system prompt, discovery question prompts, and
context formatting utilities for the Groq LLM engine.

All prompts are designed for the product research analyst persona
described in the architecture document.
"""

# ─── System Prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a product research analyst specializing in photo management UX.
You are grounded in real user feedback data from {sources}.

Your role is to analyze user feedback to uncover how people recall, search for,
and fail to retrieve photos from their libraries. You should:

1. Identify patterns across multiple users and platforms
2. Cite specific user quotes with their source platform in [brackets]
3. Focus EXCLUSIVELY on pain points, frustrations, friction, and failures. Ignore any positive feedback or praise.
4. Distinguish between different types of memory anchors and forgotten metadata
5. Be specific and evidence-based — avoid speculation without supporting data

CRITICAL REQUIREMENT: Your final response MUST be extremely concise. Summarize your findings in exactly two or three short sentences. Do not output a long essay.

When citing evidence, use this format:
- "[Reddit user]: exact quote..." 
- "[Google Play reviewer]: exact quote..."

Structure your response for immediate readability."""


# ─── Discovery Question Prompts ─────────────────────────────────────────────

DISCOVERY_PROMPTS = {
    "photo_types": """Based on the user feedback provided, analyze and categorize:

**What kinds of old photos do users struggle to retrieve?**

Organize your analysis by:
1. **Photo categories** (e.g., event photos, family photos, travel photos)
2. **Time dimension** — How old are these photos? Is there a pattern in the age?
3. **Emotional significance** — Are they struggling more with emotionally important or casual photos?
4. **Frequency ranking** — Which types are mentioned most often?

Provide specific user quotes as evidence for each category.""",

    "what_users_remember": """Based on the user feedback provided, analyze:

**What information do people actually remember about a photo?**

Categorize the memory anchors users rely on:
1. **People** — Who was in the photo
2. **Emotions/Feelings** — How it made them feel
3. **Visual attributes** — Colors, clothing, objects
4. **Events** — What was happening (wedding, birthday, trip)
5. **Temporal context** — Approximate time, season, or relative timing
6. **Spatial context** — General location or setting (not exact GPS)
7. **Adjacent memories** — What happened before/after

Rank these anchors by how frequently users mention them.""",

    "what_users_forget": """Based on the user feedback provided, analyze:

**What information have users forgotten about their photos?**

Categorize the forgotten metadata:
1. **Exact dates** — Specific day, month, or even year
2. **Precise locations** — GPS coordinates, exact venue names
3. **Device/Technical info** — Which phone, camera settings
4. **Album organization** — Which folder or album it was in
5. **File names** — Original filenames
6. **Who took the photo** — Photographer identity
7. **Sharing history** — Who they shared it with

Create a "metadata forgetting heatmap" ranking from most to least forgotten.""",

    "search_strategies": """Based on the user feedback provided, analyze:

**How do users formulate searches when their memory is incomplete?**

Document the search strategies users employ:
1. **Visual attribute searches** — "the photo with the red car"
2. **Temporal approximation** — "around Christmas 2019"
3. **People-based searches** — "photos with my sister"
4. **Event-based searches** — "from the wedding"
5. **Location-based searches** — "photos from Japan"
6. **Combination searches** — Multiple criteria combined
7. **Scroll/Browse strategies** — Manual timeline browsing

For each strategy, note:
- How often it's used
- Whether it typically succeeds or fails
- What platform features support or fail this strategy""",

    "failure_cascades": """Based on the user feedback provided, analyze:

**What are the cascading failure loops when initial photo searches fail?**

Map the typical user journey after a search fails:
1. **Initial search attempt** — What did they try first?
2. **Fallback strategies** — What do they try next?
3. **Escalation patterns** — Do they refine, broaden, or change approach?
4. **Emotional progression** — How does frustration build?
5. **Give-up threshold** — When do users abandon the search?
6. **Workarounds** — What alternative methods do they resort to?
7. **Feature requests** — What do they wish existed?

Document specific user stories that illustrate these failure cascades.""",

    "ask_vs_search": """Based on the user feedback provided, analyze:

**How do users react to the new AI 'Ask' replacing classic 'Search'?**

Categorize the user feedback:
1. **Specific noun/keyword failures** — How does the AI handle simple noun searches (e.g., specific animals, items)?
2. **Chronological/Temporal issues** — Are users struggling with how results are sorted?
3. **Abstract vs Concrete success** — Where does the AI succeed compared to the old keyword search?
4. **User frustration & workarounds** — How frustrated are users and how are they bypassing the new feature?
5. **Irrelevant results** — Are users seeing more irrelevant or hallucinated results?

Synthesize these points using direct user quotes to contrast the old 'Search' with the new 'Ask' feature.""",
}


# ─── Context Formatting ─────────────────────────────────────────────────────

def format_context_chunks(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a context string for the LLM prompt.

    Args:
        chunks: List of dicts with 'text', 'metadata', and 'score' keys

    Returns:
        Formatted context string with numbered excerpts and source labels
    """
    if not chunks:
        return "(No relevant user feedback found in the corpus.)"

    lines = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source_platform", "unknown")
        score = chunk.get("score", 0)
        text = metadata.get("text", chunk.get("text", ""))

        # Build source label
        source_label = f"[{source}]"
        if metadata.get("app_referenced"):
            source_label += f" ({metadata['app_referenced']})"

        lines.append(
            f"--- Excerpt {i} {source_label} (relevance: {score:.3f}) ---\n"
            f"{text}\n"
        )

    return "\n".join(lines)


def build_rag_prompt(
    query: str,
    context_chunks: list[dict],
    sources: list[str],
    discovery_key: str | None = None,
) -> list[dict]:
    """
    Build the full prompt messages for the Groq API.

    Args:
        query: The user's research question
        context_chunks: Retrieved and ranked chunks
        sources: List of source platform names included
        discovery_key: Optional key into DISCOVERY_PROMPTS for specialized prompting

    Returns:
        List of message dicts for the Groq chat API
    """
    # Build system message
    sources_str = ", ".join(sources) if sources else "multiple platforms"
    system_message = SYSTEM_PROMPT.format(sources=sources_str)

    # Build the context
    context = format_context_chunks(context_chunks)

    # Determine the question prompt
    if discovery_key and discovery_key in DISCOVERY_PROMPTS:
        question = DISCOVERY_PROMPTS[discovery_key]
    else:
        question = query

    # Build user message
    user_message = (
        f"Given the following user feedback excerpts:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Answer the following research question with evidence-based insights:\n\n"
        f"{question}"
    )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
