# 🦷 MedVox Frontend - iPad Voice Documentation

**Professional voice documentation for dental practices with real-time audio recording and AI processing.**

## ✨ Features

- 🎤 **Real-time audio recording** with visual feedback
- 🧠 **German dental speech recognition** (OpenAI Whisper)
- 💰 **Automatic BEMA/GOZ billing code generation**
- 📱 **iPad-optimized touch interface** for dental practice use
- 🔊 **Voice commands** for hands-free operation
- 📋 **Structured documentation** with editable results
- 💾 **Save & export** functionality
- 🌐 **Progressive Web App** - installable like a native app
- ⚡ **Offline capability** with smart caching

## 🚀 Quick Start

### 1. Start the Backend API
```bash
# In the backend directory
cd ../backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend Server
```bash
# In the frontend directory
python serve.py
```

### 3. Open in Browser
- **Local**: https://localhost:3000
- **iPad**: https://YOUR_COMPUTER_IP:3000

> ⚠️ **Important**: Use HTTPS for microphone access to work properly!

## 📱 iPad Setup

### Installation as PWA
1. Open Safari on iPad
2. Navigate to your MedVox URL
3. Tap the Share button
4. Select "Add to Home Screen"
5. MedVox will appear as a native app icon

### Microphone Permissions
1. When prompted, allow microphone access
2. For voice commands, also allow speech recognition
3. Keep iPad in landscape mode for best experience

## 🎯 How to Use

### Basic Workflow
1. **Enter Patient Info**: Patient ID and dentist name
2. **Record**: Tap the large blue microphone button
3. **Speak**: Describe the dental treatment in German
4. **Process**: Audio is automatically transcribed and analyzed
5. **Review**: Check the generated documentation and billing codes
6. **Save/Export**: Save locally or export for integration

### Voice Commands (German)
- *"Aufnahme starten"* or *"MedVox start"* - Start recording
- *"Aufnahme stoppen"* or *"MedVox stopp"* - Stop recording
- *"Pause"* - Pause/resume recording

### Keyboard Shortcuts
- **Spacebar**: Toggle recording
- **Escape**: Stop recording

## 🔧 Technical Setup

### Prerequisites
```bash
# Install required Python packages
pip install cryptography  # For HTTPS certificate generation
```

### Backend Configuration
Make sure your FastAPI backend is running with:
- OpenAI API key configured in `.env`
- CORS enabled for frontend domain
- All audio processing endpoints active

### Frontend Configuration
The app automatically connects to `http://localhost:8000` by default. To change:
1. Click the settings gear icon ⚙️
2. Update "API Endpunkt" field
3. Settings are saved automatically

## 🎵 Audio Requirements

### Supported Formats
- **Recording**: WebM with Opus codec (preferred)
- **Upload**: WAV, MP3, M4A, FLAC
- **Max Duration**: 5 minutes per recording
- **Max File Size**: 25MB

### Audio Quality Tips
- Use iPad's built-in microphone or external mic
- Record in quiet environment when possible
- Speak clearly and at normal pace
- German dental terminology is automatically recognized

## 📋 Example German Phrases

### Fillings
```
"Zahn sechsunddreißig okklusal Karies profunda, 
Lokalanästhesie mit Artikain, Exkavation, 
Kompositfüllung Klasse zwei gelegt"
```

### Extractions
```
"Zahn acht und zwanzig Extraktion wegen Wurzelfraktur, 
Infiltrationsanästhesie, Naht gesetzt"
```

### Root Canal
```
"Zahn eins vier Wurzelkanalbehandlung erste Sitzung,
Leitungsanästhesie, Aufbereitung mit Handinstrumenten"
```

## 🛠 Troubleshooting

### Microphone Not Working
- ✅ Ensure you're using HTTPS (not HTTP)
- ✅ Check browser permissions for microphone
- ✅ Try refreshing the page
- ✅ Test on Safari (recommended for iPad)

### API Connection Issues
- ✅ Verify backend server is running on port 8000
- ✅ Check network connectivity
- ✅ Update API endpoint in settings if needed
- ✅ Look for CORS errors in browser console

### Audio Processing Errors
- ✅ Ensure OpenAI API key is configured in backend
- ✅ Check internet connection for API calls
- ✅ Try shorter recordings (under 2 minutes)
- ✅ Verify audio file isn't corrupted

### Performance Issues
- ✅ Close other apps on iPad to free memory
- ✅ Use Wi-Fi instead of cellular when possible
- ✅ Clear browser cache if app feels slow
- ✅ Restart iPad if problems persist

## 🔒 Security & Privacy

### Data Protection
- Audio is processed securely through OpenAI API
- No recordings are permanently stored on servers
- Local storage used only for app settings
- HTTPS encryption for all communications

### GDPR Compliance
- Patient data stays within your practice network
- Audio transcriptions are processed but not retained
- Export/save functions are under your control
- Clear data handling policies implemented

## 🎨 Customization

### Themes & Branding
The interface uses CSS custom properties for easy theming:
```css
:root {
  --primary-color: #2563eb;    /* Change main blue color */
  --success-color: #059669;    /* Change success green */
  --background: #f8fafc;       /* Change background */
}
```

### API Integration
The frontend is designed to work with any compatible backend API. 
Key endpoints expected:
- `POST /api/v1/documentation/process-audio`
- `POST /api/v1/documentation/process-text`
- `GET /api/v1/documentation/supported-formats`

## 📊 Development

### File Structure
```
frontend/
├── index.html          # Main app interface
├── styles.css         # iPad-optimized styling
├── app.js            # Core JavaScript functionality
├── manifest.json     # PWA configuration
├── sw.js            # Service worker for offline use
├── serve.py         # HTTPS development server
└── README.md        # This file
```

### Building for Production
1. Minify CSS and JavaScript files
2. Optimize images and icons
3. Configure proper HTTPS certificates
4. Set up proper domain and SSL
5. Test thoroughly on actual iPad devices

## 🆘 Support

### Documentation
- [FastAPI Backend Docs](../backend/README.md)
- [API Documentation](http://localhost:8000/docs)
- [Technical Architecture](../docs/technical_architecture.md)

### Common Issues
- **Safari blocking microphone**: Check iOS settings > Safari > Camera & Microphone
- **PWA not installing**: Ensure HTTPS and valid manifest.json
- **Voice commands not working**: Enable Safari speech recognition
- **Slow processing**: Check network connection and API key configuration

## 🚀 Production Deployment

### Recommended Setup
1. **Web Server**: Nginx with proper SSL certificates
2. **Domain**: Use your practice domain (e.g., medvox.praxis-example.de)
3. **Network**: Deploy on practice internal network for security
4. **Backup**: Regular backups of saved documentations
5. **Updates**: Plan for regular app updates and maintenance

### iPad Fleet Management
- Use iPad MDM for enterprise deployment
- Configure WiFi profiles for automatic connection
- Set up bookmark or PWA auto-installation
- Train staff on basic troubleshooting

---

**Happy documenting! 🦷✨**

For questions or support, check the main MedVox documentation or contact your system administrator. 