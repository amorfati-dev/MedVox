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

export interface PatientFormData {
  patientId: string;
  dentistName: string;
  insuranceType: 'BEMA' | 'GOZ';
}

// API Request Types
export interface ProcessAudioRequest {
  audio_file: File;
  patient_id?: string;
  dentist_name?: string;
  insurance_type?: 'BEMA' | 'GOZ';
} 