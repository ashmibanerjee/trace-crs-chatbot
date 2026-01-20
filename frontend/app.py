"""
Chainlit Frontend Application
Modular UI for Sustainable Tourism CRS
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
    create_sample_query_actions,
    create_rating_actions,
    create_new_session
)


async def perform_soft_reset():
    """Clears session flags to allow for a fresh start without wiping the chat history."""
    cl.user_session.set("feedback_rating", None)
    cl.user_session.set("feedback_text_collected", None)
    cl.user_session.set("clarification_complete", False)
    cl.user_session.set("clarification_active", False)

    await cl.Message(
        content="Feel free to start a new search! I'm ready to recommend your next destination. 🌍",
        author="Assistant"
    ).send()

# ============================================================================
# Session Management
# ============================================================================

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session"""
    print(f"[CHAT_START] on_chat_start called, current conversation_id: {cl.user_session.get('conversation_id')}")

    # If the user has already seen the welcome message in this browser session, stop here.
    # Don't create or modify session_id in this case
    if cl.user_session.get("welcome_shown"):
        print(f"[CHAT_START] Welcome already shown, returning early with existing session")
        return

    # Only create session_id on first load
    session_id = await get_or_create_session_id()
    print(f"[CHAT_START] First load, conversation_id: {session_id}")

    # Initialize state
    await reset_session_state()

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

    await cl.Message(
        content=welcome_message,
        author="Assistant",
        actions=actions
    ).send()

    # Set the flag so this block doesn't run again
    cl.user_session.set("welcome_shown", True)


