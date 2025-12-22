"""
Test Firestore Connection
Verifies that Firestore is properly configured and accessible
"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def test_firestore_connection():
    """Test Firestore connection and basic operations"""
    print("Testing Firestore Connection...")
    print("="*60)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    project_id = os.getenv('FIREBASE_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not project_id:
        print("❌ FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT not set in .env")
        return False
    
    if not credentials_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set in .env")
        return False
    
    print(f"✅ Project ID: {project_id}")
    print(f"✅ Credentials: {credentials_path}")
    
    # Test database imports
    print("\n2. Testing database imports...")
    try:
        from database.config import get_session_store, get_conversation_store
        print("✅ Database modules imported successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test session store
    print("\n3. Testing session store...")
    try:
        session_store = get_session_store()
        print(f"✅ Session store created: {type(session_store).__name__}")
        
        # Create test session
        test_session_id = f"test-{datetime.now().timestamp()}"
        test_data = {
            'user_type': 'test_user',
            'conversation_history': [],
            'metadata': {'test': True}
        }
        
        created = await session_store.create_session(test_session_id, test_data)
        print(f"✅ Created test session: {created.get('id', test_session_id)[:20]}...")
        
        # Retrieve it
        retrieved = await session_store.get_session(test_session_id)
        if retrieved:
            print(f"✅ Retrieved test session successfully")
        
        # Clean up
        await session_store.delete_session(test_session_id)
        print(f"✅ Deleted test session")
        
    except Exception as e:
        print(f"❌ Session store error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test conversation store
    print("\n4. Testing conversation store...")
    try:
        conversation_store = get_conversation_store()
        print(f"✅ Conversation store created: {type(conversation_store).__name__}")
        
        # Create test conversation
        test_conv_id = f"test-conv-{datetime.now().timestamp()}"
        test_conv = {
            'user_type': 'test_user',
            'user_type_confidence': 0.9,
            'conversation_history': [
                {
                    'role': 'user',
                    'content': 'Test message',
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {}
                }
            ],
            'metadata': {},
            'preferences': {}
        }
        
        created_conv = await conversation_store.create_conversation(test_conv_id, test_conv)
        print(f"✅ Created test conversation: {created_conv.get('session_id', test_conv_id)[:20]}...")
        
        # Retrieve it
        retrieved_conv = await conversation_store.get_conversation(test_conv_id)
        if retrieved_conv:
            print(f"✅ Retrieved test conversation successfully")
            print(f"   Messages: {len(retrieved_conv.get('conversation_history', []))}")
        
        # Clean up
        await conversation_store.delete_conversation(test_conv_id)
        print(f"✅ Deleted test conversation")
        
    except Exception as e:
        print(f"❌ Conversation store error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test orchestrator
    print("\n5. Testing orchestrator integration...")
    try:
        from middleware.orchestrator import ConversationOrchestrator
        orchestrator = ConversationOrchestrator()
        print(f"✅ Orchestrator created successfully")
        print(f"   Session store: {type(orchestrator.session_manager.store).__name__}")
        print(f"   Conversation store: {type(orchestrator.conversation_store).__name__}")
    except Exception as e:
        print(f"❌ Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\n🎉 Firestore is properly configured and working!")
    print("   All conversations will be automatically saved to Firestore.")
    print("\nYou can now start the Chainlit server:")
    print("   chainlit run app.py -w")
    print("="*60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_firestore_connection())
    exit(0 if success else 1)
