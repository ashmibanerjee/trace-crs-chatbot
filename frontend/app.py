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
    save_feedback_answer,
    load_feedback_questions,
    create_sample_query_actions,
    create_rating_actions,
    create_new_session
)


async def perform_soft_reset():
    """Clears session flags to allow for a fresh start without wiping the chat history."""
    cl.user_session.set("feedback_rating", None)
    cl.user_session.set("feedback_text_collected", None)
    cl.user_session.set("feedback_in_progress", False)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("waiting_for_feedback_text", False)
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

    # 1. CHECK IF FEEDBACK TEXT INPUT IS EXPECTED (for free-text questions only)
    waiting_for_text = cl.user_session.get("waiting_for_feedback_text", False)

    print(f"[DEBUG] waiting_for_feedback_text: {waiting_for_text}")

    if waiting_for_text:
        # Process the text response for free-text feedback question
        print(f"[DEBUG] Processing text feedback response")
        feedback_text = message.content.strip()
        questions = cl.user_session.get("feedback_questions", [])
        current_index = cl.user_session.get("current_feedback_question_index", 0)

        if current_index < len(questions):
            question_data = questions[current_index]
            is_skip = feedback_text.lower() in ['skip', 'no', 'none', 'n/a']
            save_text = None if is_skip else feedback_text

            # Save the feedback answer
            await save_feedback_answer(
                session_id=session_id,
                q_id=question_data.get("q_id"),
                question=question_data.get("question"),
                answer=save_text if save_text else "skipped"
            )

            # Move to next question
            cl.user_session.set("current_feedback_question_index", current_index + 1)
            cl.user_session.set("waiting_for_feedback_text", False)

            # Display next question
            await display_current_feedback_question()

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
        print(f"[DEBUG] display_pipeline_results called")
        context = pipeline_result.get('context') or {}

        # 1. Persona Info
        intent_classification = context.get('intent_classification') if context else None
        if intent_classification:
            persona = intent_classification.get('user_travel_persona', 'Traveler')
            intent_text = f"### 🎯 Your Travel Profile\n**Persona:** {persona}"
            print(f"[DEBUG] Sending persona info")
            await cl.Message(content=intent_text, author="Assistant").send()

        # 2. The Main Recommendations
        cfe_rec = pipeline_result.get('recommendation_shown', [])
        cfe_exp = pipeline_result.get('explanation_shown', '')
        is_sustainable = pipeline_result.get('is_recommendation_sustainable', False)

        print(f"[DEBUG] cfe_rec: {cfe_rec}, cfe_exp length: {len(cfe_exp) if cfe_exp else 0}, is_sustainable: {is_sustainable}")

        if cfe_rec:
            recs_formatted = ", ".join(cfe_rec) if isinstance(cfe_rec, list) else str(cfe_rec)

            # Add sustainability badge if the recommendation is sustainable
            if is_sustainable:
                rec_message = f"### 🌟 Your Recommendations 🌱✨\n**Destinations:** {recs_formatted} **[Sustainable Choice]** 🌿\n\n**Why?**\n{cfe_exp}"
            else:
                rec_message = f"### 🌟 Your Recommendations\n**Destinations:** {recs_formatted}\n\n**Why?**\n{cfe_exp}"

            print(f"[DEBUG] Sending recommendations")
            await cl.Message(content=rec_message, author="Assistant").send()

            # Store for feedback question
            cl.user_session.set("recommendation_shown", recs_formatted)

        # 3. Alternative Recommendation (if available)
        alt_rec = pipeline_result.get('alternative_recommendation')
        alt_exp = pipeline_result.get('alternative_explanation', '')

        print(f"[DEBUG] alt_rec: {alt_rec}, alt_exp length: {len(alt_exp) if alt_exp else 0}")

        if alt_rec:
            alt_formatted = ", ".join(alt_rec) if isinstance(alt_rec, list) else str(alt_rec)

            # Add sustainability badge if the main recommendation is NOT sustainable
            # (meaning the alternative is the sustainable option)
            if not is_sustainable:
                alt_message = f"### 🔄 Alternative Option 🌱✨\n**Destinations:** {alt_formatted} **[Sustainable Choice]** 🌿\n\n**Why this alternative?**\n{alt_exp}"
            else:
                alt_message = f"### 🔄 Alternative Option\n**Destinations:** {alt_formatted}\n\n**Why this alternative?**\n{alt_exp}"

            print(f"[DEBUG] Sending alternative recommendations")
            await cl.Message(content=alt_message, author="Assistant").send()

            # Store for feedback question
            cl.user_session.set("alternative_recommendation", alt_formatted)

        # 4. Trigger Feedback
        print(f"[DEBUG] Calling display_feedback_request")
        await display_feedback_request()

    except Exception as e:
        print(f"Error in display: {e}")
        import traceback
        traceback.print_exc()
        await display_feedback_request()


