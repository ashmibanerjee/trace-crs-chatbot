"""
Chainlit Frontend Application
Modular UI for Sustainable Tourism CRS.

Two model profiles are available at session start:
  • Gemma (Free) — runs via HF Inference API, no key needed
  • Gemini (Your Key) — user must paste their own Google Gemini API key
"""
import chainlit as cl
import asyncio
from typing import Dict, Any
from middleware.orchestrator import orchestrator
from config import settings
from frontend.helpers import (
    get_or_create_session_id,
    reset_session_state,
    save_feedback,
    save_feedback_answer,
    load_feedback_questions,
    create_sample_query_actions,
    create_rating_actions,
    create_new_session,
)

# ---------------------------------------------------------------------------
# Model profile definitions
# ---------------------------------------------------------------------------

PROFILE_GEMMA = "Gemma (Free)"
PROFILE_GEMINI = "Gemini (Your Key)"


@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name=PROFILE_GEMMA,
            markdown_description=(
                "**Powered by Google Gemma via 🤗 HF Inference API** — no key needed.\n\n"
                "Recommended for the demo. Completely free."
            ),
        ),
        cl.ChatProfile(
            name=PROFILE_GEMINI,
            markdown_description=(
                "**Powered by Google Gemini** — you supply your own API key.\n\n"
                "The key is kept in memory for this session only and is never stored or logged."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_model_context():
    """Return (model_provider, api_key) from the current Chainlit session."""
    profile = cl.user_session.get("chat_profile", PROFILE_GEMMA)
    model_provider = "gemini" if profile == PROFILE_GEMINI else "gemma"
    # api_key is only set for Gemini profile — never expose it outside this module
    api_key = cl.user_session.get("_gemini_api_key") if model_provider == "gemini" else None
    return model_provider, api_key


async def perform_soft_reset():
    cl.user_session.set("feedback_rating", None)
    cl.user_session.set("feedback_text_collected", None)
    cl.user_session.set("feedback_in_progress", False)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("waiting_for_feedback_text", False)
    cl.user_session.set("clarification_complete", False)
    cl.user_session.set("clarification_active", False)

    await cl.Message(
        content="Feel free to start a new search! I'm ready to recommend your next destination. 🌍",
        author="Assistant",
    ).send()


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    print(f"[CHAT_START] on_chat_start called")

    if cl.user_session.get("welcome_shown"):
        return

    session_id = await get_or_create_session_id()
    await reset_session_state()

    # ---- Welcome message (shown first for all profiles) ----
    welcome_message = """# Sustainable Tourism Assistant for European Cities! 🌍✨

I'm here to help you discover eco-friendly travel destinations tailored to your preferences.
> **🏙️ City trips only (for now)**
> Please ask only about city trips where I can recommend you cities to visit.
Right now, I specialize in city destinations only within Europe.
---
### 📝 How it works:

1. **Share your travel preferences** → Tell me what you're looking for
2. **Answer clarifying questions** → I'll ask targeted questions to understand your needs.
3. **Get personalized recommendations** → Receive curated suggestions based on your answers
4. **Provide feedback** → Help us improve by rating your experience

> 💡 *Please be patient—analysis may take a few minutes to ensure quality recommendations.*

---
**Ready to start? Try one of these examples or ask your own question:**
"""

    actions = create_sample_query_actions(seed=session_id)
    await cl.Message(content=welcome_message, author="Assistant", actions=actions).send()
    cl.user_session.set("welcome_shown", True)

    # ---- Gemini: collect API key after welcome ----
    profile = cl.user_session.get("chat_profile", PROFILE_GEMMA)
    if profile == PROFILE_GEMINI:
        await cl.Message(
            content=(
                "### 🔑 Gemini API Key Required\n\n"
                "To use Gemini you need to provide your own **Google Gemini API key**.\n\n"
                "> Your key is kept in server memory for this session only — "
                "**never stored to disk or logged**.\n\n"
                "You can get a free key at [aistudio.google.com](https://aistudio.google.com/apikey)."
            ),
            author="Assistant",
        ).send()

        res = await cl.AskUserMessage(
            content="Please paste your Gemini API key below:",
            timeout=120,
        ).send()

        if not res or not res.get("output", "").strip():
            await cl.Message(
                content="No API key provided — falling back to **Gemma (Free)** mode.",
                author="Assistant",
            ).send()
            cl.user_session.set("chat_profile", PROFILE_GEMMA)
        else:
            raw_key = res["output"].strip()
            cl.user_session.set("_gemini_api_key", raw_key)
            await cl.Message(content="✅ Key received. You can now send your query!", author="Assistant").send()


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------

@cl.on_message
async def on_message(message: cl.Message):
    if not cl.user_session.get("conversation_id"):
        await get_or_create_session_id()

    session_id = cl.user_session.get("conversation_id")
    model_provider, api_key = _get_model_context()
    print(f"[DEBUG] Processing message | session={session_id} | provider={model_provider}")

    # 1. Feedback text input
    if cl.user_session.get("waiting_for_feedback_text", False):
        feedback_text = message.content.strip()
        questions = cl.user_session.get("feedback_questions", [])
        current_index = cl.user_session.get("current_feedback_question_index", 0)

        if current_index < len(questions):
            question_data = questions[current_index]
            is_skip = feedback_text.lower() in ["skip", "no", "none", "n/a"]
            save_text = None if is_skip else feedback_text

            await save_feedback_answer(
                session_id=session_id,
                q_id=question_data.get("q_id"),
                question=question_data.get("question"),
                answer=save_text if save_text else "skipped",
            )
            cl.user_session.set("current_feedback_question_index", current_index + 1)
            cl.user_session.set("waiting_for_feedback_text", False)
            await display_current_feedback_question()
        return

    # 2. Normal chat processing
    async with cl.Step(name="🤔 Thinking", type="llm") as step:
        try:
            response = await orchestrator.process_message(
                message=message.content,
                session_id=session_id,
                user_context={"timestamp": message.created_at},
                model_provider=model_provider,
                api_key=api_key,
            )

            if response.get("type") == "out_of_scope" or response.get("question_id") == -1:
                step.output = "Out-of-scope request detected."
                reason = response.get("text") or "I specialize in European city trip recommendations."
                await cl.Message(content=reason, author="Assistant").send()
                await create_new_session()
                return

            if response.get("type") in ["clarification_question", "clarification_complete"]:
                cl.user_session.set(
                    "clarification_active", response.get("type") == "clarification_question"
                )

            step.output = f"Processed by {response['metadata'].get('agent_name', 'agent')}"

        except Exception as e:
            await cl.Message(
                content=f"⚠️ An error occurred: {str(e)}\n\nPlease try again.",
                author="System",
            ).send()
            return

    await cl.Message(content=response["text"], author="Assistant").send()

    # 3. Pipeline trigger after clarification completes
    if response.get("type") == "clarification_complete":
        cl.user_session.set("clarification_complete", True)

        if response.get("trigger_pipeline"):
            await cl.Message(
                content="✨ **Analyzing your preferences... This may take a moment.**",
                author="Assistant",
            ).send()

            async with cl.Step(name="🧠 Generating Recommendations", type="tool") as step:
                pipeline_result = await orchestrator.call_run_pipeline(
                    session_id, model_provider=model_provider, api_key=api_key
                )
                if pipeline_result and "error" in pipeline_result:
                    await asyncio.sleep(3)
                    pipeline_result = await orchestrator.call_run_pipeline(
                        session_id, model_provider=model_provider, api_key=api_key
                    )
                step.output = "Analysis complete."

            if pipeline_result and "error" not in pipeline_result:
                await display_pipeline_results(pipeline_result)
            else:
                error_info = (
                    pipeline_result.get("error", "Unknown Error") if pipeline_result else "Service Unreachable"
                )
                await cl.Message(
                    content=f"⚠️ Issue generating recommendations: {error_info}",
                    author="Assistant",
                ).send()
                await display_feedback_request()


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

async def display_pipeline_results(pipeline_result: Dict[str, Any]):
    try:
        context = pipeline_result.get("context") or {}

        intent_classification = context.get("intent_classification") if context else None
        if intent_classification:
            persona = intent_classification.get("user_travel_persona", "Traveler")
            await cl.Message(
                content=f"### 🎯 Your Travel Profile\n**Persona:** {persona}",
                author="Assistant",
            ).send()

        cfe_rec = pipeline_result.get("recommendation_shown", [])
        cfe_exp = pipeline_result.get("explanation_shown", "")
        is_sustainable = pipeline_result.get("is_recommendation_sustainable", False)

        if cfe_rec:
            recs_formatted = ", ".join(cfe_rec) if isinstance(cfe_rec, list) else str(cfe_rec)
            if is_sustainable:
                rec_msg = (
                    f"### 🌟 Your Recommendations 🌱✨\n"
                    f"**Destinations:** {recs_formatted} **[Sustainable Choice]** 🌿\n\n**Why?**\n{cfe_exp}"
                )
            else:
                rec_msg = (
                    f"### 🌟 Your Recommendations\n"
                    f"**Destinations:** {recs_formatted}\n\n**Why?**\n{cfe_exp}"
                )
            await cl.Message(content=rec_msg, author="Assistant").send()
            cl.user_session.set("recommendation_shown", recs_formatted)

        alt_rec = pipeline_result.get("alternative_recommendation")
        alt_exp = pipeline_result.get("alternative_explanation", "")

        if alt_rec:
            alt_formatted = ", ".join(alt_rec) if isinstance(alt_rec, list) else str(alt_rec)
            if not is_sustainable:
                alt_msg = (
                    f"### 🔄 Alternative Option 🌱✨\n"
                    f"**Destinations:** {alt_formatted} **[Sustainable Choice]** 🌿\n\n**Why this alternative?**\n{alt_exp}"
                )
            else:
                alt_msg = (
                    f"### 🔄 Alternative Option\n"
                    f"**Destinations:** {alt_formatted}\n\n**Why this alternative?**\n{alt_exp}"
                )
            await cl.Message(content=alt_msg, author="Assistant").send()
            cl.user_session.set("alternative_recommendation", alt_formatted)

        await display_feedback_request()

    except Exception as e:
        print(f"Error in display_pipeline_results: {e}")
        import traceback
        traceback.print_exc()
        await display_feedback_request()


async def display_feedback_request():
    questions = load_feedback_questions()
    if not questions:
        return

    cl.user_session.set("feedback_in_progress", True)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("feedback_questions", questions)
    cl.user_session.set("waiting_for_feedback_text", False)
    await display_current_feedback_question()


async def display_current_feedback_question():
    questions = cl.user_session.get("feedback_questions", [])
    current_index = cl.user_session.get("current_feedback_question_index", 0)

    if current_index >= len(questions):
        await finish_feedback_collection()
        return

    question_data = questions[current_index]
    question_text = question_data.get("question", "")
    options = question_data.get("options", [])

    if options:
        session_id = cl.user_session.get("conversation_id")
        actions = []
        for option in options:
            option_id = option.get("option_id")
            label = option.get("label", "")
            if question_data.get("q_id") == 0:
                if option_id == 1:
                    city_name = cl.user_session.get("recommendation_shown", "Option 1")
                    label = f"1️⃣ {city_name} (recommended)"
                elif option_id == 2:
                    city_name = cl.user_session.get("alternative_recommendation", "Option 2")
                    label = f"2️⃣ {city_name} (alternative)"
            actions.append(
                cl.Action(
                    name="feedback_option",
                    value=str(option_id),
                    label=label,
                    payload={"option_id": option_id},
                )
            )

        res = await cl.AskActionMessage(
            content=question_text, actions=actions, timeout=600
        ).send()

        if res:
            selected_value = res.get("payload", {}).get("option_id") if isinstance(res, dict) else None
            selected_label = res.get("label") if isinstance(res, dict) else None
            selected_option = next((o for o in options if o.get("option_id") == selected_value), None)

            if selected_option:
                await save_feedback_answer(
                    session_id=session_id,
                    q_id=question_data.get("q_id"),
                    question=question_text,
                    answer=selected_label,
                    option_id=selected_value,
                )
                clean_question = question_text.replace("###", "").replace("**", "").strip()
                await cl.Message(
                    content=f"✅ {clean_question}\n**Selected:** {selected_label}",
                    author="Assistant",
                ).send()
                cl.user_session.set("current_feedback_question_index", current_index + 1)
                await display_current_feedback_question()
            else:
                await finish_feedback_collection()
        else:
            await finish_feedback_collection()
    else:
        cl.user_session.set("waiting_for_feedback_text", True)
        await cl.Message(
            content=f"{question_text}\n(Or type 'skip' to skip this question)",
            author="Assistant",
        ).send()


async def finish_feedback_collection():
    cl.user_session.set("feedback_in_progress", False)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("waiting_for_feedback_text", False)

    await cl.Message(content="Thank you for your feedback! 🙏", author="Assistant").send()
    await create_new_session()
    await cl.Message(
        content="Feel free to start a new search! I'm ready to recommend your next destination. 🌍",
        author="Assistant",
    ).send()


# ---------------------------------------------------------------------------
# Action callbacks
# ---------------------------------------------------------------------------

async def handle_rating_feedback(rating: int):
    cl.user_session.set("feedback_rating", rating)
    await cl.Message(content=f"Thank you for rating us {rating}/5! ⭐", author="Assistant").send()
    await cl.Message(
        content="Any additional comments? (Or type 'skip' to finish)", author="Assistant"
    ).send()


@cl.action_callback("rating_1")
async def on_rating_1(action: cl.Action): await handle_rating_feedback(1)
@cl.action_callback("rating_2")
async def on_rating_2(action: cl.Action): await handle_rating_feedback(2)
@cl.action_callback("rating_3")
async def on_rating_3(action: cl.Action): await handle_rating_feedback(3)
@cl.action_callback("rating_4")
async def on_rating_4(action: cl.Action): await handle_rating_feedback(4)
@cl.action_callback("rating_5")
async def on_rating_5(action: cl.Action): await handle_rating_feedback(5)


async def _dispatch_query(query: str):
    """Display the selected query as a user bubble, then process it."""
    await cl.Message(content=query, author="User", type="user_message").send()
    await on_message(cl.Message(content=query))


@cl.action_callback("quick_reply")
async def on_quick_reply(action: cl.Action):
    await _dispatch_query(action.payload.get("value", ""))


# Separate named functions — stacked @cl.action_callback decorators in
# Chainlit 2.x wrap each other and cause the handler to fire multiple times.
@cl.action_callback("sample_query_1")
async def on_sample_query_1(action: cl.Action):
    await _dispatch_query(action.payload.get("query", ""))


@cl.action_callback("sample_query_2")
async def on_sample_query_2(action: cl.Action):
    await _dispatch_query(action.payload.get("query", ""))


@cl.action_callback("sample_query_3")
async def on_sample_query_3(action: cl.Action):
    await _dispatch_query(action.payload.get("query", ""))
