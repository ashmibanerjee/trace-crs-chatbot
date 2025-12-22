# 🌍 Sustainable Tourism CRS Chatbot

A modular Conversational Recommender System (CRS) for sustainable tourism, built with Chainlit and Firebase Firestore, featuring automatic conversation storage for model training.

## 📋 Overview

This project implements a three-layer architecture for a tourism chatbot with Firestore backend:

```
┌─────────────────────────────────────┐
│  Frontend (Chainlit UI)             │  ← User interaction layer
│  - Chat interface                   │
│  - Rich messages & actions          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Orchestrator (Middleware)          │  ← Business logic layer
│  - Session management               │
│  - Automatic conversation saving    │
│  - Response formatting              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Backend (Agent System)             │  ← AI agent layer
│  - Coordinator Agent                │
│  - Clarification Agent              │
│  - Intent Agent                     │
│  - Recommendation Agent             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Firestore Database                 │  ← Data persistence layer
│  - Sessions (active chats)          │
│  - Conversations (training data)    │
└─────────────────────────────────────┘
```

## ✨ Features

- **🎯 Modular Architecture**: Clean separation between UI, orchestration, and AI logic
- **🔥 Firestore Backend**: All data stored in Firebase Firestore (no local storage)
- **💬 Chainlit Frontend**: Rich chat interface with cards, buttons, and quick replies
- **🧠 Multi-Agent System**: Coordinator routes to specialized agents
- **🌱 Sustainability Focus**: Eco-friendly recommendations with carbon footprint data
- **🤖 Auto User Type Inference**: Automatically detects user behavior patterns
- **📊 Training-Ready Data**: Conversations automatically saved in JSON for training
- **🗄️ Complete CRUD Operations**: Full database operations for conversations
- **📈 Export Utilities**: Export to JSONL, Q&A, ChatML formats
- **🔍 Advanced Queries**: Filter by user type, date range, with analytics
- **💾 Automatic Saving**: Every conversation saved to Firestore automatically

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Firebase/Firestore account
- Service account credentials JSON file

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ashmibanerjee/crs-chatbot.git
   cd crs-chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Firebase credentials**
   - Download your Firebase service account JSON file
   - Place it in the project root (e.g., `crs-chatbot-application-secret.json`)
   - Update `.env` file with your Firebase details:
   ```env
   FIREBASE_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=crs-chatbot-application-secret.json
   ```

### Running the Application

**Start the Chainlit server:**
```bash
source venv/bin/activate
chainlit run app.py -w
```

**Production mode:**
```bash
chainlit run app.py
```

The chatbot will be available at `http://localhost:8000`

**All conversations are automatically saved to Firestore!**

## 🧪 Testing

Verify your Firestore connection:
```bash
python test_firestore.py
```

This will test:
- Environment variables
- Session store operations
- Conversation store operations
- Orchestrator integration

## 📁 Project Structure

```
crs-chatbot/
├── app.py                      # Entry point
├── config.py                   # Configuration with .env loading
├── frontend/
│   └── app.py                  # Chainlit UI
├── middleware/
│   └── orchestrator.py         # Business logic & auto-save
├── backend/
│   └── agents.py               # AI agents
├── database/                   # Firestore-only storage
│   ├── session_store.py        # Session storage interface
│   ├── firestore_store.py      # Firestore session implementation
│   ├── conversation_store.py   # Conversation CRUD operations
│   └── config.py               # Database factory (Firestore from .env)
├── utils/
│   └── training_data_export.py # Export utilities
├── .env                        # Firebase credentials
└── requirements.txt            # Dependencies
```

## 📁 Project Structure

