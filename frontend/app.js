/**
 * MedVox - iPad-Optimized Voice Documentation App
 * Real-time audio recording and dental documentation
 */

class MedVoxApp {
    constructor() {
        this.isRecording = false;
        this.isPaused = false;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.audioChunks = [];
        this.recordingStartTime = null;
        this.recordingTimer = null;
        this.audioContext = null;
        this.analyser = null;
        this.animationId = null;
        
        // Configuration with enhanced settings
        this.config = {
            // General
            apiEndpoint: localStorage.getItem('apiEndpoint') || 'http://localhost:8000',
            language: localStorage.getItem('language') || 'de',
            autoStart: localStorage.getItem('autoStart') === 'true',
            voiceCommands: localStorage.getItem('voiceCommands') === 'true',
            autoSave: localStorage.getItem('autoSave') === 'true',
            theme: localStorage.getItem('theme') || 'auto',
            
            // Audio
            selectedMicrophone: localStorage.getItem('selectedMicrophone') || 'default',
            audioQuality: localStorage.getItem('audioQuality') || 'high',
            noiseReduction: localStorage.getItem('noiseReduction') === 'true',
            autoGain: localStorage.getItem('autoGain') === 'true',
            whisperModel: localStorage.getItem('whisperModel') || 'whisper-1',
            
            // Practice
            practiceName: localStorage.getItem('practiceName') || '',
            defaultDentist: localStorage.getItem('defaultDentist') || 'Dr. Martin',
            patientIdFormat: localStorage.getItem('patientIdFormat') || 'free',
            requirePatientConsent: localStorage.getItem('requirePatientConsent') === 'true',
            dataRetention: localStorage.getItem('dataRetention') || '30days',
            
            // Billing
            defaultBillingSystem: localStorage.getItem('defaultBillingSystem') || 'both',
            selectedInsuranceType: localStorage.getItem('selectedInsuranceType') || 'bema',
            gozFactor: parseFloat(localStorage.getItem('gozFactor')) || 2.3,
            showBillingWarnings: localStorage.getItem('showBillingWarnings') === 'true',
            autoBillingCodes: localStorage.getItem('autoBillingCodes') === 'true',
            billingReviewThreshold: parseInt(localStorage.getItem('billingReviewThreshold')) || 100,
            
            // Integration
            evidentUrl: localStorage.getItem('evidentUrl') || '',
            evidentApiKey: localStorage.getItem('evidentApiKey') || '',
            autoExportEvident: localStorage.getItem('autoExportEvident') === 'true',
            exportFormat: localStorage.getItem('exportFormat') || 'json',
            backupEnabled: localStorage.getItem('backupEnabled') === 'true',
            
            // System
            maxRecordingTime: 300, // 5 minutes
            visualizerEnabled: true
        };
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        this.loadSettings();
        await this.checkMicrophonePermission();
        await this.checkAPIConnection();
        this.showToast('MedVox ready! 🦷', 'success');
        
        // Add to global scope for debugging
        window.medvoxApp = this;
        window.testSettings = () => this.debugSettings();
    }
    
    setupEventListeners() {
        // Recording controls
        const recordBtn = document.getElementById('record-btn');
        const pauseBtn = document.getElementById('pause-btn');
        const stopBtn = document.getElementById('stop-btn');
        const playbackBtn = document.getElementById('playback-btn');
        
        recordBtn.addEventListener('click', () => this.toggleRecording());
        pauseBtn.addEventListener('click', () => this.pauseRecording());
        stopBtn.addEventListener('click', () => this.stopRecording());
        playbackBtn.addEventListener('click', () => this.playback());
        
        // Action buttons
        document.getElementById('save-btn').addEventListener('click', () => this.saveDocumentation());
        document.getElementById('export-btn').addEventListener('click', () => this.exportDocumentation());
        document.getElementById('new-recording-btn').addEventListener('click', () => this.newRecording());
        document.getElementById('edit-btn').addEventListener('click', () => this.editResults());
        
        // Settings
        const settingsToggle = document.getElementById('settings-toggle');
        const headerSettingsToggle = document.getElementById('header-settings-toggle');
        const closeSettings = document.getElementById('close-settings');
        
        console.log('Settings toggle button found:', !!settingsToggle);
        console.log('Header settings toggle button found:', !!headerSettingsToggle);
        console.log('Close settings button found:', !!closeSettings);
        
        if (settingsToggle) {
            settingsToggle.addEventListener('click', () => this.toggleSettings());
            console.log('Settings toggle event listener attached');
        } else {
            console.error('Settings toggle button not found!');
        }
        
        if (headerSettingsToggle) {
            headerSettingsToggle.addEventListener('click', () => this.toggleSettings());
            console.log('Header settings toggle event listener attached');
        } else {
            console.error('Header settings toggle button not found!');
        }
        
        if (closeSettings) {
            closeSettings.addEventListener('click', () => this.closeSettings());
            console.log('Close settings event listener attached');
        } else {
            console.error('Close settings button not found!');
        }
        
        // Settings tabs
        this.setupSettingsTabs();
        
        // Settings action buttons
        this.setupSettingsActions();
        
        // Enhanced settings inputs
        this.setupSettingsInputs();
        
        // Patient inputs
        document.getElementById('patient-id').addEventListener('input', () => this.validateInputs());
        document.getElementById('dentist-id').addEventListener('input', () => this.validateInputs());
        
        // Insurance type toggle
        const insuranceRadios = document.querySelectorAll('input[name="insurance"]');
        insuranceRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this.handleInsuranceTypeChange(e));
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // Voice commands
        if (this.config.voiceCommands) {
            this.setupVoiceCommands();
        }
        
