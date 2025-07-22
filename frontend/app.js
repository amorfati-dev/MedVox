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
        const closeSettings = document.getElementById('close-settings');
        
        console.log('Settings toggle button found:', !!settingsToggle);
        console.log('Close settings button found:', !!closeSettings);
        
        if (settingsToggle) {
            settingsToggle.addEventListener('click', () => this.toggleSettings());
            console.log('Settings toggle event listener attached');
        } else {
            console.error('Settings toggle button not found!');
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
            formData.append('use_mock', 'false'); // Use real OpenAI Whisper
            
            this.updateProcessingStatus('Transkription wird erstellt...');
            
            // Send to API
            const response = await fetch(`${this.config.apiEndpoint}/api/v1/documentation/process-audio`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.displayResults(result.documentation);
                this.showToast('Dokumentation erstellt! 🎉', 'success');
            } else {
                throw new Error(result.error_message || 'Processing failed');
            }
            
        } catch (error) {
            console.error('Processing failed:', error);
            this.showToast('Verarbeitung fehlgeschlagen: ' + error.message, 'error');
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
        
        // Transcription
        document.getElementById('transcription-text').textContent = documentation.transcription.text;
        document.getElementById('confidence-score').textContent = Math.round(documentation.transcription.confidence * 100);
        document.getElementById('detected-language').textContent = documentation.transcription.language.toUpperCase();
        
        // Procedures
        const proceduresList = document.getElementById('procedures-list');
        proceduresList.innerHTML = '';
        documentation.procedures_performed.forEach(procedure => {
            const tag = document.createElement('span');
            tag.className = 'procedure-tag';
            tag.textContent = procedure;
            proceduresList.appendChild(tag);
        });
        
        // Billing codes
        const billingCodes = document.getElementById('billing-codes');
        billingCodes.innerHTML = '';
        let totalFee = 0;
        
        documentation.billing_codes.forEach(code => {
            const codeElement = document.createElement('div');
            codeElement.className = 'billing-code';
            codeElement.innerHTML = `
                <div class="code-info">
                    <div class="code-number">${code.code}</div>
                    <div class="code-description">${code.description}</div>
                </div>
                <div class="code-fee">€${code.fee_euros.toFixed(2)}</div>
            `;
            billingCodes.appendChild(codeElement);
            totalFee += code.fee_euros;
        });
        
        document.getElementById('total-fee').textContent = `€${totalFee.toFixed(2)}`;
        
        // Clinical notes
        document.getElementById('clinical-notes').value = documentation.clinical_notes || '';
        
        // Store documentation for export
        this.currentDocumentation = documentation;
    }
    
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