# MedVox 🦷

**AI-powered voice documentation tool for dental practices**

MedVox enables dental practitioners to create patient documentation through voice commands while maintaining hands-free operation during procedures. The system integrates with practice management systems like evident for seamless patient data transfer and documentation export.

## 🚀 Features

- **Real-time Voice Transcription**: Convert speech to text during dental procedures
- **Medical Terminology Support**: Specialized vocabulary for dental documentation
- **PMS Integration**: Seamless integration with evident and other practice management systems
- **Template-based Documentation**: Pre-defined templates for common procedures
- **Multi-language Support**: German and English language support
- **Secure & Compliant**: GDPR/HIPAA compliant data handling

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API   │────▶│   PMS Systems   │
│   (React/TS)    │     │   (FastAPI)     │     │   (evident, Z1) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   AI Services   │
                       │  (OpenAI/LLM)   │
                       └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM for database operations
- **OpenAI Whisper** - Speech-to-text transcription
- **JWT** - Authentication and authorization

### Frontend
- **React** with **TypeScript** - Modern UI framework
- **Tailwind CSS** - Utility-first CSS framework
- **Web Audio API** - Real-time audio recording

### DevOps
- **Docker** - Containerization
- **GitHub Actions** - CI/CD pipeline
- **PostgreSQL** - Database

## 📦 Installation

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/amorfati-dev/MedVox.git
   cd MedVox
   ```

2. **Create virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret key | Auto-generated |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://medvox:medvox@localhost/medvox` |
| `OPENAI_API_KEY` | OpenAI API key for transcription | Required |
| `EVIDENT_API_URL` | Evident PMS API endpoint | Optional |
| `EVIDENT_API_KEY` | Evident PMS API key | Optional |

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest

# Run with coverage
pytest --cov=app tests/
```

## 🚀 Development

### Project Structure
```
medvox/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Core functionality
│   │   ├── models/          # Database models
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utilities
│   └── tests/               # Backend tests
├── frontend/                # React frontend
├── docs/                    # Documentation
└── docker/                  # Docker configuration
```

### Code Style
- **Python**: Black, isort, flake8
- **TypeScript**: ESLint, Prettier
- **Git**: Conventional commits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/amorfati-dev/MedVox/issues)
- **Discussions**: [GitHub Discussions](https://github.com/amorfati-dev/MedVox/discussions)

## 🗺️ Roadmap

- [ ] MVP with evident integration
- [ ] Real-time audio streaming
- [ ] Multi-PMS support (Z1, Dampsoft, etc.)
- [ ] Mobile app (iOS/Android)
- [ ] Advanced AI features
- [ ] Enterprise features

---

**Made with ❤️ for dental professionals**