        // Prevent zoom on double tap
        document.addEventListener('touchend', (e) => {
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
            }
        });
    }
    
    async checkMicrophonePermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            document.getElementById('record-btn').disabled = false;
            this.updateConnectionStatus('🟢 Mikrofon bereit');
            return true;
        } catch (error) {
            console.error('Microphone access denied:', error);
            this.showToast('Mikrofon-Zugriff erforderlich! Bitte in den Browser-Einstellungen erlauben.', 'error');
            this.updateConnectionStatus('🔴 Kein Mikrofon');
            return false;
        }
    }
    
    async checkAPIConnection() {
        try {
            const response = await fetch(`${this.config.apiEndpoint}/health`);
            if (response.ok) {
                this.updateAPIStatus('🟢 API verbunden');
                return true;
            } else {
                throw new Error('API not available');
            }
        } catch (error) {
            console.error('API connection failed:', error);
            this.updateAPIStatus('🔴 API offline');
            return false;
        }
    }
    
    updateConnectionStatus(status) {
        document.getElementById('connection-status').textContent = status;
    }
    
    updateAPIStatus(status) {
        const apiStatusElement = document.getElementById('api-status');
        if (apiStatusElement) {
            apiStatusElement.textContent = status;
            
            // Update CSS classes for visual styling
            apiStatusElement.classList.remove('online', 'offline');
            if (status.includes('🟢') || status.includes('verbunden')) {
                apiStatusElement.classList.add('online');
            } else {
                apiStatusElement.classList.add('offline');
            }
        }
    }
    
    validateInputs() {
        const patientId = document.getElementById('patient-id').value.trim();
        const dentistId = document.getElementById('dentist-id').value.trim();
        
        return patientId.length > 0 && dentistId.length > 0;
    }
    
    handleInsuranceTypeChange(event) {
        const selectedType = event.target.value;
        this.config.selectedInsuranceType = selectedType;
        localStorage.setItem('selectedInsuranceType', selectedType);
        
        // Visual feedback
        const toggleSwitch = document.getElementById('insurance-toggle');
        toggleSwitch.setAttribute('data-selected', selectedType);
        
        // Show toast notification
        const typeName = selectedType === 'bema' ? 'BEMA (Kasse)' : 'GOZ (Privat)';
        this.showToast(`Abrechnungstyp geändert zu ${typeName}`, 'info');
        
        console.log(`Insurance type changed to: ${selectedType}`);
    }
    
    getSelectedInsuranceType() {
        const checkedRadio = document.querySelector('input[name="insurance"]:checked');
        return checkedRadio ? checkedRadio.value : this.config.selectedInsuranceType;
    }
    
    async toggleRecording() {
        if (!this.validateInputs()) {
            this.showToast('Bitte Patient ID und Zahnarzt eingeben', 'warning');
            return;
        }
        
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    async startRecording() {
        try {
            // Request microphone access
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100,  // Higher quality for better transcription
                    channelCount: 1,    // Mono is sufficient for speech
                    volume: 1.0         // Full volume
                }
            });
            
            // Setup audio context for visualization
            if (this.config.visualizerEnabled) {
                this.setupAudioVisualization();
            }
            
            // Setup MediaRecorder with backend-supported formats
            let options = {};
            
            // Try formats supported by backend: wav, mp3, m4a, flac
            const supportedFormats = [
                'audio/wav',
                'audio/mpeg',  // mp3
                'audio/mp4',   // m4a
                'audio/webm;codecs=opus', // fallback
                'audio/webm'   // fallback
            ];
            
            for (const format of supportedFormats) {
                if (MediaRecorder.isTypeSupported(format)) {
                    options.mimeType = format;
                    break;
                }
            }
            
            this.mediaRecorder = new MediaRecorder(this.audioStream, options);
            this.audioChunks = [];
            this.recordingMimeType = options.mimeType || 'audio/webm'; // Store for later use
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };
            
            // Start recording
            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            
            // Update UI
            this.updateRecordingUI();
            this.startRecordingTimer();
            
            if (this.config.visualizerEnabled) {
                this.startVisualization();
            }
            
            this.showToast('Aufnahme gestartet', 'success');
            
        } catch (error) {
            console.error('Recording failed:', error);
            this.showToast('Aufnahme fehlgeschlagen: ' + error.message, 'error');
        }
    }
    
    pauseRecording() {
        if (this.mediaRecorder && this.isRecording && !this.isPaused) {
            this.mediaRecorder.pause();
            this.isPaused = true;
            this.stopRecordingTimer();
            this.showToast('Aufnahme pausiert', 'warning');
            this.updateRecordingUI();
        } else if (this.isPaused) {
            this.mediaRecorder.resume();
            this.isPaused = false;
            this.startRecordingTimer();
            this.showToast('Aufnahme fortgesetzt', 'success');
            this.updateRecordingUI();
        }
    }
    
    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.isPaused = false;
            
            // Stop audio stream
            if (this.audioStream) {
                this.audioStream.getTracks().forEach(track => track.stop());
            }
            
            // Stop visualization
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
            }
            
            this.stopRecordingTimer();
            this.updateRecordingUI();
            this.showToast('Aufnahme gestoppt', 'success');
        }
    }
    
    setupAudioVisualization() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        
        const source = this.audioContext.createMediaStreamSource(this.audioStream);
        source.connect(this.analyser);
        
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.8;
        
        const visualizer = document.getElementById('audio-visualizer');
        const canvas = document.getElementById('visualizer-canvas');
        
        visualizer.classList.remove('hidden');
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
    }
    
    startVisualization() {
        const canvas = document.getElementById('visualizer-canvas');
        const ctx = canvas.getContext('2d');
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        const draw = () => {
            if (!this.isRecording) return;
            
            this.animationId = requestAnimationFrame(draw);
            
            this.analyser.getByteFrequencyData(dataArray);
            
            ctx.fillStyle = '#f1f5f9';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            const barWidth = (canvas.width / bufferLength) * 2.5;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;
                
                const gradient = ctx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
                gradient.addColorStop(0, '#2563eb');
                gradient.addColorStop(1, '#1d4ed8');
                
                ctx.fillStyle = gradient;
                ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        };
        
        draw();
    }
    
    updateRecordingUI() {
        const recordBtn = document.getElementById('record-btn');
        const recordingStatus = document.getElementById('recording-status');
        const pauseBtn = document.getElementById('pause-btn');
        const stopBtn = document.getElementById('stop-btn');
        const playbackBtn = document.getElementById('playback-btn');
        
        if (this.isRecording) {
            recordBtn.classList.add('recording');
            recordBtn.innerHTML = '<span class="record-icon">⏹️</span><span class="record-text">Aufnahme stoppen</span>';
            recordingStatus.classList.remove('hidden');
            pauseBtn.disabled = false;
            stopBtn.disabled = false;
            playbackBtn.disabled = true;
        } else {
            recordBtn.classList.remove('recording');
            recordBtn.innerHTML = '<span class="record-icon">🎤</span><span class="record-text">Aufnahme starten</span>';
            recordingStatus.classList.add('hidden');
            pauseBtn.disabled = true;
            stopBtn.disabled = true;
            playbackBtn.disabled = this.audioChunks.length === 0;
        }
        
        if (this.isPaused) {
            pauseBtn.innerHTML = '▶️ Fortsetzen';
        } else {
            pauseBtn.innerHTML = '⏸️ Pause';
        }
    }
    
    startRecordingTimer() {
        this.recordingTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            document.getElementById('recording-time').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            // Auto-stop at max recording time
            if (elapsed >= this.config.maxRecordingTime) {
                this.stopRecording();
                this.showToast('Maximale Aufnahmedauer erreicht', 'warning');
            }
        }, 1000);
    }
    
    stopRecordingTimer() {
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
    }
    
    async processRecording() {
        this.showProcessing('Verarbeitung läuft...');
        
        try {
            // Create audio blob with correct MIME type
            const mimeType = this.recordingMimeType || 'audio/webm';
            const audioBlob = new Blob(this.audioChunks, { type: mimeType });
            
            // Get correct file extension
            const extension = this.getFileExtensionFromMimeType(mimeType);
            const filename = `recording.${extension}`;
            
            // Create FormData for API call
            const formData = new FormData();
            formData.append('audio_file', audioBlob, filename);
            formData.append('patient_id', document.getElementById('patient-id').value);
            formData.append('dentist_id', document.getElementById('dentist-id').value);
            formData.append('insurance_type', this.getSelectedInsuranceType());
            formData.append('use_mock', 'false'); // Use real OpenAI Whisper
            
            this.updateProcessingStatus('Transkription wird erstellt...');
            
            // Send to API with enhanced headers
            const response = await fetch(`${this.config.apiEndpoint}/api/v1/documentation/process-audio`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Model-Version': 'gpt-4o',
                    'X-Insurance-Type': this.getSelectedInsuranceType(),
                    'X-AI-Engine': 'openai-gpt4o'
                }
            });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }
            
            this.updateProcessingStatus('🧠 GPT-4o analysiert Behandlung...');
            
            const result = await response.json();
            
            if (result.success) {
                this.updateProcessingStatus('💰 GPT-4o erstellt BEMA/GOZ Abrechnung...');
                this.displayResults(result.documentation);
                this.showToast('🎉 Enhanced Dokumentation erstellt!', 'success');
            } else {
                throw new Error(result.error_message || 'Processing failed');
            }
            
        } catch (error) {
            console.error('Processing failed:', error);
            this.showToast('GPT-4o-Verarbeitung fehlgeschlagen: ' + error.message, 'error');
        } finally {
            this.hideProcessing();
        }
    }
    
    getFileExtensionFromMimeType(mimeType) {
        const mimeToExtension = {
            'audio/wav': 'wav',
            'audio/mpeg': 'mp3',
            'audio/mp4': 'm4a',
            'audio/webm': 'webm',
            'audio/webm;codecs=opus': 'webm'
        };
        return mimeToExtension[mimeType] || 'webm';
    }
    
    displayResults(documentation) {
        // Hide other sections (with safety checks)
        const recordingSection = document.getElementById('recording-section');
        if (recordingSection) recordingSection.style.display = 'none';
        
        const audioVisualizer = document.getElementById('audio-visualizer');
        if (audioVisualizer) audioVisualizer.classList.add('hidden');
        
        // Show results
        const resultsSection = document.getElementById('results-section');
        if (!resultsSection) {
            console.error('Results section not found in HTML!');
            this.showToast('UI Error: Results section missing', 'error');
            return;
        }
        resultsSection.classList.remove('hidden');
        
        // Transcription - handle nested structure
        const transcription = documentation.transcription || {};
        document.getElementById('transcription-text').textContent = transcription.text || documentation.transcription_text || '';
        document.getElementById('confidence-score').textContent = Math.round((transcription.confidence || 0.9) * 100);
        document.getElementById('detected-language').textContent = (transcription.language || 'DE').toUpperCase();
        
        // NEW APPROACH: Display Gemini's raw professional output directly
        this.displayGeminiOutput(documentation);
        
        // Clinical notes
        document.getElementById('clinical-notes').value = documentation.clinical_notes || documentation.notes || '';
        
        // Store documentation for export
        this.currentDocumentation = documentation;
    }
    
    displayBillingCodes(billingCodes) {
        const billingCodesContainer = document.getElementById('billing-codes');
        billingCodesContainer.innerHTML = '';
        
        const insuranceType = this.getSelectedInsuranceType();
        
        // Debug log to check data structure
        console.log('🔍 Billing codes received:', billingCodes);
        if (billingCodes.length > 0) {
            console.log('🔍 First billing code structure:', billingCodes[0]);
        }
        
        // Clean billing codes - remove any undefined fee properties that might cause toFixed errors
        const cleanedBillingCodes = billingCodes.map((code, index) => {
            try {
                console.log(`🔧 Cleaning billing code ${index}:`, code);
                const cleanCode = { ...code };
                // Remove any fee-related properties that might be undefined
                delete cleanCode.fee_euros;
                delete cleanCode.fee;
                delete cleanCode.total_fee;
                delete cleanCode.cost;
                delete cleanCode.price;
                console.log(`✅ Cleaned billing code ${index}:`, cleanCode);
                return cleanCode;
            } catch (error) {
                console.error(`❌ Error cleaning billing code ${index}:`, error, code);
                return {}; // Return empty object on error
            }
        });
        
        // Separate codes by system (backend uses 'system' field, not 'type')
        const bemaCodes = cleanedBillingCodes.filter(code => code.system === 'bema');
        const gozCodes = cleanedBillingCodes.filter(code => code.system === 'goz');
        
        // BEMA Patient Logic
        if (insuranceType === 'bema') {
            // Show BEMA Codes (Kassensachleistungen)
            if (bemaCodes.length > 0) {
                const bemaSection = this.createBillingSection('🏥 BEMA Sachleistungen (Kasse)', 'bema-section');
                bemaCodes.forEach((code, index) => {
                    try {
                        console.log(`🏥 Creating BEMA code element ${index}:`, code);
                        const codeElement = this.createBillingCodeElement(code, 'bema');
                        bemaSection.appendChild(codeElement);
                    } catch (error) {
                        console.error(`❌ Error creating BEMA code element ${index}:`, error, code);
                    }
                });
                billingCodesContainer.appendChild(bemaSection);
            }
            
            // Show GOZ Codes with MKV (Mehrkostenvereinbarung)
            if (gozCodes.length > 0) {
                const gozSection = this.createBillingSection('💰 GOZ Mehrkostenvereinbarung (MKV)', 'goz-mkv-section');
                gozCodes.forEach((code, index) => {
                    try {
                        console.log(`💰 Creating GOZ-MKV code element ${index}:`, code);
                        const codeElement = this.createBillingCodeElement(code, 'goz-mkv');
                        gozSection.appendChild(codeElement);
                    } catch (error) {
                        console.error(`❌ Error creating GOZ-MKV code element ${index}:`, error, code);
                    }
                });
                billingCodesContainer.appendChild(gozSection);
            }
            
        } else {
            // GOZ Patient Logic - Only GOZ codes
            if (gozCodes.length > 0) {
                const gozSection = this.createBillingSection('💰 GOZ Privatleistungen', 'goz-private-section');
                gozCodes.forEach((code, index) => {
                    try {
                        console.log(`💰 Creating GOZ-Private code element ${index}:`, code);
                        const codeElement = this.createBillingCodeElement(code, 'goz-private');
                        gozSection.appendChild(codeElement);
                    } catch (error) {
                        console.error(`❌ Error creating GOZ-Private code element ${index}:`, error, code);
                    }
                });
                billingCodesContainer.appendChild(gozSection);
            }
            
            // Show warning if BEMA codes are present for GOZ patient
            if (bemaCodes.length > 0) {
                const warningDiv = document.createElement('div');
                warningDiv.className = 'billing-warning';
                warningDiv.innerHTML = `
                    <span class="warning-icon">⚠️</span>
                    <span>ACHTUNG: BEMA-Codes wurden für Privatpatienten erkannt. Diese werden nicht abgerechnet.</span>
                `;
                billingCodesContainer.appendChild(warningDiv);
            }
        }
        
        // Display summary information about code counts
        this.displayCodeSummary(bemaCodes.length, gozCodes.length, insuranceType);
    }
    
    createBillingSection(title, className) {
        const section = document.createElement('div');
        section.className = `billing-section ${className}`;
        
        const header = document.createElement('h4');
        header.className = 'billing-section-header';
        header.textContent = title;
        section.appendChild(header);
        
        return section;
    }
    
    createBillingCodeElement(code, displayType) {
        const codeElement = document.createElement('div');
        codeElement.className = `billing-code billing-code-${displayType}`;
        
        // Debug log to check code structure
        console.log('🔍 Creating element for code:', code);
        
        // Safe access to all properties with fallbacks
        const safeCode = code.code || 'N/A';
        const safeDescription = code.description || 'Keine Beschreibung';
        const safeToothNumber = code.tooth_number || code.tooth || null;
        const safePoints = code.points || null;
        const safeFactor = code.factor || null;
        const safeQuantity = code.quantity || 1;
        const safeNote = code.note || '';
        
        let noteHtml = '';
        if (displayType === 'goz-mkv') {
            noteHtml = '<span class="mkv-note">MKV</span>';
        } else if (safeNote && safeNote !== '') {
            noteHtml = `<span class="code-note">${safeNote}</span>`;
        }
        
        codeElement.innerHTML = `
            <div class="code-info">
                <div class="code-number">${safeCode}</div>
                <div class="code-description">${safeDescription}</div>
                ${safeToothNumber ? `<div class="code-tooth">Zahn: ${safeToothNumber}</div>` : ''}
                ${safePoints ? `<div class="code-points">${safePoints} Punkte</div>` : ''}
                ${safeFactor ? `<div class="code-factor">Faktor: ${safeFactor}</div>` : ''}
                ${safeQuantity && safeQuantity > 1 ? `<div class="code-quantity">× ${safeQuantity}</div>` : ''}
            </div>
            <div class="code-note-container">
                ${noteHtml}
                ${safeNote && safeNote !== 'MKV' ? `<span class="code-note">${safeNote}</span>` : ''}
            </div>
        `;
        
        return codeElement;
    }
    
    displayGeminiOutput(documentation) {
        // Get the containers we need to update
        const proceduresContainer = document.getElementById('procedures-list');
        const billingCodesContainer = document.getElementById('billing-codes');
        const summaryContainer = document.getElementById('total-fee-container');
        
        // Clear old content
        proceduresContainer.innerHTML = '';
        billingCodesContainer.innerHTML = '';
        summaryContainer.innerHTML = '';
        
        console.log('🚀 Full Documentation for Gemini display:', documentation);
        console.log('📊 Documentation keys:', Object.keys(documentation));
        console.log('🔍 raw_gemini_response field:', documentation.raw_gemini_response);
        
        // Try to get the raw Gemini response if available
        const rawGeminiResponse = documentation.raw_gemini_response || documentation.llm_raw_response || documentation.gemini_response || null;
        const billingCodes = documentation.billing_codes || [];
        const procedures = documentation.procedures || [];
        
        console.log('🔍 Raw response check:', {
            hasRawResponse: !!rawGeminiResponse,
            rawLength: rawGeminiResponse ? rawGeminiResponse.length : 0,
            rawPreview: rawGeminiResponse ? rawGeminiResponse.substring(0, 200) + '...' : 'null',
            billingCodesCount: billingCodes.length
        });
        
        // PRIORITY 1: Always show Gemini's raw output if available
        if (rawGeminiResponse && rawGeminiResponse.trim()) {
            console.log('✅ Showing Gemini raw response - this is the best!');
            this.displayRawGeminiResponse(rawGeminiResponse, billingCodesContainer);
            proceduresContainer.innerHTML = '<div class="gemini-info">✅ Siehe Gemini-Ausgabe unten</div>';
        } else if (billingCodes.length > 0) {
            console.log('⚠️ No raw response available, using processed data');
            this.createProfessionalBillingTable(billingCodes, billingCodesContainer);
        } else {
            console.log('❌ No useful data available');
            this.displayProcedures(procedures, proceduresContainer);
            billingCodesContainer.innerHTML = '<div class="no-codes">Keine Abrechnungsdaten verfügbar</div>';
        }
    }
    
    displayRawGeminiResponse(rawResponse, container) {
        const responseDiv = document.createElement('div');
        responseDiv.className = 'gemini-raw-output';
        
        // Clear container and show ONLY Gemini's output
        container.innerHTML = '';
        
        try {
            // Try to parse and beautify JSON
            const geminiData = JSON.parse(rawResponse);
            console.log('🎯 Parsed Gemini JSON:', geminiData);
            
            // Create a beautiful display from Gemini's data
            responseDiv.innerHTML = `<h3>🤖 Gemini 2.5 Pro Abrechnungsvorschlag</h3>`;
            
            // Check which format Gemini used and display accordingly
            if (geminiData.billed_items) {
                // Format: Top-level billed_items
                this.displayGeminiBilledItems(geminiData, responseDiv);
            } else if (geminiData.procedures) {
                // Format: Nested procedures with billing_codes/billing_entries
                this.displayGeminiProcedures(geminiData, responseDiv);
            } else if (geminiData.prozeduren) {
                // Format: German prozeduren
                this.displayGeminiProzeduren(geminiData, responseDiv);
            } else if (geminiData.billing_entries) {
                // Format: Direct billing_entries
                this.displayGeminiBillingEntries(geminiData, responseDiv);
            } else {
                // Fallback: Show raw JSON beautifully
                responseDiv.innerHTML += `<pre class="gemini-json">${JSON.stringify(geminiData, null, 2)}</pre>`;
            }
            
        } catch (e) {
            // Not JSON - show as HTML/Text
            console.log('🔍 Gemini response is not JSON, showing as HTML');
            responseDiv.innerHTML = `
                <h3>🤖 Gemini 2.5 Pro Abrechnungsvorschlag</h3>
                <div class="gemini-content">
                    ${rawResponse}
                </div>
            `;
        }
        
        container.appendChild(responseDiv);
        console.log('🤖 Showing Gemini response');
    }
    
    displayGeminiBilledItems(data, container) {
        // Create beautiful table from billed_items
        const tableHTML = `
            <div class="billing-section">
                <h4>📋 Behandlung: ${data.treatment_summary || 'Zahnbehandlung'}</h4>
                <p>📅 Datum: ${data.treatment_date || new Date().toLocaleDateString('de-DE')}</p>
                
                <table class="billing-table">
                    <thead>
                        <tr>
                            <th>Zahn</th>
                            <th>System</th>
                            <th>Code</th>
                            <th>Leistung</th>
                            <th>Beschreibung</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.billed_items.map(item => `
                            <tr>
                                <td>${item.tooth || item.zahn || '-'}</td>
                                <td><span class="code-type ${item.code_system?.toLowerCase()}">${item.code_system || item.system || ''}</span></td>
                                <td><strong>${item.code || item.position || ''}</strong></td>
                                <td>${item.description || item.beschreibung || ''}</td>
                                <td class="description-cell">${item.official_description || ''}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML += tableHTML;
    }
    
    displayGeminiProcedures(data, container) {
        // Handle nested procedures format
        container.innerHTML += '<div class="procedures-section">';
        
        data.procedures.forEach(proc => {
            const procDiv = document.createElement('div');
            procDiv.className = 'procedure-block';
            procDiv.innerHTML = `
                <h4>🦷 ${proc.procedure_name || proc.beschreibung || 'Behandlung'} 
                    ${proc.tooth_number || proc.zahn ? `- Zahn ${proc.tooth_number || proc.zahn}` : ''}</h4>
            `;
            
            // Extract billing codes from nested structure
            const codes = proc.billing_codes || proc.billing_entries || proc.abrechnungspositionen || [];
            if (codes.length > 0) {
                procDiv.innerHTML += this.createBillingTable(codes);
            }
            
            container.appendChild(procDiv);
        });
        
        container.innerHTML += '</div>';
    }
    
    createBillingTable(codes) {
        return `
            <table class="billing-table compact">
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>System</th>
                        <th>Beschreibung</th>
                    </tr>
                </thead>
                <tbody>
                    ${codes.map(code => `
                        <tr>
                            <td><strong>${code.code || code.position || ''}</strong></td>
                            <td><span class="code-type ${(code.system || code.code_system || '').toLowerCase()}">${code.system || code.code_system || ''}</span></td>
                            <td>${code.description || code.beschreibung || ''}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
    
    displayGeminiProzeduren(data, container) {
        // Handle German "prozeduren" format
        const procedures = data.prozeduren || [];
        
        if (procedures.length === 0) {
            container.innerHTML += '<p>Keine Prozeduren gefunden.</p>';
            return;
        }
        
        // Create header section
        container.innerHTML += `
            <div class="billing-section">
                <h4>📋 Behandlung vom ${data.behandlungsdatum || new Date().toLocaleDateString('de-DE')}</h4>
                <p>🏥 Abrechnungstyp: ${data.abrechnungstyp || 'BEMA'}</p>
            </div>
        `;
        
        // Create procedures section
        const proceduresHTML = procedures.map(proc => {
            const codes = proc.abrechnungspositionen || [];
            
            return `
                <div class="procedure-block">
                    <h4>🦷 ${proc.prozedur_beschreibung || 'Behandlung'} 
                        ${proc.zahn ? `- Zahn ${proc.zahn}` : ''}</h4>
                    ${proc.flaechen && proc.flaechen.length > 0 ? 
                        `<p>Flächen: ${proc.flaechen.join(', ').toUpperCase()}</p>` : ''}
                    
                    ${codes.length > 0 ? `
                        <table class="billing-table compact">
                            <thead>
                                <tr>
                                    <th>Code</th>
                                    <th>System</th>
                                    <th>Beschreibung</th>
                                    <th>Anzahl</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${codes.map(code => `
                                    <tr>
                                        <td><strong>${code.code || ''}</strong></td>
                                        <td><span class="code-type ${(code.code_system || '').toLowerCase()}">${code.code_system || ''}</span></td>
                                        <td>${code.beschreibung || ''}</td>
                                        <td>${code.anzahl || 1}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    ` : '<p>Keine Abrechnungspositionen</p>'}
                </div>
            `;
        }).join('');
        
        container.innerHTML += proceduresHTML;
    }
    
    createProfessionalBillingTable(billingCodes, container) {
        const insuranceType = this.getSelectedInsuranceType();
        const today = new Date().toLocaleDateString('de-DE');
        
        const tableDiv = document.createElement('div');
        tableDiv.className = 'professional-billing-table';
        
        // Separate BEMA and GOZ codes
        const bemaCodes = billingCodes.filter(code => code.system === 'bema');
        const gozCodes = billingCodes.filter(code => code.system === 'goz' || code.system === 'goä');
        
        let tableHTML = '';
        
        // BEMA Table (if applicable)
        if (bemaCodes.length > 0 && insuranceType === 'bema') {
            tableHTML += `
                <div class="billing-section">
                    <h3>🏥 BEMA-Abrechnung (Kassensachleistungen)</h3>
                    <table class="billing-table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Zahn</th>
                                <th>BEMA-Nr.</th>
                                <th>Bezeichnung</th>
                                <th>Anzahl</th>
                                <th>Anmerkungen</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${bemaCodes.map(code => `
                                <tr>
                                    <td>${today}</td>
                                    <td>${code.tooth_number || code.tooth || '-'}</td>
                                    <td>${code.code || 'N/A'}</td>
                                    <td>${code.description || 'Keine Beschreibung'}</td>
                                    <td>${code.quantity || 1}</td>
                                    <td>${code.note || 'Standardbehandlung'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        // GOZ Table
        if (gozCodes.length > 0) {
            const gozTitle = insuranceType === 'bema' ? 
                '💰 GOZ-Abrechnung (Mehrkostenvereinbarung)' : 
                '💰 GOZ-Abrechnung (Privatleistungen)';
                
            tableHTML += `
                <div class="billing-section">
                    <h3>${gozTitle}</h3>
                    <table class="billing-table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Zahn</th>
                                <th>GOZ/GOÄ-Nr.</th>
                                <th>Bezeichnung</th>
                                <th>Anzahl</th>
                                <th>Anmerkungen</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${gozCodes.map(code => `
                                <tr>
                                    <td>${today}</td>
                                    <td>${code.tooth_number || code.tooth || code.zahn || '-'}</td>
                                    <td>${code.code || 'N/A'}</td>
                                    <td>${code.description || 'Keine Beschreibung'}</td>
                                    <td>${code.quantity || 1}</td>
                                    <td>${this.formatBillingNote(code, insuranceType)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        if (tableHTML === '') {
            tableHTML = '<div class="no-codes">Keine Abrechnungsdaten verfügbar</div>';
        }
        
        tableDiv.innerHTML = tableHTML;
        container.appendChild(tableDiv);
    }
    
    formatBillingNote(code, insuranceType) {
        // Start with Gemini's note if available
        let note = code.note || code.anmerkung || '';
        
        // Add quantity info if more than 1
        if (code.quantity > 1) {
            note = note ? `${note} (${code.quantity}x)` : `${code.quantity}x`;
        }
        
        // Add MKV info only if it's BEMA patient with GOZ codes AND no other note
        if (insuranceType === 'bema' && (code.system === 'goz' || code.type === 'goz') && !note) {
            note = 'MKV';
        }
        
        // Fallback only if really nothing available
        return note || '-';
    }
    
    displayProcedures(procedures, container) {
        if (procedures.length === 0) return;
        
        const proceduresDiv = document.createElement('div');
        proceduresDiv.className = 'procedures-display';
        proceduresDiv.innerHTML = `
            <h3>📋 Durchgeführte Maßnahmen</h3>
            <div class="procedures-list">
                ${procedures.map(proc => `
                    <span class="procedure-tag">${proc}</span>
                `).join('')}
            </div>
        `;
        container.appendChild(proceduresDiv);
    }
    
    displayCodeSummary(bemaCodesCount, gozCodesCount, insuranceType) {
        const summaryContainer = document.getElementById('total-fee-container');
        summaryContainer.innerHTML = '';
        
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'codes-summary';
        
        if (insuranceType === 'bema') {
            if (bemaCodesCount > 0) {
                const bemaSum = document.createElement('div');
                bemaSum.className = 'summary-line bema-summary';
                bemaSum.innerHTML = `<span>🏥 BEMA Positionen:</span> <span>${bemaCodesCount}</span>`;
                summaryDiv.appendChild(bemaSum);
            }
            
            if (gozCodesCount > 0) {
                const gozSum = document.createElement('div');
                gozSum.className = 'summary-line goz-summary';
                gozSum.innerHTML = `<span>💰 GOZ Positionen (MKV):</span> <span>${gozCodesCount}</span>`;
                summaryDiv.appendChild(gozSum);
            }
            
        } else {
            if (gozCodesCount > 0) {
                const gozSum = document.createElement('div');
                gozSum.className = 'summary-line goz-private-summary';
                gozSum.innerHTML = `<span>💰 GOZ Positionen:</span> <span>${gozCodesCount}</span>`;
                summaryDiv.appendChild(gozSum);
            }
        }
        
        const totalPositions = bemaCodesCount + gozCodesCount;
        if (totalPositions > 0) {
            const totalSum = document.createElement('div');
            totalSum.className = 'summary-line total-summary';
            totalSum.innerHTML = `<strong><span>📋 Gesamt erfasste Positionen:</span> <span>${totalPositions}</span></strong>`;
            summaryDiv.appendChild(totalSum);
        }
        
        summaryContainer.appendChild(summaryDiv);
    }
    
    // Price parsing function removed - no more euro calculations in frontend
    
    showProcessing(message) {
        document.getElementById('processing-section').classList.remove('hidden');
        document.getElementById('processing-status').textContent = message;
    }
    
    updateProcessingStatus(message) {
        document.getElementById('processing-status').textContent = message;
    }
    
    hideProcessing() {
        document.getElementById('processing-section').classList.add('hidden');
    }
    
    playback() {
        if (this.audioChunks.length > 0) {
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
            
            this.showToast('Wiedergabe gestartet', 'success');
        }
    }
    
    newRecording() {
        // Reset state
        this.audioChunks = [];
        this.currentDocumentation = null;
        
        // Reset UI
        document.getElementById('recording-section').style.display = 'block';
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('audio-visualizer').classList.add('hidden');
        
        this.updateRecordingUI();
        this.showToast('Bereit für neue Aufnahme', 'success');
    }
    
    editResults() {
        const transcriptionText = document.getElementById('transcription-text');
        const clinicalNotes = document.getElementById('clinical-notes');
        
        // Make transcription editable
        if (transcriptionText.contentEditable === 'true') {
            transcriptionText.contentEditable = 'false';
            transcriptionText.style.border = 'none';
            document.getElementById('edit-btn').innerHTML = '✏️ Bearbeiten';
        } else {
            transcriptionText.contentEditable = 'true';
            transcriptionText.style.border = '2px solid var(--primary-color)';
            transcriptionText.focus();
            document.getElementById('edit-btn').innerHTML = '✅ Fertig';
        }
    }
    
    async saveDocumentation() {
        if (!this.currentDocumentation) {
            this.showToast('Keine Dokumentation zum Speichern', 'warning');
            return;
        }
        
        try {
            // Update clinical notes
            this.currentDocumentation.clinical_notes = document.getElementById('clinical-notes').value;
            
            // Here you would typically save to a local database or send to server
            const savedData = {
                ...this.currentDocumentation,
                saved_at: new Date().toISOString(),
                updated_notes: document.getElementById('clinical-notes').value
            };
            
            // Store in localStorage as backup
            const savedDocs = JSON.parse(localStorage.getItem('savedDocumentations') || '[]');
            savedDocs.push(savedData);
            localStorage.setItem('savedDocumentations', JSON.stringify(savedDocs));
            
            this.showToast('Dokumentation gespeichert! 💾', 'success');
            
        } catch (error) {
            console.error('Save failed:', error);
            this.showToast('Speichern fehlgeschlagen: ' + error.message, 'error');
        }
    }
    
    exportDocumentation() {
        if (!this.currentDocumentation) {
            this.showToast('Keine Dokumentation zum Exportieren', 'warning');
            return;
        }
        
        try {
            // Create export data
            const exportData = {
                ...this.currentDocumentation,
                clinical_notes: document.getElementById('clinical-notes').value,
                exported_at: new Date().toISOString()
            };
            
            // Create downloadable file
            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(dataBlob);
            link.download = `medvox-${exportData.patient_id}-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            
            this.showToast('Dokumentation exportiert! 📤', 'success');
            
        } catch (error) {
            console.error('Export failed:', error);
            this.showToast('Export fehlgeschlagen: ' + error.message, 'error');
        }
    }
    
    toggleSettings() {
        console.log('🔧 Settings toggle clicked - DEBUGGING');
        try {
            const settingsPanel = document.getElementById('settings-panel');
            if (!settingsPanel) {
                console.error('❌ Settings panel not found!');
                this.showToast('Settings panel not found', 'error');
                return;
            }
            
            console.log('✅ Settings panel found:', settingsPanel);
            console.log('📋 Current classes:', settingsPanel.className);
            console.log('📐 Current style.right:', settingsPanel.style.right);
            
            const isOpen = settingsPanel.classList.contains('open');
            console.log('🔄 Settings panel current state:', isOpen ? 'open' : 'closed');
            
            // Force remove any hidden class and add open class
            settingsPanel.classList.remove('hidden');
            settingsPanel.classList.toggle('open');
            
            // Force style to ensure visibility
            if (settingsPanel.classList.contains('open')) {
                settingsPanel.style.right = '0px';
                settingsPanel.style.display = 'flex';
                console.log('🟢 FORCED OPEN: right=0px, display=flex');
            } else {
                settingsPanel.style.right = '-500px';
                console.log('🔴 CLOSED: right=-500px');
            }
            
            const newState = settingsPanel.classList.contains('open');
            console.log('🎯 Settings panel new state:', newState ? 'open' : 'closed');
            
            // Show toast for confirmation
            this.showToast(newState ? '⚙️ Settings geöffnet' : '❌ Settings geschlossen', 'success');
        } catch (error) {
            console.error('Error toggling settings:', error);
            this.showToast('Fehler beim Öffnen der Einstellungen', 'error');
        }
    }
    
    closeSettings() {
        console.log('🔴 Close settings called - DEBUGGING');
        try {
            const settingsPanel = document.getElementById('settings-panel');
            if (settingsPanel) {
                console.log('✅ Settings panel found for closing');
                console.log('📋 Current classes before close:', settingsPanel.className);
                
                // Remove open class AND reset direct style
                settingsPanel.classList.remove('open');
                settingsPanel.style.right = '-500px';
                
                console.log('🔴 FORCED CLOSED: right=-500px, removed open class');
                console.log('📋 Current classes after close:', settingsPanel.className);
                
                this.showToast('❌ Einstellungen geschlossen', 'info');
            } else {
                console.error('❌ Settings panel not found for closing!');
            }
        } catch (error) {
            console.error('💥 Error closing settings:', error);
        }
    }
    
    loadSettings() {
        console.log('Loading settings...');
        
        try {
            // General settings
            this.setElementValue('language-select', this.config.language);
            this.setElementValue('auto-start', this.config.autoStart, 'checked');
            this.setElementValue('voice-commands', this.config.voiceCommands, 'checked');
            this.setElementValue('auto-save', this.config.autoSave, 'checked');
            this.setElementValue('theme-select', this.config.theme);
            
            // Audio settings
            this.setElementValue('audio-quality', this.config.audioQuality);
            this.setElementValue('noise-reduction', this.config.noiseReduction, 'checked');
            this.setElementValue('auto-gain', this.config.autoGain, 'checked');
            this.setElementValue('whisper-model', this.config.whisperModel);
            
            // Practice settings
            this.setElementValue('practice-name', this.config.practiceName);
            this.setElementValue('default-dentist', this.config.defaultDentist);
            this.setElementValue('patient-id-format', this.config.patientIdFormat);
            this.setElementValue('require-patient-consent', this.config.requirePatientConsent, 'checked');
            this.setElementValue('data-retention', this.config.dataRetention);
            
            // Billing settings
            this.setElementValue('default-billing-system', this.config.defaultBillingSystem);
            this.setElementValue('goz-factor', this.config.gozFactor);
            this.setElementValue('show-billing-warnings', this.config.showBillingWarnings, 'checked');
            this.setElementValue('auto-billing-codes', this.config.autoBillingCodes, 'checked');
            this.setElementValue('billing-review-threshold', this.config.billingReviewThreshold);
            
            // Integration settings
            this.setElementValue('api-endpoint', this.config.apiEndpoint);
            this.setElementValue('evident-url', this.config.evidentUrl);
            this.setElementValue('evident-api-key', this.config.evidentApiKey);
            this.setElementValue('auto-export-evident', this.config.autoExportEvident, 'checked');
            this.setElementValue('export-format', this.config.exportFormat);
            this.setElementValue('backup-enabled', this.config.backupEnabled, 'checked');
            
            // Update dentist field with current setting
            const dentistField = document.getElementById('dentist-id');
            if (dentistField && this.config.defaultDentist) {
                dentistField.value = this.config.defaultDentist;
            }
            
            // Set insurance type toggle
            const insuranceRadio = document.querySelector(`input[name="insurance"][value="${this.config.selectedInsuranceType}"]`);
            if (insuranceRadio) {
                insuranceRadio.checked = true;
                // Trigger change event to update visual state
                insuranceRadio.dispatchEvent(new Event('change'));
            }
            
            // Load available microphones
            this.loadMicrophones();
            
            console.log('Settings loaded successfully');
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    setElementValue(elementId, value, property = 'value') {
        const element = document.getElementById(elementId);
        if (element) {
            if (property === 'checked') {
                element.checked = value;
            } else {
                element[property] = value;
            }
        }
    }
    
    setupSettingsTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.getAttribute('data-tab');
                
                // Remove active class from all tabs and contents
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding content
                button.classList.add('active');
                const targetContent = document.getElementById(`${targetTab}-tab`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
                
                console.log('Switched to tab:', targetTab);
            });
        });
    }
    
    setupSettingsActions() {
        // Save settings button
        const saveBtn = document.getElementById('save-settings');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSettings());
        }
        
        // Reset settings button
        const resetBtn = document.getElementById('reset-settings');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetSettings());
        }
        
        // Refresh microphones button
        const refreshMicsBtn = document.getElementById('refresh-microphones');
        if (refreshMicsBtn) {
            refreshMicsBtn.addEventListener('click', () => this.loadMicrophones());
        }
        
        // Test Evident connection button
        const testEvidentBtn = document.getElementById('test-evident');
        if (testEvidentBtn) {
            testEvidentBtn.addEventListener('click', () => this.testEvidentConnection());
        }
    }
    
    setupSettingsInputs() {
        // General settings
        this.addSettingListener('language-select', 'language');
        this.addSettingListener('auto-start', 'autoStart', 'change', 'checked');
        this.addSettingListener('voice-commands', 'voiceCommands', 'change', 'checked');
        this.addSettingListener('auto-save', 'autoSave', 'change', 'checked');
        this.addSettingListener('theme-select', 'theme');
        
        // Audio settings
        this.addSettingListener('microphone-select', 'selectedMicrophone');
        this.addSettingListener('audio-quality', 'audioQuality');
        this.addSettingListener('noise-reduction', 'noiseReduction', 'change', 'checked');
        this.addSettingListener('auto-gain', 'autoGain', 'change', 'checked');
        this.addSettingListener('whisper-model', 'whisperModel');
        
        // Practice settings
        this.addSettingListener('practice-name', 'practiceName');
        this.addSettingListener('default-dentist', 'defaultDentist');
        this.addSettingListener('patient-id-format', 'patientIdFormat');
        this.addSettingListener('require-patient-consent', 'requirePatientConsent', 'change', 'checked');
        this.addSettingListener('data-retention', 'dataRetention');
        
        // Billing settings
        this.addSettingListener('default-billing-system', 'defaultBillingSystem');
        this.addSettingListener('goz-factor', 'gozFactor', 'change', 'value', parseFloat);
        this.addSettingListener('show-billing-warnings', 'showBillingWarnings', 'change', 'checked');
        this.addSettingListener('auto-billing-codes', 'autoBillingCodes', 'change', 'checked');
        this.addSettingListener('billing-review-threshold', 'billingReviewThreshold', 'input', 'value', parseInt);
        
        // Integration settings
        this.addSettingListener('api-endpoint', 'apiEndpoint', 'change', 'value', null, () => this.checkAPIConnection());
        this.addSettingListener('evident-url', 'evidentUrl');
        this.addSettingListener('evident-api-key', 'evidentApiKey');
        this.addSettingListener('auto-export-evident', 'autoExportEvident', 'change', 'checked');
        this.addSettingListener('export-format', 'exportFormat');
        this.addSettingListener('backup-enabled', 'backupEnabled', 'change', 'checked');
    }
    
    addSettingListener(elementId, configKey, event = 'change', property = 'value', transform = null, callback = null) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.addEventListener(event, (e) => {
            let value = e.target[property];
            
            // Apply transformation if provided
            if (transform) {
                value = transform(value);
            }
            
            // Update config
            this.config[configKey] = value;
            
            // Save to localStorage
            localStorage.setItem(configKey, value);
            
            // Execute callback if provided
            if (callback) {
                callback();
            }
            
            console.log(`Setting updated: ${configKey} = ${value}`);
        });
    }
    
    handleKeyboardShortcuts(e) {
        // Space bar to toggle recording
        if (e.code === 'Space' && !e.target.matches('input, textarea')) {
            e.preventDefault();
            this.toggleRecording();
        }
        
        // Escape to stop recording or close settings
        if (e.code === 'Escape') {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.closeSettings();
            }
        }
        
        // S key to toggle settings (when not in input field)
        if (e.code === 'KeyS' && !e.target.matches('input, textarea') && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.toggleSettings();
        }
    }
    
    debugSettings() {
        console.log('=== SETTINGS DEBUG ===');
        const settingsPanel = document.getElementById('settings-panel');
        const settingsToggle = document.getElementById('settings-toggle');
        const closeSettings = document.getElementById('close-settings');
        
        console.log('Elements:', {
            settingsPanel: !!settingsPanel,
            settingsToggle: !!settingsToggle,
            closeSettings: !!closeSettings
        });
        
        if (settingsPanel) {
            console.log('Settings panel classes:', settingsPanel.className);
            console.log('Settings panel style:', settingsPanel.style.cssText);
            console.log('Settings panel computed style right:', getComputedStyle(settingsPanel).right);
        }
        
        if (settingsToggle) {
            console.log('Settings toggle visible:', settingsToggle.offsetParent !== null);
            console.log('Settings toggle position:', {
                top: settingsToggle.offsetTop,
                left: settingsToggle.offsetLeft,
                width: settingsToggle.offsetWidth,
                height: settingsToggle.offsetHeight
            });
        }
        
        // Try to toggle settings programmatically
        console.log('Testing toggle...');
        this.toggleSettings();
    }
    
    saveSettings() {
        try {
            console.log('Saving settings...');
            
            // All settings are already saved to localStorage through the event listeners
            // This is just a confirmation action
            
            this.showToast('✅ Einstellungen gespeichert!', 'success');
            
            // Apply any immediate changes
            this.applyTheme();
            this.updateDentistField();
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showToast('❌ Fehler beim Speichern der Einstellungen', 'error');
        }
    }
    
    resetSettings() {
        if (!confirm('Möchten Sie alle Einstellungen auf die Standardwerte zurücksetzen?')) {
            return;
        }
        
        try {
            console.log('Resetting settings...');
            
            // Clear localStorage
            const keysToKeep = ['apiEndpoint']; // Keep API endpoint
            Object.keys(localStorage).forEach(key => {
                if (!keysToKeep.includes(key)) {
                    localStorage.removeItem(key);
                }
            });
            
            // Reset config to defaults
            this.config = {
                apiEndpoint: this.config.apiEndpoint, // Keep current API endpoint
                language: 'de',
                autoStart: true,
                voiceCommands: true,
                autoSave: true,
                theme: 'auto',
                selectedMicrophone: 'default',
                audioQuality: 'high',
                noiseReduction: true,
                autoGain: true,
                whisperModel: 'whisper-1',
                practiceName: '',
                defaultDentist: 'Dr. Martin',
                patientIdFormat: 'free',
                requirePatientConsent: false,
                dataRetention: '30days',
                defaultBillingSystem: 'both',
                gozFactor: 2.3,
                showBillingWarnings: true,
                autoBillingCodes: true,
                billingReviewThreshold: 100,
                evidentUrl: '',
                evidentApiKey: '',
                autoExportEvident: false,
                exportFormat: 'json',
                backupEnabled: true,
                maxRecordingTime: 300,
                visualizerEnabled: true
            };
            
            // Reload settings in UI
            this.loadSettings();
            
            this.showToast('🔄 Einstellungen zurückgesetzt', 'success');
            
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showToast('❌ Fehler beim Zurücksetzen', 'error');
        }
    }
    
    async loadMicrophones() {
        try {
            console.log('Loading available microphones...');
            
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioInputs = devices.filter(device => device.kind === 'audioinput');
            
            const micSelect = document.getElementById('microphone-select');
            if (!micSelect) return;
            
            // Clear existing options except default
            micSelect.innerHTML = '<option value="default">Standard-Mikrofon</option>';
            
            // Add available microphones
            audioInputs.forEach(device => {
                const option = document.createElement('option');
                option.value = device.deviceId;
                option.textContent = device.label || `Mikrofon ${device.deviceId.substr(0, 8)}...`;
                micSelect.appendChild(option);
            });
            
            // Select current microphone
            micSelect.value = this.config.selectedMicrophone;
            
            console.log(`Found ${audioInputs.length} microphones`);
            this.showToast(`🎤 ${audioInputs.length} Mikrofone gefunden`, 'info');
            
        } catch (error) {
            console.error('Error loading microphones:', error);
            this.showToast('❌ Fehler beim Laden der Mikrofone', 'error');
        }
    }
    
    async testEvidentConnection() {
        const url = this.config.evidentUrl;
        const apiKey = this.config.evidentApiKey;
        
        if (!url) {
            this.showToast('❌ Evident URL ist erforderlich', 'error');
            return;
        }
        
        try {
            console.log('Testing Evident connection...');
            this.showToast('🧪 Teste Evident-Verbindung...', 'info');
            
            // Test connection to Evident API
            const response = await fetch(`${url}/api/health`, {
                method: 'GET',
                headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}
            });
            
            if (response.ok) {
                this.showToast('✅ Evident-Verbindung erfolgreich!', 'success');
            } else {
                this.showToast(`❌ Evident-Verbindung fehlgeschlagen (${response.status})`, 'error');
            }
            
        } catch (error) {
            console.error('Evident connection test failed:', error);
            this.showToast('❌ Evident-Verbindung fehlgeschlagen', 'error');
        }
    }
    
    applyTheme() {
        const theme = this.config.theme;
        const html = document.documentElement;
        
        if (theme === 'dark') {
            html.classList.add('dark-theme');
        } else if (theme === 'light') {
            html.classList.remove('dark-theme');
        } else {
            // Auto theme - detect system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
                html.classList.add('dark-theme');
            } else {
                html.classList.remove('dark-theme');
            }
        }
    }
    
    updateDentistField() {
        const dentistField = document.getElementById('dentist-id');
        if (dentistField && this.config.defaultDentist) {
            dentistField.value = this.config.defaultDentist;
        }
    }
    
    setupVoiceCommands() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.log('Voice commands not supported');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.speechRecognition = new SpeechRecognition();
        
        this.speechRecognition.continuous = true;
        this.speechRecognition.interimResults = false;
        this.speechRecognition.lang = 'de-DE';
        
        this.speechRecognition.onresult = (event) => {
            const command = event.results[event.results.length - 1][0].transcript.toLowerCase();
            
            if (command.includes('aufnahme starten') || command.includes('medvox start')) {
                if (!this.isRecording) this.startRecording();
            } else if (command.includes('aufnahme stoppen') || command.includes('medvox stopp')) {
                if (this.isRecording) this.stopRecording();
            } else if (command.includes('pause')) {
                if (this.isRecording) this.pauseRecording();
            }
        };
        
        // Start listening for voice commands
        this.speechRecognition.start();
    }
    
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div>${message}</div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 4000);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new MedVoxApp();
    
    // Make app globally accessible for debugging
    window.medvoxApp = app;
    
    // Register Service Worker for PWA functionality
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(() => console.log('Service Worker registered'))
            .catch(() => console.log('Service Worker registration failed'));
    }
}); 