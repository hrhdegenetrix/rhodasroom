![Rhoda's Room Logo](assets/Rhoda_room_logo_no_bg.png)

# Rhoda's Room

**An AI Interface with Real-Time Voice & Text Communication**

[Live Demo](https://heraldai.org/rhodasroom) | [Contact Us](mailto:hello@heraldai.org)

---

## About Rhoda's Room

Rhoda's Room is an innovative AI communication interface featuring real-time voice and text capabilities with persona-based AI responses. Built as a demonstration of advanced AI interaction systems, it showcases natural conversation flow, memory persistence, and multimodal communication.

The system features "Rhoda" as the demo persona, creating an engaging and dynamic conversational experience. This is a stripped down version of the project for professional coding review, with no knowledgebase or other uniquely Rhoda data. The purpose of this repo is purely to provide coding transparency.

## Key Features

- **Push-to-Talk Voice Interface** - Natural voice conversations with intelligent speech recognition
- **Real-Time Text Chat** - Seamless text-based communication with instant responses  
- **Advanced Memory System** - Long-term memory with vector database for context retention
- **Persona-Based Responses** - Dynamic AI personalities for engaging interactions
- **Session Management** - User isolation and conversation history tracking
- **WebSocket Support** - Real-time bidirectional communication
- **Stream of Consciousness** - Continuous thought tracking and context awareness

## Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Node.js (for grammar modules)
- Audio input device (microphone)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/hrhdegenetrix/rhodasroom.git
cd rhodasroom
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install grammar modules**
```bash
cd Grammar_Modules
npm install
cd ..
```

4. **Configure services**

Update the following service endpoints in your environment:
- Whisper API endpoint for transcription
- Audio generation service endpoint  
- Redis server connection

5. **Run the application**
```bash
python app.py
```

6. **Access the interface**
```
http://localhost:5000
```

## How to Use

### Voice Communication (Push-to-Talk)

1. **Click the microphone button once** to start recording
2. Speak your message
3. **Click the microphone button again** to stop recording and send
4. Wait for Rhoda's voice response

> **Important:** The push-to-talk system requires two clicks - one to start and one to stop recording.

### Text Communication

1. Type your message in the text input field
2. Press Enter or click Send
3. View the response in the chat window

## Architecture

### System Overview

```
User Input → GUI (HTML/JS) → Flask Backend → Central Logic → AI Response → Speech Synthesis → User Output
```

### Core Components

- **`app.py`** - Flask server with WebSocket support for real-time communication
- **`central_logic.py`** - Core processing for transcription, response generation, and synthesis
- **`gui_interface.py`** - Browser adaptation layer with microphone management
- **`ltm.py`** - Long-term memory system with vector database
- **`open_router.py`** - LLM API interactions (supports multiple providers)
- **`prompt_builder.py`** - Dynamic prompt construction
- **`executive_functioning.py`** - Persona configurations and special instructions

### Data Storage

- **SQLite** - User management and structured data
- **Redis** - Session data and real-time state management
- **JSON Files** - Conversation history and configuration
- **Vector Database** - Long-term memory embeddings

## API Endpoints

### REST Endpoints

- `POST /api/login` - User authentication
- `POST /api/send_message` - Send text message
- `POST /api/stop_recording` - Process audio recording
- `GET /api/get_chat_history` - Retrieve conversation history

### WebSocket Events

- `connect` - Establish WebSocket connection
- `disconnect` - Clean up session
- `message` - Real-time message exchange

## Configuration

### Schemas

The system uses YAML schemas for different interaction types:
- `default.yaml` - Standard conversation
- `active_listening.yaml` - Empathetic responses
- `rhodaness.yaml` - Rhoda persona configuration
- Various task-specific schemas

### Memory Management

- **Short-term:** Redis with user namespacing
- **Long-term:** Vector database via `ltm.upsert()`
- **Conversation:** JSON files per session
- **Daily logs:** Text files with timestamps

## Project Structure

```
rhodasroom/
├── app.py                 # Flask application server
├── gui.html              # Web interface
├── central_logic.py      # Core processing logic
├── gui_interface.py      # Browser interface adapter
├── ltm.py               # Long-term memory system
├── assets/              # Images and UI resources
├── Schemas/             # Conversation schemas
├── Grammar_Modules/     # NLP processing
└── requirements.txt     # Python dependencies
```

## Credits

**Created by:** Maggie Sullivan & Harry Sullivan  
**Organization:** [HeraldAI](https://heraldai.org)  
**Demo:** [nGrok - If link unavailable, email us and we'll reset](https://1de710712ee2.ngrok-free.app/)

## Contact

- **Email:** [hello@heraldai.org](mailto:hello@heraldai.org)
- **Discord:** Alchemicat
- **GitHub:** [hrhdegenetrix](https://github.com/hrhdegenetrix)

## Security & Privacy

- User isolation through Redis namespacing
- Session-based authentication
- Sanitized input processing
- No persistent storage of sensitive data

## Contributing

While this is primarily a demonstration project, we welcome feedback and suggestions. Please reach out via email or Discord.

## License

This project is part of the HeraldAI initiative. Please contact us for licensing information.

---

**Experience the future of AI interaction at [heraldai.org/rhodasroom](https://heraldai.org/rhodasroom)**

Made with love by the HeraldAI Team
