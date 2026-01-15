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
    create_new_session,
    save_feedback,
    create_sample_query_actions,
    create_rating_actions
)


# ============================================================================
# Session Management
# ============================================================================

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session"""
    session_id = await get_or_create_session_id()
    await reset_session_state()

    welcome_message = """# Welcome to Sustainable Tourism Assistant! 🌍✨

I'm here to help you discover eco-friendly travel destinations tailored to your preferences.
> **🏙️ City trips only (for now)**
> Please ask only about city trips where I can recommend you cities to visit.
---
### 📝 How it works:

1. **Share your travel preferences** → Tell me what you're looking for
2. **Answer clarifying questions** → I'll ask targeted questions to understand your needs. 
Please try to be as specific as possible. This helps me understand your preferences better.
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


# ============================================================================
# Message Handling
# ============================================================================

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming user messages"""

    # Get session info
    session_id = cl.user_session.get("id")

    # Check if we're expecting feedback text
    feedback_rating = cl.user_session.get("feedback_rating")
    if feedback_rating and not cl.user_session.get("feedback_text_collected"):
        # This is the feedback text
        feedback_text = message.content.strip()

        # Mark that we've collected the text feedback
        cl.user_session.set("feedback_text_collected", True)

        # Skip if user doesn't want to provide feedback
        if feedback_text.lower() in ['skip', 'no', 'none', 'n/a']:
            await save_feedback(
                session_id=session_id,
                rating=feedback_rating,
                feedback_text=None
            )
            await cl.Message(
                content="Thank you for your feedback! 🙏",
                author="Assistant"
            ).send()
        else:
            # Save the feedback
            await save_feedback(
                session_id=session_id,
                rating=feedback_rating,
                feedback_text=feedback_text
            )
            await cl.Message(
                content="Thank you for your detailed feedback! We really appreciate it. 🙏",
                author="Assistant"
            ).send()

        # Clear the feedback state and create new session for next conversation
        cl.user_session.set("feedback_rating", None)
        await create_new_session()

        # Inform user that a new session has started
        await cl.Message(
            content="Feel free to start a new search! I'm ready to help you find your next destination. 🌍",
            author="Assistant"
        ).send()
        return

    # Show processing indicator
    async with cl.Step(name="🤔 Thinking", type="tool") as step:
        # Call orchestrator (user_type will be inferred by backend)
        # The orchestrator automatically handles active clarification flows
        try:
            response = await orchestrator.process_message(
                message=message.content,
                session_id=session_id,
                user_context={
                    'timestamp': message.created_at
                }
            )

            # Check if this is a clarification response
            if response.get('type') in ['clarification_question', 'clarification_complete']:
                cl.user_session.set("clarification_active",
                                    response.get('type') == 'clarification_question')

            step.output = f"Processed by {response['metadata'].get('agent_name', 'agent')}"

        except Exception as e:
            await cl.Message(
                content=f"⚠️ An error occurred: {str(e)}\n\nPlease try again.",
                author="System"
            ).send()
            return

    # Send response (elements and actions handled by orchestrator)
    await cl.Message(
        content=response['text'],
        author="Assistant"
    ).send()

    # Handle clarification completion and display pipeline results
    if response.get('type') == 'clarification_complete':
        print(f"[Frontend] Clarification complete detected!")

        # Store that clarification is complete
        cl.user_session.set("clarification_complete", True)

        # Check if we need to trigger the pipeline
        if response.get('trigger_pipeline'):
            # Show processing messages
            await cl.Message(
                content="✨ **Analyzing your preferences... Please wait. This may take a few minutes**",
                author="Assistant"
            ).send()

            # Show a step-by-step progress indicator
            async with cl.Step(name="🧠 Understanding your travel profile", type="tool") as step:
                step.output = "Analyzing your answers..."

                async with cl.Step(name="🔍 Finding personalized recommendations", type="tool") as step2:
                    step2.output = "Searching for the best destinations..."

                    async with cl.Step(name="📊 Generating explanations", type="tool") as step3:
                        step3.output = "Creating your personalized report..."

                        # Now run the pipeline (retry once on 500 errors)
                        pipeline_result = await orchestrator.call_run_pipeline(session_id)
                        if pipeline_result and 'error' in pipeline_result:
                            error_text = str(pipeline_result.get('error'))
                            if "500 Internal Server Error" in error_text:
                                await asyncio.sleep(5)
                                pipeline_result = await orchestrator.call_run_pipeline(session_id)

                        step3.output = "Complete! ✓"
                    step2.output = "Complete! ✓"
                step.output = "Complete! ✓"

            # Display the results
            if pipeline_result and 'error' not in pipeline_result:
                await display_pipeline_results(pipeline_result)
            elif pipeline_result and 'error' in pipeline_result:
                print(f"[Frontend] Pipeline error: {pipeline_result.get('error')}")
                await cl.Message(
                    content=f"⚠️ There was an issue processing your recommendations: {pipeline_result.get('error')}",
                    author="Assistant"
                ).send()
            else:
                await cl.Message(
                    content="⚠️ Unable to generate recommendations at this time. Please try again.",
                    author="Assistant"
                ).send()

    # Show debug info if enabled
    if settings.debug and response.get('debug_info'):
        debug_info = response['debug_info']
        await cl.Message(
            content=f"**Debug Info:**\n```json\n{debug_info}\n```",
            author="System"
        ).send()


# ============================================================================
# Helper Functions
# ============================================================================

async def display_pipeline_results(pipeline_result: Dict[str, Any]):
    """
    Display the results from the pipeline execution
    
    Args:
        pipeline_result: The CFE output from the run-pipeline endpoint
    """
    try:
        # Debug: Print the pipeline result structure
        print(f"[Frontend] Pipeline result keys: {pipeline_result.keys()}")
        print(f"[Frontend] Pipeline result: {pipeline_result}")

        # Extract key information from the pipeline result (CFEOutput structure)
        context = pipeline_result.get('context', {})
        intent_classification = context.get('intent_classification') if context else None

        # Display intent classification if available
        if intent_classification:
            persona = intent_classification.get('user_travel_persona', 'Unknown')
            travel_intent = intent_classification.get('travel_intent', 'Not specified')

            intent_text = f"""### 🎯 Your Travel Profile

