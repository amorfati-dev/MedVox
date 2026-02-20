#!/usr/bin/env python3
"""
MedVox Configuration Diagnostic Tool
Checks all critical settings that could prevent LLM extraction
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

try:
    from app.core.config import settings
    print("✅ Settings loaded successfully")
except Exception as e:
    print(f"❌ Failed to load settings: {e}")
    sys.exit(1)

def check_config():
    print("\n🔍 MedVox LLM Configuration Diagnostic")
    print("=" * 50)
    
    # 1. OpenAI API Key
    api_key = settings.OPENAI_API_KEY
    if api_key:
        print(f"✅ OPENAI_API_KEY: Set (length: {len(api_key)})")
        print(f"   Starts with: {api_key[:10]}...")
    else:
        print("❌ OPENAI_API_KEY: NOT SET")
        print("   🚨 This will prevent LLM extraction!")
    
    # 2. LLM Model Configuration
    print(f"\n🤖 LLM Model Configuration:")
    print(f"   LLM_MODEL: {settings.LLM_MODEL}")
    print(f"   LLM_TEMPERATURE: {settings.LLM_TEMPERATURE}")
    print(f"   LLM_MAX_TOKENS: {settings.LLM_MAX_TOKENS}")
    print(f"   USE_LLM_EXTRACTION: {settings.USE_LLM_EXTRACTION}")
    
    # 3. Critical Conditions
    print(f"\n🔧 Critical Conditions:")
    
    # Check condition 1: API key exists
    has_api_key = settings.OPENAI_API_KEY is not None
    print(f"   OPENAI_API_KEY is not None: {has_api_key}")
    
    # Check condition 2: LLM extraction enabled
    llm_extraction_enabled = settings.USE_LLM_EXTRACTION
    print(f"   USE_LLM_EXTRACTION: {llm_extraction_enabled}")
    
    # Check condition 3: Combined condition
    use_llm = llm_extraction_enabled and has_api_key
    print(f"   Combined (should enable LLM): {use_llm}")
    
    # 4. Pipeline Configuration
    print(f"\n🚰 Pipeline Configuration:")
    print(f"   USE_MULTI_STAGE_PIPELINE: {settings.USE_MULTI_STAGE_PIPELINE}")
    print(f"   PIPELINE_NORMALIZATION_ENABLED: {settings.PIPELINE_NORMALIZATION_ENABLED}")
    print(f"   PIPELINE_BILLING_MAPPING_ENABLED: {settings.PIPELINE_BILLING_MAPPING_ENABLED}")
    
    # 5. Environment Variables
    print(f"\n🌍 Environment Variables:")
    env_openai_key = os.getenv('OPENAI_API_KEY')
    if env_openai_key:
        print(f"   ENV OPENAI_API_KEY: Set (length: {len(env_openai_key)})")
    else:
        print("   ENV OPENAI_API_KEY: NOT SET")
    
    # 6. Model Validation
    print(f"\n🎯 Model Validation:")
    try:
        from app.services.llm_processor import LLMProcedureExtractor
        extractor = LLMProcedureExtractor()
        print(f"   ✅ LLMProcedureExtractor created successfully")
        print(f"   Model: {extractor.model}")
        print(f"   API Key exists: {bool(extractor.api_key)}")
    except Exception as e:
        print(f"   ❌ LLMProcedureExtractor failed: {e}")
    
    # 7. RAG System
    print(f"\n🔍 RAG System:")
    try:
        from app.services.rag_retriever import DentalCodeRetriever
        retriever = DentalCodeRetriever()
        catalog_info = retriever.get_catalog_info()
        print(f"   ✅ RAG retriever created successfully")
        print(f"   BEMA codes: {catalog_info['bema_codes_count']}")
        print(f"   GOZ codes: {catalog_info['goz_codes_count']}")
        print(f"   GOÄ codes: {catalog_info['goae_codes_count']}")
    except Exception as e:
        print(f"   ❌ RAG retriever failed: {e}")
    
    # 8. Final Diagnosis
    print(f"\n🏥 DIAGNOSIS:")
    if not has_api_key:
        print("   🚨 PRIMARY ISSUE: OPENAI_API_KEY not set!")
        print("   💡 SOLUTION: Set your OpenAI API key in environment")
    elif not llm_extraction_enabled:
        print("   🚨 PRIMARY ISSUE: USE_LLM_EXTRACTION is False!")
        print("   💡 SOLUTION: Check your configuration")
    elif use_llm:
        print("   ✅ Configuration looks good!")
        print("   🔍 Issue might be in code execution or error handling")
    else:
        print("   🚨 UNKNOWN ISSUE: Check logs for errors")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    check_config() 