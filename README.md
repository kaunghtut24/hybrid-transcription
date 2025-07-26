# AI Meeting Notes - Real-time Transcription & AI Analysis

A powerful web application that provides real-time meeting transcription using AssemblyAI and intelligent meeting insights powered by Google Gemini AI.

## 🚀 Features

- **Real-time Audio Transcription** - Live speech-to-text using AssemblyAI Streaming v3 API
- **AI-Powered Meeting Insights** - Intelligent analysis and summaries via Google Gemini
- **Cross-Browser Support** - Works on Chrome, Edge, Safari (Firefox with limitations)
- **WebSocket Streaming** - Low-latency audio processing and transcription
- **Secure Session Management** - JWT-based authentication
- **Responsive Design** - Works on desktop and mobile devices

## 🛠️ Technology Stack

- **Backend**: Python Flask with SocketIO
- **Frontend**: Vanilla JavaScript with Web Audio API
- **AI Services**: AssemblyAI (transcription) + Google Gemini (analysis)
- **Real-time Communication**: WebSockets
- **Audio Processing**: AudioWorkletProcessor with custom buffering

## 📋 Prerequisites

- Python 3.11+
- AssemblyAI API key ([Get one here](https://www.assemblyai.com/app/account))
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kaunghtut24/Ai-meetingnotes.git
   cd Ai-meetingnotes
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

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   ```
   http://localhost:5000
   ```

## ⚙️ Configuration

Edit the `.env` file with your API keys:

```env
# Required API Keys
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Flask Configuration
SECRET_KEY=your_secret_key_here
FLASK_ENV=development
PORT=5000
```

## 🎯 Usage

1. **Start Recording** - Click the microphone button to begin transcription
2. **Real-time Transcription** - See live speech-to-text as you speak
3. **AI Analysis** - Get intelligent meeting insights and summaries
4. **Export Results** - Save transcripts and AI analysis

## 🌐 Browser Compatibility

| Browser | Audio Recording | Real-time Transcription | AI Analysis |
|---------|----------------|------------------------|-------------|
| Chrome  | ✅ Full Support | ✅ AssemblyAI + Web Speech | ✅ |
| Edge    | ✅ Full Support | ✅ AssemblyAI + Web Speech | ✅ |
| Safari  | ✅ Full Support | ✅ AssemblyAI + Web Speech | ✅ |
| Firefox | ⚠️ Limited     | ✅ AssemblyAI Only      | ✅ |

## 🔧 Technical Details

### Audio Processing Pipeline
- **Sample Rate**: Dynamic (48kHz → 16kHz resampling)
- **Buffer Size**: 100ms chunks (meets AssemblyAI 50-1000ms requirement)
- **Format**: PCM 16-bit, Base64 encoded for WebSocket transmission

### API Integration
- **AssemblyAI**: Streaming v3 WebSocket API for real-time transcription
- **Gemini**: REST API for AI analysis and insights
- **Authentication**: JWT tokens for secure session management

## 🚀 Deployment

The application is deployment-ready with:

- ✅ Production-ready Flask configuration
- ✅ Environment variable management
- ✅ Comprehensive error handling
- ✅ Security best practices
- ✅ Docker support (see `Dockerfile`)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for better meeting experiences**