**Persona:** {persona}  
**Travel Intent:** {travel_intent}
"""
            await cl.Message(
                content=intent_text,
                author="Assistant"
            ).send()

        # Display the main CFE recommendation
        cfe_recommendation = pipeline_result.get('cfe_recommendation', [])
        cfe_explanation = pipeline_result.get('cfe_explanation', '')
        cfe_trade_off = pipeline_result.get('cfe_trade_off')

        print(f"[Frontend] cfe_recommendation: {cfe_recommendation}")
        print(f"[Frontend] cfe_explanation: {cfe_explanation[:100] if cfe_explanation else 'None'}...")

        if cfe_recommendation:
            # Format recommendations
            if isinstance(cfe_recommendation, list):
                recs_text = ", ".join(str(r) for r in cfe_recommendation)
            else:
                recs_text = str(cfe_recommendation)

            recommendation_text = f"""### 🌟 Your Personalized Recommendations

**Destinations:** {recs_text}

**Why these recommendations?**
{cfe_explanation}
"""

            if cfe_trade_off:
                recommendation_text += f"\n\n**Trade-offs:**\n{cfe_trade_off}"

            await cl.Message(
                content=recommendation_text,
                author="Assistant"
            ).send()
        else:
            print("[Frontend] WARNING: No cfe_recommendation found in pipeline result")
            # Show a fallback message with whatever we have
            if cfe_explanation:
                await cl.Message(
                    content=f"### 🌟 Your Recommendations\n\n{cfe_explanation}",
                    author="Assistant"
                ).send()

        # Display comparison insights if available
        if context:
            baseline_rec = context.get('baseline_recommendation')
            context_rec = context.get('context_aware_recommendation')

            if baseline_rec and context_rec:
                comparison_text = """### 📊 Understanding Your Recommendations