# ============================================================================
# Message Handling
# ============================================================================

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming user messages"""

    # Ensure we have a session_id (in case cl.user_session was reset)
    if not cl.user_session.get("conversation_id"):
        print(f"[WARNING] No conversation_id found, creating new one")
        await get_or_create_session_id()

    session_id = cl.user_session.get("conversation_id")
    print(f"[DEBUG] Processing message with conversation_id: {session_id}")

    # 1. CHECK IF WE ARE COLLECTING FEEDBACK TEXT
    feedback_rating = cl.user_session.get("feedback_rating")
    if feedback_rating and not cl.user_session.get("feedback_text_collected"):
        feedback_text = message.content.strip()
        cl.user_session.set("feedback_text_collected", True)

        is_skip = feedback_text.lower() in ['skip', 'no', 'none', 'n/a']
        save_text = None if is_skip else feedback_text

        await save_feedback(
            session_id=session_id,
            rating=feedback_rating,
            feedback_text=save_text
        )

        feedback_reply = "Thank you for your feedback! 🙏" if is_skip else "Thank you for your detailed feedback! 🙏"
        await cl.Message(content=feedback_reply, author="Assistant").send()

        # Create a new session for the next query (without showing welcome screen)
        new_session_id = await create_new_session()
        print(f"Created new session after feedback: {new_session_id}")

        # Show ready message
        await cl.Message(
            content="Feel free to start a new search! I'm ready to recommend your next destination. 🌍",
            author="Assistant"
        ).send()

        return

    # 2. NORMAL CHAT PROCESSING
    async with cl.Step(name="🤔 Thinking", type="llm") as step:
        try:
            response = await orchestrator.process_message(
                message=message.content,
                session_id=session_id,
                user_context={'timestamp': message.created_at}
            )

            # --- HANDLE OUT-OF-SCOPE REQUEST ---
            if response.get("type") == "out_of_scope" or response.get("question_id") == -1:
                step.output = "Out-of-scope request detected."

                # Get text or use a descriptive fallback
                reason = response.get('text')
                if not reason:
                    reason = "I specialize in European city trip recommendations. Please ask about city destinations!"

                await cl.Message(content=reason, author="Assistant").send()

                # Create a new session with timestamp-based ID for next query
                new_session_id = await create_new_session()
                print(f"Created new session after out-of-scope query: {new_session_id}")

                return

            # Update normal clarification state
            if response.get('type') in ['clarification_question', 'clarification_complete']:
                cl.user_session.set("clarification_active", response.get('type') == 'clarification_question')

            step.output = f"Processed by {response['metadata'].get('agent_name', 'agent')}"

        except Exception as e:
            await cl.Message(
                content=f"⚠️ An error occurred: {str(e)}\n\nPlease try again.",
                author="System"
            ).send()
            return

    # Send the agent's response text (for normal clarification questions)
    await cl.Message(
        content=response['text'],
        author="Assistant"
    ).send()

    # 3. HANDLE PIPELINE TRIGGER (Recommendations)
    if response.get('type') == 'clarification_complete':
        cl.user_session.set("clarification_complete", True)

        if response.get('trigger_pipeline'):
            await cl.Message(
                content="✨ **Analyzing your preferences... This may take a moment.**",
                author="Assistant"
            ).send()

            async with cl.Step(name="🧠 Generating Recommendations", type="tool") as step:
                pipeline_result = await orchestrator.call_run_pipeline(session_id)
                if pipeline_result and 'error' in pipeline_result:
                    await asyncio.sleep(3)
                    pipeline_result = await orchestrator.call_run_pipeline(session_id)

                step.output = "Analysis complete."

            if pipeline_result and 'error' not in pipeline_result:
                await display_pipeline_results(pipeline_result)
            else:
                error_info = pipeline_result.get('error', 'Unknown Error') if pipeline_result else "Service Unreachable"
                await cl.Message(
                    content=f"⚠️ Issue generating recommendations: {error_info}",
                    author="Assistant"
                ).send()
                await display_feedback_request()

# ============================================================================
# UI Helpers
# ============================================================================

async def display_pipeline_results(pipeline_result: Dict[str, Any]):
    """Display the results from the pipeline execution"""
    try:
        context = pipeline_result.get('context', {})

        # 1. Persona Info
        intent_classification = context.get('intent_classification')
        if intent_classification:
            persona = intent_classification.get('user_travel_persona', 'Traveler')
            intent_text = f"### 🎯 Your Travel Profile\n**Persona:** {persona}"
            await cl.Message(content=intent_text, author="Assistant").send()

        # 2. The Main Recommendations
        cfe_rec = pipeline_result.get('cfe_recommendation', [])
        cfe_exp = pipeline_result.get('cfe_explanation', '')

        if cfe_rec:
            recs_formatted = ", ".join(cfe_rec) if isinstance(cfe_rec, list) else str(cfe_rec)
            rec_message = f"### 🌟 Your Recommendations\n**Destinations:** {recs_formatted}\n\n**Why?**\n{cfe_exp}"
            await cl.Message(content=rec_message, author="Assistant").send()

        # 3. Trigger Feedback
        await display_feedback_request()

    except Exception as e:
        print(f"Error in display: {e}")
        await display_feedback_request()


async def display_feedback_request():
    """Display feedback request with star rating options"""
    await cl.Message(
        content="### 💬 How did you like these recommendations?\nPlease rate your experience:",
        actions=create_rating_actions(),
        author="Assistant"
    ).send()


# ============================================================================
# Action Callbacks
# ============================================================================

async def handle_rating_feedback(rating: int):
    cl.user_session.set("feedback_rating", rating)

    await cl.Message(
        content=f"Thank you for rating us {rating}/5! ⭐",
        author="Assistant"
    ).send()

    await cl.Message(
        content="Any additional comments? (Or type 'skip' to finish)",
        author="Assistant"
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

@cl.action_callback("quick_reply")
async def on_quick_reply(action: cl.Action):
    val = action.payload.get("value", "")
    await cl.Message(content=val, author="User").send()
    await on_message(cl.Message(content=val))

@cl.action_callback("sample_query_1")
@cl.action_callback("sample_query_2")
@cl.action_callback("sample_query_3")
async def on_sample_query(action: cl.Action):
    query = action.payload.get("query", "")
    await cl.send_window_message({"type": "set_chat_input", "value": query})