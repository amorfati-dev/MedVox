// API Response Types based on Gemini LLM output
export interface BillingCode {
  code: string;
  system?: 'BEMA' | 'GOZ';
  code_system?: string;
  description?: string;
  description_de?: string;
  bezeichnung?: string;
  leistungsbeschreibung?: string;
  quantity?: number;
  anzahl?: number;
  fee?: number;
  is_zusatzleistung?: boolean;
  tooth_number?: string;
}

export interface DentalProcedure {
  procedure_name?: string;
  procedure_description_de?: string;
  prozedur?: string;
  tooth?: string;
  tooth_number?: string;
  zahn?: string;
  surfaces?: string[];
  material?: string;
  description?: string;
  beschreibung_kurz?: string;
  billing_codes?: BillingCode[];
  abrechnung?: BillingCode[];
}

export interface PatientInfo {
  patient_status?: string;
  versichertenstatus?: string;
  treatment_date?: string;
  treated_teeth?: string[];
  findings?: string;
  befunde?: string[];
}

export interface TranscriptionResult {
  text: string;
  language: string;
  confidence: number;
  segments?: any[];
  processing_time_ms?: number;
  stt_model?: string;
}

export interface DocumentationResponse {
  transcription?: string | TranscriptionResult;
  confidence?: number;
  language?: string;
  patient_status?: string;
  treatment_date?: string;
  treated_teeth?: string[];
  findings?: string;
  procedures?: DentalProcedure[];
  billing_codes?: BillingCode[];
  abrechnungstyp?: string;
  patient?: PatientInfo;
  abrechnungspositionen?: BillingCode[];
  patient_case?: string;
  total_fee?: number;
}

// UI State Types
export interface SelectedBillingCode extends BillingCode {
  id: string;
  selected: boolean;
  procedure_context?: string;
  tooth_context?: string;
}

export interface RecordingState {
  isRecording: boolean;
  isProcessing: boolean;
  duration: number;
  audioUrl?: string;
}

// Session-based Recording Types
export interface AudioSegment {
  blob: Blob;
  duration: number;
  transcription: string;
  timestamp: Date;
}

export interface RecordingSession {
  segments: AudioSegment[];
  isActive: boolean;
  accumulatedTranscription: string;
  patientId: string;
  dentistName: string;
  insuranceType: 'BEMA' | 'GOZ';
}

export type SessionState = 'idle' | 'recording' | 'paused' | 'processing';

export interface PatientFormData {
  patientId: string;
  dentistName: string;
  insuranceType: 'BEMA' | 'GOZ';
}

// Dentist Management Types
export interface DentistInfo {
  id: string;
  name: string;
  licenseNumber?: string;
}

// Settings Types
export interface AppSettings {
  dentists: DentistInfo[];
  currentDentistId: string;
  defaultInsuranceType: 'BEMA' | 'GOZ';
  defaultProcessingMode: ProcessingMode;
  gozFactor: number;
  autoStopDuration: number;
  apiEndpoint: string;
  // Legacy field for backward compatibility
  dentistName?: string;
}

export const DEFAULT_SETTINGS: AppSettings = {
  dentists: [
    {
      id: 'dentist-1',
      name: 'Dr. Martin Hartmann',
    },
  ],
  currentDentistId: 'dentist-1',
  defaultInsuranceType: 'BEMA',
  defaultProcessingMode: 'with_billing',
  gozFactor: 2.3,
  autoStopDuration: 120,
  apiEndpoint: '/api/v1',
};

// API Request Types
export interface ProcessAudioRequest {
  audio_file: File;
  patient_id?: string;
  dentist_name?: string;
  insurance_type?: 'BEMA' | 'GOZ';
}

// Transfer Session Types
export interface TransferSession {
  session_id: string;
  short_code?: string;
  transfer_url: string;
  qr_code: string;
  expires_at: string;
  expires_in_seconds: number;
}

export interface CreateTransferRequest {
  billing_codes: BillingCode[];
  transcription: string;
  patient_id?: string;
}

// Session Management Types
export type ProcessingMode = 'transcription_only' | 'with_billing';

export interface SessionSummary {
  id: number;
  patient_id: string | null;
  dentist_id: number;
  dentist_name: string;
  transcription_preview: string;
  processing_mode: ProcessingMode;
  billing_codes_count: number;
  created_at: string;
  status: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
}

// Auth Types
export interface AuthUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
}