**Context-Aware vs Baseline Comparison:**
"""
                # Show how context improved recommendations
                context_cities = context_rec.get('recommendation', [])
                baseline_cities = baseline_rec.get('recommendation', [])

                if context_cities != baseline_cities:
                    comparison_text += f"\nOur personalized system recommended **{context_cities if isinstance(context_cities, str) else ', '.join(context_cities)}** based on your preferences, "
                    comparison_text += f"while a generic search might have suggested **{baseline_cities if isinstance(baseline_cities, str) else ', '.join(baseline_cities)}**.\n"

                    if context_rec.get('explanation'):
                        comparison_text += f"\n**Why the difference?** {context_rec['explanation']}"

                await cl.Message(
                    content=comparison_text,
                    author="Assistant"
                ).send()

        # Display feedback request
        await display_feedback_request()

    except Exception as e:
        print(f"Error displaying pipeline results: {e}")
        import traceback
        traceback.print_exc()
        await cl.Message(
            content=f"⚠️ Error displaying recommendations: {str(e)}\n\nPlease check the logs for details.",
            author="Assistant"
        ).send()
        # Still show feedback even if there was an error displaying results
        await display_feedback_request()


async def display_feedback_request():
    """Display feedback request with star rating options"""
    feedback_text = """### 💬 How did you like these recommendations?

Please rate your experience and share any feedback to help us improve!"""

    # Disable input while waiting for rating selection
    await cl.send_window_message({
        "type": "set_input_disabled",
        "value": True
    })

    await cl.Message(
        content=feedback_text,
        actions=create_rating_actions(),
        author="Assistant"
    ).send()


# ============================================================================
# Action Handlers
# ============================================================================

@cl.action_callback("quick_reply")
async def on_quick_reply(action: cl.Action):
    """Handle quick reply button clicks"""
    value = action.payload.get("value", "")

    # Process the value by calling on_message
    # Chainlit will automatically attribute the user's message in on_message
    # but we need to display it first.
    await cl.Message(content=value).send()
    await on_message(cl.Message(content=value))


async def handle_sample_query(query: str):
    """Handle sample query button clicks"""
    # Populate the chat input instead of auto-sending the message
    # This lets the user review/edit and press Enter.
    await cl.send_window_message({
        "type": "set_chat_input",
        "value": query
    })


@cl.action_callback("sample_query_1")
async def on_sample_query_1(action: cl.Action):
    """Handle sample query 1"""
    await handle_sample_query(action.payload["query"])


@cl.action_callback("sample_query_2")
async def on_sample_query_2(action: cl.Action):
    """Handle sample query 2"""
    await handle_sample_query(action.payload["query"])


@cl.action_callback("sample_query_3")
async def on_sample_query_3(action: cl.Action):
    """Handle sample query 3"""
    await handle_sample_query(action.payload["query"])


async def handle_rating_feedback(rating: int):
    """Handle rating feedback submission"""
    session_id = cl.user_session.get("id")
    cl.user_session.set("feedback_rating", rating)

    # Re-enable input so user can type optional feedback
    await cl.send_window_message({
        "type": "set_input_disabled",
        "value": False
    })

    await cl.Message(
        content=f"Thank you for rating us {'⭐' * rating} ({rating}/5)!",
        author="Assistant"
    ).send()

    await cl.Message(
        content="Would you like to share any additional comments? (Optional - you can skip this by typing 'skip' or just provide your feedback)",
        author="Assistant"
    ).send()


# Rating action callbacks
@cl.action_callback("rating_1")
async def on_rating_1(action: cl.Action):
    await handle_rating_feedback(1)


@cl.action_callback("rating_2")
async def on_rating_2(action: cl.Action):
    await handle_rating_feedback(2)


@cl.action_callback("rating_3")
async def on_rating_3(action: cl.Action):
    await handle_rating_feedback(3)


@cl.action_callback("rating_4")
async def on_rating_4(action: cl.Action):
    await handle_rating_feedback(4)


@cl.action_callback("rating_5")
async def on_rating_5(action: cl.Action):
    await handle_rating_feedback(5)
