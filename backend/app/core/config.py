"""
Configuration settings for MedVox application
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator, Field


class AppSettings(BaseSettings):
    """Application core settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MedVox"
    DEBUG: bool = False
    
    # CORS - Restrict to specific origins in production
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = True


class SecuritySettings(BaseSettings):
    """Security-related settings"""
    
    # Secret key with fallback for development
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", description="Secret key for JWT tokens")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Security headers
    HSTS_MAX_AGE: int = 31536000  # 1 year
    X_FRAME_OPTIONS: str = "DENY"
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = True


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    
    DATABASE_URL: str = Field(
        default="postgresql://medvox:medvox@localhost/medvox",
        description="Database connection URL"
    )
    ECHO_SQL: bool = False
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = True


class OpenAISettings(BaseSettings):
    """OpenAI/Whisper configuration"""
    
    # API key is optional for development/testing
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API key")
    OPENAI_MODEL: str = "whisper-1"
    
    # Audio Processing
    MAX_AUDIO_SIZE_MB: int = 25
    SUPPORTED_AUDIO_FORMATS: List[str] = ["wav", "mp3", "m4a", "flac"]
    AUDIO_SAMPLE_RATE: int = 16000
    
    # Whisper specific settings
    WHISPER_MODEL_SIZE: str = "base"  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = "auto"  # auto, cpu, cuda
    
    class Config:
        env_prefix = "OPENAI_"
        case_sensitive = True


class EvidentSettings(BaseSettings):
    """Evident PMS integration settings"""
    
    # No defaults for API credentials - must be set via environment
    EVIDENT_API_URL: Optional[str] = Field(None, description="Evident API base URL")
    EVIDENT_API_KEY: Optional[str] = Field(None, description="Evident API key")
    EVIDENT_CLIENT_ID: Optional[str] = Field(None, description="Evident client ID")
    
    class Config:
        env_prefix = "EVIDENT_"
        case_sensitive = True


class Settings(BaseSettings):
    """Main settings class that combines all settings"""
    
    app: AppSettings = AppSettings()
    security: SecuritySettings = SecuritySettings()
    database: DatabaseSettings = DatabaseSettings()
    openai: OpenAISettings = OpenAISettings()
    evident: EvidentSettings = EvidentSettings()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app.DEBUG
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.app.DEBUG
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate that required settings are present in production
        if self.is_production:
            if not self.openai.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required in production")
            if self.security.SECRET_KEY == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be set in production")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings() 