```
crs-chatbot/
├── app.py                      # Entry point (imports frontend)
├── config.py                   # Configuration management
├── frontend/
│   ├── __init__.py
│   └── app.py                  # Chainlit frontend application
├── middleware/
│   ├── __init__.py
│   └── orchestrator.py         # Middleware orchestrator with auto-save
├── backend/
│   ├── __init__.py
│   └── agents.py               # Minimal backend agents
├── database/                   # Database abstraction layer
│   ├── __init__.py
│   ├── session_store.py        # Active session storage (abstract + in-memory)
│   ├── firestore_store.py      # Firestore session implementation
│   ├── conversation_store.py   # Training data storage with CRUD ops
│   └── config.py               # Backend factory
├── utils/                      # Utility functions
│   ├── __init__.py
│   └── training_data_export.py # Export conversation data
├── tests/
│   ├── __init__.py
│   ├── test_backend.py
│   └── test_orchestrator.py
├── demo_database.py            # Database demo script
├── demo_training_data.py       # Training data demo script
├── requirements.txt            # Python dependencies
├── .chainlit/                  # Chainlit configuration directory
├── .env.example                # Example environment variables
├── .gitignore
├── package.json                # Project metadata & scripts
└── README.md
```

## 🔧 Architecture Details

### Frontend Layer (`app.py`)

The Chainlit UI provides:
- **Chat profiles**: User can select their travel style
- **Rich messages**: Cards for recommendations with sustainability scores
- **Action buttons**: Quick replies and interaction buttons
- **Session management**: User session tracking
- **Error handling**: Graceful error display

### Orchestrator Layer (`orchestrator.py`)

The middleware handles:
- **Session management**: Create, retrieve, and update user sessions (using pluggable database)
- **Request transformation**: Convert UI messages to backend format
- **Response formatting**: Transform agent responses to UI elements
- **Action routing**: Handle button clicks and user actions
- **History tracking**: Maintain conversation history in training-ready format

### Database Layer (`database/`)

Two-tier storage architecture:

**1. Session Store** (Active sessions):
- **In-Memory Store**: Fast local storage for development
- **Firestore Store**: Production-ready persistent storage with auto-scaling
- **Easy to extend**: Add Redis, PostgreSQL, or any other backend
- **Environment-based switching**: Change backends with one environment variable

**2. Conversation Store** (Training data):
- **CRUD Operations**: Create, Read, Update, Delete conversations
- **JSON Storage**: All conversations stored in structured JSON format
- **Advanced Queries**: Filter by user type, date range, with pagination
- **Export Utilities**: Multiple formats (JSONL, Q&A, ChatML) for training
- **Statistics & Analytics**: Built-in conversation analysis
- **Automatic Saving**: Orchestrator auto-saves all conversations

Key class: `ConversationOrchestrator`
```python
response = await orchestrator.process_message(
    message="Show me eco-friendly hotels",
    session_id="user-123"
)

# Export training data
training_data = await orchestrator.export_conversations_for_training(
    output_format='jsonl',
    filters={'user_type': 'sustainability_focused'}
)
```

### Backend Layer (`backend/agents.py`)

The agent system includes:
- **CoordinatorAgent**: Routes queries to appropriate agents
- **ClarificationAgent**: Asks questions to gather missing info
- **IntentAgent**: Classifies user intent (FIND_DESTINATION, GET_INFO, etc.)
- **RecommendationAgent**: Generates sustainability-focused recommendations

All agents inherit from `BaseAgent` and implement:
```python
async def process(self, message: str, context: Dict) -> AgentResponse
```

## 🔄 Replacing the Backend

The backend is designed to be **easily replaceable**. To integrate Google's ADK or another framework:

### Option 1: Replace MinimalBackend

```python
# backend/adk_backend.py
from google.adk import Agent, Runner
from backend import AgentResponse

class ADKBackend:
    def __init__(self):
        self.coordinator = Agent(
            model="gemini-2.0-flash-exp",
            name="coordinator",
            # ... ADK configuration
        )
        self.runner = Runner()
    
    async def process_message(
        self,
        message: str,
        session_state: Dict[str, Any]
    ) -> AgentResponse:
        # ADK implementation
        result = await self.runner.run(
            agent=self.coordinator,
            user_message=message
        )
        
        # Convert to AgentResponse format
        return AgentResponse(
            text=result.messages[-1].content,
            agent_name="adk_coordinator",
            action="PROCESS"
        )
```

Then update `middleware/orchestrator.py`:
```python
# from backend import MinimalBackend
from backend.adk_backend import ADKBackend

class ConversationOrchestrator:
    def __init__(self):
        # self.backend = MinimalBackend()
        self.backend = ADKBackend()  # ← Swap here
        self.session_manager = SessionManager()
```