async def display_feedback_request():
    """Display first feedback question from feedback_questions.json"""
    print(f"[DEBUG] display_feedback_request called")
    # Load feedback questions
    questions = load_feedback_questions()

    print(f"[DEBUG] Loaded {len(questions)} feedback questions")

    if not questions:
        print("No feedback questions found, skipping feedback collection")
        return

    # Initialize feedback state
    cl.user_session.set("feedback_in_progress", True)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("feedback_questions", questions)
    cl.user_session.set("waiting_for_feedback_text", False)

    print(f"[DEBUG] Set feedback_in_progress=True, calling display_current_feedback_question")

    # Display first question
    await display_current_feedback_question()


async def display_current_feedback_question():
    """Display the current feedback question based on index"""
    questions = cl.user_session.get("feedback_questions", [])
    current_index = cl.user_session.get("current_feedback_question_index", 0)

    print(f"[DEBUG] display_current_feedback_question: index={current_index}, total={len(questions)}")

    if current_index >= len(questions):
        # All questions answered, finish feedback collection
        print(f"[DEBUG] All questions answered, finishing feedback collection")
        await finish_feedback_collection()
        return

    question_data = questions[current_index]
    question_text = question_data.get("question", "")
    options = question_data.get("options", [])

    print(f"[DEBUG] Question {current_index}: has {len(options)} options")

    if options:
        # Question with radio button options - Use AskActionMessage to lock input
        print(f"[DEBUG] Displaying radio button question with AskActionMessage")
        session_id = cl.user_session.get("conversation_id")

        actions = []
        for option in options:
            option_id = option.get("option_id")
            label = option.get("label", "")

            # Dynamically populate first question (q_id: 0) with actual recommendations
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
                    payload={"option_id": option_id}
                )
            )

        # AskActionMessage locks the chat input until user clicks a button
        res = await cl.AskActionMessage(
            content=question_text,
            actions=actions,
            timeout=300  # 5 minutes timeout
        ).send()

        print(f"[DEBUG] User selected res: {res}")
        print(f"[DEBUG] Type of res: {type(res)}")
        print(f"[DEBUG] res.__dict__: {res.__dict__ if hasattr(res, '__dict__') else 'N/A'}")

        if res:
            # Access the option_id from the response payload
            selected_value = res.get("payload", {}).get("option_id") if isinstance(res, dict) else None
            selected_label = res.get("label") if isinstance(res, dict) else None
            print(f"[DEBUG] Selected value: {selected_value}")
            print(f"[DEBUG] Selected label: {selected_label}")

            # Find the selected option details
            selected_option = next((opt for opt in options if opt.get("option_id") == selected_value), None)
            print(f"[DEBUG] Selected option: {selected_option}")

            if selected_option:
                # Save the feedback answer using the label from response
                print(f"[DEBUG] Saving feedback answer for q_id={question_data.get('q_id')}")
                await save_feedback_answer(
                    session_id=session_id,
                    q_id=question_data.get("q_id"),
                    question=question_text,
                    answer=selected_label,  # Use label from response
                    option_id=selected_value  # Use option_id from payload
                )

                # Show confirmation message with question and selected answer
                # Strip markdown headers from question for cleaner display
                clean_question = question_text.replace("###", "").replace("**", "").strip()
                await cl.Message(
                    content=f"✅ {clean_question}\n**Selected:** {selected_label}",
                    author="Assistant"
                ).send()

                # Move to next question
                new_index = current_index + 1
                cl.user_session.set("current_feedback_question_index", new_index)
                print(f"[DEBUG] Moving to question index: {new_index}")

                # Display next question
                await display_current_feedback_question()
            else:
                print(f"[DEBUG] Could not find selected option, finishing feedback")
                await finish_feedback_collection()
        else:
            print(f"[DEBUG] User timeout or cancelled feedback")
            await finish_feedback_collection()

    else:
        # Free text question
        print(f"[DEBUG] Displaying free text question")
        cl.user_session.set("waiting_for_feedback_text", True)

        await cl.Message(
            content=f"{question_text}\n(Or type 'skip' to skip this question)",
            author="Assistant"
        ).send()
        print(f"[DEBUG] Free text question sent")


async def finish_feedback_collection():
    """Complete feedback collection and start new session"""
    print(f"[DEBUG] finish_feedback_collection called")

    cl.user_session.set("feedback_in_progress", False)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("waiting_for_feedback_text", False)

    await cl.Message(
        content="Thank you for your feedback! 🙏",
        author="Assistant"
    ).send()

    # Create a new session for the next query
    new_session_id = await create_new_session()
    print(f"Created new session after feedback: {new_session_id}")

    await cl.Message(
        content="Feel free to start a new search! I'm ready to recommend your next destination. 🌍",
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