"""
Configuration settings for MedVox
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("../.env")


class Settings(BaseSettings):
    """Application settings loaded directly from environment variables"""
    
    # App Settings
    PROJECT_NAME: str = "MedVox"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # CORS
    ALLOWED_HOSTS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    HSTS_MAX_AGE: int = 31536000  # 1 year
    X_FRAME_OPTIONS: str = "DENY"
    
    # Database
    DATABASE_URL: str = "sqlite:///./medvox.db"
    ECHO_SQL: bool = False
    
    # OpenAI/Whisper
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "whisper-1"
    MAX_AUDIO_SIZE_MB: int = 25
    SUPPORTED_AUDIO_FORMATS: str = "wav,mp3,m4a,flac,webm"
    AUDIO_SAMPLE_RATE: int = 44100  # Higher quality for better accuracy
    WHISPER_MODEL_SIZE: str = "large-v3"  # Best available model
    WHISPER_DEVICE: str = "auto"
    
    # Enhanced transcription settings
    WHISPER_TEMPERATURE: float = 0.1  # Lower for more consistent medical terms
    DENTAL_TERMINOLOGY_BOOST: bool = True  # Enable dental terminology enhancement
    
    # LLM Configuration for Intelligent Procedure Extraction  
    LLM_MODEL: str = "gemini-3-flash-preview"  # Gemini 3 Flash for fast, high-quality extraction
    LLM_TEMPERATURE: float = 0.1  # Lower temperature for medical consistency
    LLM_MAX_TOKENS: int = 65536  # Gemini 3 supports up to 65k output tokens
    USE_LLM_EXTRACTION: bool = True  # Enable LLM-based procedure extraction
    
    # Google Cloud Configuration
    GOOGLE_CLOUD_API_KEY: Optional[str] = None  # Google Cloud API Key for Speech-to-Text
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = None  # Google Cloud Project ID
    
    # LLM Provider Umschaltung
    LLM_PROVIDER: str = "google"  # "openai" oder "google"
    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    GOOGLE_GEMINI_API_URL: Optional[str] = None  # Auto-generated from LLM_MODEL if not set
    
    @property
    def gemini_api_url(self) -> str:
        """Build Gemini API URL from model name, or use explicit override"""
        if self.GOOGLE_GEMINI_API_URL:
            return self.GOOGLE_GEMINI_API_URL
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.LLM_MODEL}:generateContent"
    
    # Advanced models for complex cases
    ADVANCED_LLM_MODEL: str = "gemini-3-pro-preview"  # Gemini 3 Pro for complex billing cases
    BILLING_LLM_MODEL: str = "gemini-3-pro-preview"  # Gemini 3 Pro for BEMA/GOZ
    
    # Multi-Stage Pipeline Configuration - FORCE DISABLED for Gemini testing
    USE_MULTI_STAGE_PIPELINE: bool = False  # HARD OVERRIDE: Force disable pipeline
    PIPELINE_NORMALIZATION_ENABLED: bool = False
    PIPELINE_BILLING_MAPPING_ENABLED: bool = False
    PIPELINE_ADVANCED_BILLING_ENABLED: bool = False
    PIPELINE_PLAUSIBILITY_CHECK_ENABLED: bool = False
    
    # Pipeline Model Settings - USE GPT-4o (O3 requires verification)
    PIPELINE_NORMALIZATION_MODEL: str = "gpt-4o"
    PIPELINE_BILLING_MODEL: str = "gpt-4o"
    PIPELINE_AUDIT_MODEL: str = "gpt-4o"
    
    # Advanced o3 Configuration
    USE_O3_FOR_COMPLEX_CASES: bool = True  # Use full o3 for complex/high-value cases
    O3_COMPLEXITY_THRESHOLD: float = 100.0  # Euro threshold for using o3 instead of o3-mini
    O3_REASONING_MODE: str = "detailed"  # detailed, concise, or audit
    
    # Evident PMS
    EVIDENT_API_URL: str = "https://api.evident.de"
    EVIDENT_API_KEY: Optional[str] = None
    EVIDENT_CLIENT_ID: Optional[str] = None
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.DEBUG
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.DEBUG
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get CORS allowed hosts as a list"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    @property
    def supported_audio_formats_list(self) -> List[str]:
        """Get supported audio formats as a list"""
        return [fmt.strip() for fmt in self.SUPPORTED_AUDIO_FORMATS.split(",")]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # FORCE OVERRIDE: Disable pipeline for Gemini testing
        # This overrides any .env file settings that might be causing issues
        self.USE_MULTI_STAGE_PIPELINE = False
        self.PIPELINE_NORMALIZATION_ENABLED = False
        self.PIPELINE_BILLING_MAPPING_ENABLED = False
        self.PIPELINE_ADVANCED_BILLING_ENABLED = False
        self.PIPELINE_PLAUSIBILITY_CHECK_ENABLED = False
        
        # Validate that required settings are present in production
        if self.is_production:
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required in production")
            if self.SECRET_KEY == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be set in production")
        else:
            # In development, warn about missing API key but don't fail
            if not self.OPENAI_API_KEY:
                import warnings
                warnings.warn("OPENAI_API_KEY not set - only mock transcription will work")
    
    class Config:
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Create settings instance
settings = Settings() 