### Option 2: Extend BaseAgent

Keep the modular structure but replace individual agents:
```python
from backend import BaseAgent
from google.adk import Agent

class ADKRecommendationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="adk_recommendation",
            description="ADK-powered recommendations"
        )
        self.agent = Agent(...)  # ADK agent
    
    async def process(self, message: str, context: Dict) -> AgentResponse:
        # Use ADK agent
        result = await self.agent.run(message)
        return AgentResponse(...)
```

## 🧪 Testing

Run the test suite:
```bash
# All tests
pytest

# With coverage
pytest --cov=backend --cov=orchestrator

# Specific test file
pytest tests/test_backend.py

# Verbose output
pytest -v
```

## 🎨 Customization

### Adding New Agents

1. Create agent class in `backend/agents.py`:
```python
class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="new_agent", description="...")
    
    async def process(self, message: str, context: Dict) -> AgentResponse:
        # Implementation
        return AgentResponse(...)
```

2. Register in `CoordinatorAgent`:
```python
self.new_agent = NewAgent()
```

3. Add routing logic in `CoordinatorAgent.process()`

### Customizing UI

Edit `app.py` to modify:
- Chat profiles (`@cl.set_chat_profiles`)
- Welcome message (`on_chat_start`)
- Message display (`on_message`)
- Action handlers (`@cl.action_callback`)

### Configuration

Edit `.env` or `config.py` to change:
- Session timeout
- Conversation history length
- Debug mode
- Model settings (for future ADK integration)

## 🌟 Features to Add

The current implementation is minimal but extensible. Consider adding:

- [ ] **Real database integration** (replace mock data in `RecommendationAgent`)
- [ ] **Vector search** with Vertex AI Vector Search for RAG
- [ ] **User authentication** (Chainlit supports various auth methods)
- [ ] **Streaming responses** (uncomment streaming code in `app.py`)
- [ ] **File uploads** (images, PDFs for itinerary planning)
- [ ] **Multi-language support**
- [ ] **Analytics dashboard** (track user preferences, popular destinations)
- [ ] **Booking integration** (connect to travel APIs)
- [ ] **Carbon calculator** (detailed trip carbon footprint)
- [ ] **Memory bank** (cross-session user profiles with Agent Engine)

## 📚 Dependencies

Core dependencies:
- `chainlit` - Frontend chat interface
- `fastapi` - Web framework (used by Chainlit)
- `pydantic` - Data validation and settings
- `pytest` - Testing framework

See `requirements.txt` for full list.

## 🔐 Environment Variables

```bash
# Application
APP_NAME="Sustainable Tourism CRS"
DEBUG=true

# Database Backend
DATABASE_BACKEND=in_memory  # or 'firestore' for production

# Google Cloud (for Firestore and ADK)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# Model Settings
DEFAULT_MODEL=gemini-2.0-flash-exp

# Session Management
SESSION_TIMEOUT=3600
MAX_CONVERSATION_HISTORY=50
```

## 📚 Documentation

- **[Session Store](DATABASE_README.md)**: Active session management with pluggable backends
- **[Conversation Store](CONVERSATION_STORE_README.md)**: CRUD operations for training data collection
- **[Training Data Export](TRAINING_DATA_README.md)**: Export formats and utilities for model training

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional agent types (booking, itinerary planning)
- Better entity extraction
- Integration with real tourism APIs
- UI enhancements
- Performance optimization
- Additional database backends (Redis, PostgreSQL)

## 📄 License

MIT License - see LICENSE file for details.

## 👤 Author

**Ashmi Banerjee**
- GitHub: [@ashmibanerjee](https://github.com/ashmibanerjee)

## 🙏 Acknowledgments

- Built with [Chainlit](https://chainlit.io/)
- Designed for integration with [Google ADK](https://github.com/google/adk)
- Inspired by conversational recommender system research

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the [Chainlit documentation](https://docs.chainlit.io/)
- Review [ADK documentation](https://google.github.io/adk-docs/)

---

**Happy Sustainable Traveling! 🌍✈️🌱**