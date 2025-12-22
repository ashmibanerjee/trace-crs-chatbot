"""
Chainlit Frontend Application
Modular UI for Sustainable Tourism CRS
"""
import chainlit as cl
from typing import Optional, Dict, Any
from middleware.orchestrator import orchestrator
from config import settings


# ============================================================================
# Session Management
# ============================================================================

@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session"""
    
    # Generate session ID
    session_id = cl.user_session.get("id")
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        cl.user_session.set("id", session_id)
    
    # Simple welcome message
    welcome_message = """# Welcome to Sustainable Tourism Assistant! 🌍✨

I'm here to help you discover eco-friendly travel destinations.

I can help you with:
- 🌿 Finding sustainable destinations
- 📊 Comparing carbon footprints  
- 🏆 Learning about eco-certifications
- 💚 Planning environmentally responsible trips

**Where would you like to go?**
"""
    
    await cl.Message(
        content=welcome_message,
        author="Assistant"
    ).send()


# Note: on_chat_end not supported in Chainlit 1.1.0
# @cl.on_chat_end
# async def on_chat_end():
#     """Clean up when chat ends"""
#     session_id = cl.user_session.get("id")
#     if session_id:
#         # Could save session data here
#         pass


# ============================================================================
# Message Handling
# ============================================================================

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming user messages"""
    
    # Get session info
    session_id = cl.user_session.get("id")
    
    # Show processing indicator
    async with cl.Step(name="🤔 Thinking", type="tool") as step:
        # Call orchestrator (user_type will be inferred by backend)
        try:
            response = await orchestrator.process_message(
                message=message.content,
                session_id=session_id,
                user_context={
                    'timestamp': message.created_at
                }
            )
            
            step.output = f"Processed by {response['metadata'].get('agent_name', 'agent')}"
        
        except Exception as e:
            await cl.Message(
                content=f"⚠️ An error occurred: {str(e)}\n\nPlease try again.",
                author="System"
            ).send()
            return
    
    # Build response elements
    elements = []
    
    # Add recommendation cards if present
    if response.get('elements'):
        for element in response['elements']:
            if element['type'] == 'card':
                card_data = element['data']
                
                # Create rich card display
                card_content = f"""### {card_data['title']}

{card_data['description']}

**🌱 Sustainability Score:** {card_data['sustainability_score']}/10  
**♻️ Carbon Offset:** {card_data['carbon_offset']}  
**🏆 Certifications:** {', '.join(card_data['certifications'])}
"""
                
                elements.append(
                    cl.Text(
                        name=card_data['title'],
                        content=card_content,
                        display="inline"
                    )
                )
    
    # Create action buttons
    actions = []
    if response.get('actions'):
        for action in response['actions']:
            if action['type'] == 'button':
                actions.append(
                    cl.Action(
                        name="quick_reply",
                        value=action['data']['value'],
                        payload={"value": action['data']['value']},
                        label=action['data']['label']
                    )
                )
    
    # Add standard actions
    actions.extend([
        cl.Action(
            name="view_history",
            value="history",
            payload={"action": "history"},
            label="📜 View History"
        ),
        cl.Action(
            name="reset",
            value="reset",
            payload={"action": "reset"},
            label="🔄 Start Over"
        )
    ])
    
    # Send response
    await cl.Message(
        content=response['text'],
        elements=elements,
        actions=actions,
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
# Action Handlers
# ============================================================================

@cl.action_callback("quick_reply")
async def on_quick_reply(action: cl.Action):
    """Handle quick reply button clicks"""
    
    # Send the action payload value as a new message
    value = action.payload.get("value", "")
    await on_message(cl.Message(content=value))





@cl.action_callback("view_history")
async def on_view_history(action: cl.Action):
    """Show conversation history"""
    
    session_id = cl.user_session.get("id")
    history = orchestrator.get_conversation_history(session_id)
    
    if not history:
        await cl.Message(
            content="No conversation history yet.",
            author="System"
        ).send()
        return
    
    # Format history
    history_text = "# 📜 Conversation History\n\n"
    for i, entry in enumerate(history[-5:], 1):  # Last 5 messages
        history_text += f"**Turn {i}:**\n"
        history_text += f"- **You:** {entry['user']}\n"
        history_text += f"- **Assistant:** {entry['assistant'][:100]}...\n\n"
    
    await cl.Message(
        content=history_text,
        author="System"
    ).send()


@cl.action_callback("reset")
async def on_reset(action: cl.Action):
    """Reset the conversation"""
    
    session_id = cl.user_session.get("id")
    
    response = await orchestrator.handle_action(
        action_name="reset",
        action_value=None,
        session_id=session_id
    )
    
    await cl.Message(
        content=response['text'],
        author="Assistant"
    ).send()


@cl.action_callback("more_info")
async def on_more_info(action: cl.Action):
    """Request more information about a recommendation"""
    
    session_id = cl.user_session.get("id")
    
    response = await orchestrator.handle_action(
        action_name="more_info",
        action_value=action.payload,
        session_id=session_id
    )
    
    await cl.Message(
        content=response['text'],
        author="Assistant"
    ).send()


# ============================================================================
# Error Handling
# ============================================================================

# Note: on_chat_error not supported in Chainlit 1.1.0
# Error handling is done inline in message handlers
# @cl.on_chat_error
# async def on_error(error: Exception):
#     """Handle errors gracefully"""
#     
#     await cl.Message(
#         content=f"⚠️ An unexpected error occurred: {str(error)}\n\nPlease refresh and try again.",
#         author="System"
#     ).send()


# ============================================================================
# Optional: Streaming Support (for future enhancement)
# ============================================================================

# @cl.on_message
# async def on_message_stream(message: cl.Message):
#     """Handle messages with streaming response"""
#     
#     session_id = cl.user_session.get("id")
#     
#     msg = cl.Message(content="", author="Assistant")
#     await msg.send()
#     
#     async for chunk in orchestrator.stream_response(message.content, session_id):
#         await msg.stream_token(chunk)
#     
#     await msg.update()


# ============================================================================
# Settings
# ============================================================================

# Note: password_auth_callback may not be supported in this version
# Uncomment if needed and supported
# @cl.password_auth_callback
# async def auth_callback(username: str, password: str) -> Optional[cl.User]:
#     """
#     Optional: Add authentication
#     Remove or modify this based on your needs
#     """
#     
#     # For demo purposes, accept any username/password
#     # In production, validate against a real user database
#     if username and password:
#         return cl.User(identifier=username, metadata={"role": "user"})
#     
#     return None


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # This will be run by: chainlit run app.py
    pass
