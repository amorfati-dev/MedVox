"""
Enhanced LLM Processor Service
Uses Gemini2.5 Pro advanced models for intelligent procedure and billing code extraction
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
import structlog

from app.core.config import settings
from app.schemas.dental_documentation import DentalFinding, BillingCode, BillingSystem, ConfidenceLevel
from app.utils.llm_logger import llm_logger
from app.services.rag_retriever import DentalCodeRetriever

import requests

logger = structlog.get_logger()


class LLMExtractionError(Exception):
    """Custom exception for LLM extraction errors"""
    pass


class GeminiLLMProcedureExtractor:
    """Extract dental procedures and billing codes using Google Gemini 3"""
    def __init__(self):
        from app.core.config import settings
        self.api_key = settings.GOOGLE_GEMINI_API_KEY
        self.api_url = settings.gemini_api_url  # Auto-generated from LLM_MODEL
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.max_completion_tokens = settings.LLM_MAX_TOKENS  # Alias for compatibility
        self.temperature = settings.LLM_TEMPERATURE
        
        # RAG temporarily disabled for simplification
        # from app.services.rag_retriever import DentalCodeRetriever
        # self.rag_retriever = DentalCodeRetriever()
        
        # 🔍 DEBUG: Check model assignment
        logger.info(f"🔧 settings.LLM_MODEL: {settings.LLM_MODEL}")
        logger.info(f"🔧 Hardcoded self.model: {self.model}")
        logger.info(f"🤖 Gemini LLM initialized: {self.model}")
        logger.info(f"🔑 Gemini API Key present: {bool(self.api_key)}")
        logger.info(f"🌐 Gemini API URL: {self.api_url}")
        # logger.info(f"🔍 RAG retriever initialized with {self.rag_retriever.get_catalog_info()}")

    async def extract_procedures_and_codes(self, text: str, bema_goz_catalog: dict, findings: list = None, insurance_type: str = "bema") -> dict:
        """
        Use Gemini to extract procedures and suggest BEMA/GOZ codes
        """
        import asyncio
        findings_context = ""
        if findings:
            findings_context = "\n".join([
                f"- Zahn {f.tooth_number}: {f.diagnosis}" + (f" ({f.surface})" if f.surface else "")
                for f in findings
            ])
        prompt = self._create_extraction_prompt(text, bema_goz_catalog, findings_context)
        logger.info("Starting Gemini LLM extraction", text_length=len(text), model=self.model)
        headers = {
            "Content-Type": "application/json",
        }
        # Create insurance-specific prompt
        insurance_instruction = ""
        if insurance_type.lower() == "bema":
            insurance_instruction = """ABRECHNUNGSTYP: BEMA (Gesetzlich versicherter Kassenpatient)

REGELN FÜR BEMA-ABRECHNUNG:
- Verwende primär BEMA-Abrechnungsziffern für alle Kassenleistungen
- WICHTIG: Prüfe bei jeder Behandlung, ob GOZ-Zusatzleistungen (Zuzahlungen) sinnvoll sind
- Zusatzleistungen sind Leistungen, die über den Kassenkatalog hinausgehen und vom Patienten privat bezahlt werden
- Beispiele für Zusatzleistungen: Kompositfüllungen statt Amalgam (GOZ 2080 + 2197), hochwertige Keramik, Adhäsivtechnik, erweiterte Prophylaxe
- Markiere Zusatzleistungen mit "is_zusatzleistung": true und "system": "GOZ"
- Alle Kassenleistungen mit "is_zusatzleistung": false und "system": "BEMA"
"""
        else:
            insurance_instruction = """ABRECHNUNGSTYP: GOZ (Privatpatient)

REGELN FÜR GOZ-ABRECHNUNG:
- Verwende ausschließlich GOZ-Abrechnungsziffern
- Beachte die Steigerungsfaktoren (Standard 2,3-fach)
- Ärztliche Leistungen mit Ä-Ziffern abrechnen (z.B. Ä5004 für Röntgen)
- Alle Leistungen mit "system": "GOZ" und "is_zusatzleistung": false
"""
            
        body = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{insurance_instruction}\nBEHANDLUNGSDOKUMENTATION:\n{prompt}\n\nErstelle eine vollständige Abrechnung als JSON mit 'procedures' und 'billing_codes'."}]}
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "responseMimeType": "application/json"
            }
        }
        
        # Simple logging
        logger.info(f"🎤 Voice input: {len(prompt)} chars → {self.model} ({insurance_type.upper()})")
        
        # Retry logic for timeouts
        max_retries = 3
        timeout_seconds = 90  # Increased from 60
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Gemini attempt {attempt + 1}/{max_retries}")
                # Add API key as query parameter (Google Gemini auth method)
                url_with_key = f"{self.api_url}?key={self.api_key}"
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(url_with_key, headers=headers, json=body, timeout=timeout_seconds)
                )
                # If we get here, the request succeeded
                break
            except Exception as retry_error:
                logger.warning(f"🔄 Gemini attempt {attempt + 1} failed: {retry_error}")
                if attempt == max_retries - 1:
                    # Last attempt failed, re-raise the error
                    raise retry_error
                # Wait before retry (exponential backoff)
                wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
                continue
        
        try:
            logger.info(f"Gemini API status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.text}")
                raise Exception(f"Gemini API error: {response.status_code}")
            data = response.json()
            
            # 🔍 CRITICAL DEBUG: Log what Gemini actually returned
            logger.debug(f"🔍 GEMINI RAW RESPONSE: {data}")
            logger.info(f"🔍 Gemini response keys: {list(data.keys())}")
            logger.info(f"🔍 Gemini response type: {type(data)}")
            
            # Parse Gemini response structure
            try:
                candidate = data["candidates"][0]
                finish_reason = candidate.get("finishReason", "")
                
                logger.debug(f"🔍 GEMINI FINISH REASON: {finish_reason}")
                
                if finish_reason == "MAX_TOKENS":
                    logger.error("Gemini response was cut off due to MAX_TOKENS limit")
                    raise Exception("Response truncated - increase max_tokens")
                
                if finish_reason == "SAFETY":
                    logger.error("Gemini response blocked by safety filters")
                    raise Exception("Response blocked by safety filters")
                
                # Extract the actual response text
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                
                logger.debug(f"🔍 GEMINI CONTENT: {content}")
                logger.debug(f"🔍 GEMINI PARTS: {parts}")
                
                if not parts:
                    logger.error(f"No parts in Gemini response. Content: {content}")
                    raise Exception("No response content received")
                
                result_text = parts[0].get("text", "")
                
                logger.debug(f"🔍 GEMINI RESULT TEXT: {result_text[:500]}...")
                
                if not result_text:
                    logger.error("Empty text in Gemini response")
                    raise Exception("Empty response text")
                    
            except Exception as e:
                logger.error(f"Gemini response parsing failed: {e}")
                logger.error(f"Raw Gemini response: {data}")
                raise Exception(f"Gemini response parsing failed: {str(e)}")
            # 🎯 DIRECT RAW OUTPUT - no processing!
            logger.info("✅ Gemini response received - returning raw")
            
            # Try to parse as JSON, but if it fails, return the raw text
            try:
                logger.debug("Attempting JSON parse of Gemini response")
                result = json.loads(result_text)
                
                # Handle both object and array responses from Gemini
                if isinstance(result, list):
                    logger.debug(f"🔍 JSON PARSE SUCCESS: Array with {len(result)} items")
                    # Convert array to object format for normalization
                    result = {"procedures": result}
                elif isinstance(result, dict):
                    logger.debug(f"🔍 JSON PARSE SUCCESS: Object with keys {list(result.keys())}")
                else:
                    logger.debug(f"🔍 JSON PARSE SUCCESS: {type(result).__name__}")
                
                # 🔧 FIX: Convert Gemini's field names to our expected format
                normalized_result = self._normalize_gemini_response(result)
                logger.debug(f"🔍 NORMALIZED RESULT: {list(normalized_result.keys())}")
                
                normalized_result["raw_gemini_response"] = result_text
                return normalized_result
            except Exception as json_error:
                logger.debug(f"🔍 JSON PARSE FAILED: {json_error}")
                logger.debug(f"🔍 JSON PARSE FAILED - Raw text preview: {result_text[:200]}...")
                # If JSON parsing fails, return raw text for frontend
                return {
                    "raw_gemini_response": result_text,
                    "procedures": [],
                    "billing_codes": []
                }
        except Exception as e:
            logger.error(f"Gemini LLM extraction failed: {e}")
            return {"procedures": [], "billing_codes": [], "error": str(e)}
    
    def _extract_single_billing_code(self, code_obj: dict, parent_obj: dict = None) -> dict:
        """Extract a single billing code from various possible formats"""
        if not isinstance(code_obj, dict):
            return None
            
        # Try all possible field name combinations Gemini might use
        code_value = (
            code_obj.get("code") or 
            code_obj.get("ziffer") or 
            code_obj.get("position") or 
            code_obj.get("nummer") or ""
        ).strip()
        
        description = (
            code_obj.get("description") or 
            code_obj.get("beschreibung") or 
            code_obj.get("text") or ""
        ).strip()
        
        # Extract system/type information
        system = (
            code_obj.get("system") or 
            code_obj.get("fee_type") or 
            code_obj.get("abrechnungsart") or 
            code_obj.get("gebuehrenordnung") or 
            code_obj.get("type") or ""
        ).lower().strip()
        
        # Clean up system name
        if "bema" in system:
            system = "bema"
        elif "goz" in system or "goä" in system:
            system = "goz"
        elif system and "privat" not in system and "zusatz" not in system:
            # If we have a system but it's not clearly BEMA/GOZ, default to BEMA
            system = "bema"
        else:
            # If no system specified, default to BEMA (since most German dental codes are BEMA)
            system = "bema"
        
        # Get tooth number from code or parent
        tooth_number = (
            code_obj.get("tooth_number") or 
            code_obj.get("zahn_nummer") or 
            code_obj.get("zahn") or
            (parent_obj.get("tooth_number") if parent_obj else None) or
            (parent_obj.get("zahn_region") if parent_obj else None) or
            None
        )
        
        # Only return if we have at least a code
        if code_value:
            return {
                "code": code_value,
                "description": description,
                "system": system,
                "type": system,
                "tooth_number": tooth_number,
                "quantity": code_obj.get("quantity") or code_obj.get("anzahl") or 1,
                "factor": code_obj.get("factor") or code_obj.get("faktor") or 1.0,
                "points": code_obj.get("points") or code_obj.get("punkte") or 0,
                "confidence": "medium"
            }
        return None
    
    def _normalize_gemini_response(self, result: dict) -> dict:
        """Convert Gemini's response format to our expected format - UNIVERSAL PARSER"""
        
        logger.debug(f"🔧 NORMALIZING Gemini response: {list(result.keys())}")
        
        normalized = {}
        all_billing_codes = []
        simple_procedures = []
        
        # 🚀 UNIVERSAL EXTRACTION: Find billing codes ANYWHERE in the JSON
        def extract_codes_recursively(obj, parent_key="", depth=0):
            """Recursively extract billing codes from any JSON structure"""
            logger.debug(f"{'  ' * depth}🔍 Scanning: {parent_key} (type: {type(obj).__name__})")
            
            if isinstance(obj, dict):
                # Look for billing code arrays with various names
                for key in ["billing_codes", "abrechnungspositionen", "abrechnungsziffern", "codes", "positionen", "entries"]:
                    if key in obj and isinstance(obj[key], list):
                        logger.debug(f"{'  ' * depth}✅ FOUND {key} with {len(obj[key])} codes")
                        for code_obj in obj[key]:
                            extracted = self._extract_single_billing_code(code_obj, obj)
                            if extracted:
                                all_billing_codes.append(extracted)
                                logger.debug(f"{'  ' * depth}  📋 Extracted: {extracted['code']} ({extracted.get('system', 'unknown')})")
                
                # Look for procedure names
                for key in ["procedure_description", "bezeichnung", "name", "description", "procedure_name"]:
                    if key in obj and isinstance(obj[key], str):
                        simple_procedures.append(obj[key])
                        logger.debug(f"{'  ' * depth}  📝 Found procedure: {obj[key]}")
                
                # Recurse into nested objects
                for key, value in obj.items():
                    extract_codes_recursively(value, f"{parent_key}.{key}" if parent_key else key, depth + 1)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_codes_recursively(item, f"{parent_key}[{i}]", depth + 1)
        
        # Start recursive extraction
        logger.debug(f"🚀 Starting UNIVERSAL extraction...")
        extract_codes_recursively(result)
        
        # Remove duplicates while preserving order
        unique_procedures = []
        for proc in simple_procedures:
            if proc not in unique_procedures:
                unique_procedures.append(proc)
        
        normalized["procedures"] = unique_procedures
        normalized["billing_codes"] = all_billing_codes
        
        logger.debug(f"🎯 UNIVERSAL EXTRACTION COMPLETE:")
        logger.debug(f"   📝 Procedures: {len(unique_procedures)}")
        logger.debug(f"   📋 Billing Codes: {len(all_billing_codes)}")
        
        # If we found anything, we're done!
        if all_billing_codes or unique_procedures:
            return normalized
        
        # 🆕 Fallback: Handle specific known structures
        if "abrechnung" in result:
            logger.debug(f"🔧 FOUND 'abrechnung' structure - extracting billing codes")
            abrechnung = result["abrechnung"]
            
            simple_procedures = []
            all_billing_codes = []
            
            # Extract from behandlungen array
            behandlungen = abrechnung.get("behandlungen", [])
            logger.debug(f"🔧 Found {len(behandlungen)} behandlungen")
            
            for behandlung in behandlungen:
                # Extract procedure name
                proc_name = behandlung.get("bezeichnung", "Unbekannte Behandlung")
                simple_procedures.append(proc_name)
                logger.debug(f"🔧 Added procedure: {proc_name}")
                
                # Extract billing codes from abrechnungspositionen
                abrechnungspositionen = behandlung.get("abrechnungspositionen", [])
                logger.debug(f"🔧 Found {len(abrechnungspositionen)} abrechnungspositionen in '{proc_name}'")
                
                for pos in abrechnungspositionen:
                    logger.debug(f"🔧 Processing position: {pos}")
                    
                    # Map German fields to our format
                    converted_code = {
                        "code": pos.get("ziffer", ""),
                        "description": pos.get("beschreibung", ""),
                        "system": pos.get("abrechnungsart", "").lower(),  # "BEMA" -> "bema"
                        "type": pos.get("abrechnungsart", "").lower(),
                        "tooth_number": behandlung.get("zahn_region", None),
                        "quantity": pos.get("anzahl", 1),
                        "factor": pos.get("faktor", 1.0),
                        "points": pos.get("punkte", 0),
                        "confidence": "medium"
                    }
                    all_billing_codes.append(converted_code)
                    logger.debug(f"🔧 EXTRACTED billing code: {converted_code['code']} ({converted_code['system']})")
            
            normalized["procedures"] = simple_procedures
            normalized["billing_codes"] = all_billing_codes
            logger.debug(f"🔧 FINAL: {len(simple_procedures)} procedures, {len(all_billing_codes)} billing codes")
            return normalized
        
        # Convert procedures and extract nested billing codes
        elif "treatment_summary" in result:
            treatment = result["treatment_summary"]
            procedures = []
            if "treatment_description" in treatment:
                procedures.append(treatment["treatment_description"])
            normalized["procedures"] = procedures
            logger.debug(f"🔧 MAPPED treatment_summary → procedures: {procedures}")
        elif "procedures" in result or "prozeduren" in result:
            # Handle nested structure where billing_codes are inside procedures (English or German)
            procedures_list = result.get("procedures") or result.get("prozeduren", [])
            simple_procedures = []
            all_billing_codes = []
            
            for proc in procedures_list:
                # Extract procedure name (English or German)
                if isinstance(proc, dict):
                    proc_name = (proc.get("procedure_name") or 
                               proc.get("beschreibung") or 
                               str(proc))
                    simple_procedures.append(proc_name)
                    
                    # Extract nested billing codes (handle ALL possible field names Gemini might use)
                    billing_codes_field = None
                    field_name_used = None
                    
                    for field_name in ["billing_codes", "abrechnungspositionen", "abrechnungsziffern", "billing_entries", "codes", "positionen", "entries"]:
                        if field_name in proc and proc[field_name]:
                            billing_codes_field = proc[field_name]
                            field_name_used = field_name
                            break
                    
                    logger.debug(f"🔍 PROCEDURE FIELDS: {list(proc.keys())}")
                    logger.debug(f"🔍 FOUND billing field: '{field_name_used}' with {len(billing_codes_field) if billing_codes_field else 0} codes")
                    
                    if billing_codes_field:
                        for code in billing_codes_field:
                            # Convert nested billing code format (handle German fields)
                            
                            # Debug: Show what fields Gemini provided
                            logger.debug(f"🔍 RAW CODE DATA: {code}")
                            
                            code_value = (code.get("code") or code.get("position") or "")
                            type_value = (code.get("code_system") or 
                                        code.get("gebuehrenordnung") or
                                        code.get("system") or "").lower()
                            
                            logger.debug(f"🔍 MAPPED code: '{code_value}', type: '{type_value}'")
                            
                            converted_code = {
                                "code": code_value,
                                "description": (code.get("description") or 
                                              code.get("beschreibung") or ""),
                                "type": type_value,
                                "tooth_number": (proc.get("tooth_number") or 
                                               proc.get("zahn") or ""),
                                "quantity": (code.get("quantity") or 
                                           code.get("anzahl") or 1),
                                "factor": (code.get("factor") or 
                                         code.get("faktor") or 1.0),
                                "points": (code.get("points") or 
                                         code.get("punkte") or 0),
                                "note": ""
                            }
                            all_billing_codes.append(converted_code)
                            logger.debug(f"🔧 EXTRACTED nested billing code: {converted_code['code']} (type: {converted_code['type']}) from procedure")
                else:
                    simple_procedures.append(str(proc))
            
            normalized["procedures"] = simple_procedures
            
            # If we found nested billing codes, use them
            if all_billing_codes:
                if "billing_codes" not in normalized:
                    normalized["billing_codes"] = []
                normalized["billing_codes"].extend(all_billing_codes)
                logger.debug(f"🔧 EXTRACTED {len(all_billing_codes)} billing codes from nested procedures")
        else:
            normalized["procedures"] = result.get("procedures", [])
        
        # Convert billing codes  
        if "billing_entries" in result:
            billing_entries = result["billing_entries"]
            billing_codes = []
            
            for entry in billing_entries:
                # Convert each billing entry to our expected format
                converted_code = {
                    "code": entry.get("code", ""),
                    "description": entry.get("description", ""),
                    "type": entry.get("billing_type", "").lower(),
                    "tooth_number": entry.get("tooth_region", ""),
                    "quantity": entry.get("quantity", 1),
                    "factor": entry.get("factor", 1.0),
                    "points": entry.get("points", 0),
                    "note": ""
                }
                billing_codes.append(converted_code)
                logger.debug(f"🔧 CONVERTED billing entry: {entry.get('code')} → {converted_code}")
            
            normalized["billing_codes"] = billing_codes
            logger.debug(f"🔧 MAPPED billing_entries → billing_codes: {len(billing_codes)} codes")
        else:
            # Ensure billing_codes is always present (might be populated from nested procedures above)
            if "billing_codes" not in normalized:
                normalized["billing_codes"] = result.get("billing_codes", [])
                logger.debug(f"🔧 USING existing billing_codes: {len(normalized['billing_codes'])} codes")
        
        # Copy other fields
        for key, value in result.items():
            if key not in ["treatment_summary", "billing_entries"]:
                normalized[key] = value
        
        return normalized

    def _get_system_prompt(self) -> str:
        """Delegate to the static method from LLMProcedureExtractor"""
        return LLMProcedureExtractor._get_system_prompt()
    
    def _create_extraction_prompt(self, text: str, bema_goz_catalog: dict, findings_context: str, insurance_type: str = "bema") -> str:
        # Use the same prompt as OpenAI for now
        return self._get_system_prompt() + f"\n\nBEHANDLUNGSTEXT:\n{text}\n\nBEFUNDE:\n{findings_context}\n"


class LLMProcedureExtractor:
    """Extract dental procedures and billing codes using GPT-4o for excellent accuracy"""
    
    def __init__(self):
        from app.core.config import settings
        self.model = settings.LLM_MODEL  # Force use settings model (no fallback)
        self.temperature = settings.LLM_TEMPERATURE
        self.max_completion_tokens = settings.LLM_MAX_TOKENS
        
        # RAG temporarily disabled for simplification  
        # self.rag_retriever = DentalCodeRetriever()
        
        # Log actual model being used
        logger.info(f"🤖 LLM Model initialized: {self.model}")
        logger.info(f"🤖 Settings LLM_MODEL: {settings.LLM_MODEL}")
        # logger.info(f"🔍 RAG retriever initialized with {self.rag_retriever.get_catalog_info()}")
        
        # Validate model availability
        self._validate_model_selection()
        
    def _validate_model_selection(self):
        """Validate that the selected model is available and optimal for the task"""
        valid_models = {
            "gemini-3-flash-preview": {"reasoning": "excellent", "cost": "low", "speed": "very fast", "availability": "public"},
            "gemini-3-pro-preview": {"reasoning": "best", "cost": "medium", "speed": "fast", "availability": "public"},
            "gemini-2.5-pro": {"reasoning": "excellent", "cost": "low", "speed": "fast", "availability": "deprecated March 2026"},
        }
        
        if self.model not in valid_models:
            logger.warning(f"🚨 Model {self.model} not in validated list. Using anyway but results may vary.")
        else:
            model_info = valid_models[self.model]
            logger.info(f"✅ Using validated model {self.model}: {model_info}")
        
        # Force log current model for debugging
        logger.info(f"🎯 FINAL MODEL BEING USED: {self.model}")
        
        if self.model in valid_models:
            model_info = valid_models[self.model]
            logger.info(f"Using LLM model: {self.model}", 
                       reasoning_quality=model_info["reasoning"],
                       cost_tier=model_info["cost"],
                       speed_tier=model_info["speed"],
                       availability=model_info["availability"])
            
            # Inform about access requirements
            if model_info["availability"] == "limited_preview":
                logger.warning(f"⚠️  {self.model} requires OpenAI waitlist approval for access")
            elif model_info["availability"] == "research_preview":
                logger.warning(f"⚠️  {self.model} only available for approved research projects")
            
            # Recommend best available option
            if self.model not in ["o3-mini", "o3", "gpt-4o"]:
                logger.info("💡 Tip: Use 'gpt-4o' for excellent medical reasoning, or 'o3' if organization is verified")
        
    async def extract_procedures_and_codes(
        self, 
        text: str, 
        bema_goz_catalog: dict,
        findings: List[DentalFinding] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to extract procedures and suggest BEMA/GOZ codes
        
        Args:
            text: Normalized dental documentation text
            bema_goz_catalog: Complete BEMA/GOZ code database
            findings: Previously extracted dental findings for context
            
        Returns:
            Dict with extracted procedures, billing codes, and confidence scores
        """
        if not self.api_key:
            raise LLMExtractionError("OpenAI API key not configured")
        
        start_time = time.time()
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            # Prepare context from findings
            findings_context = ""
            if findings:
                findings_context = "\n".join([
                    f"- Zahn {f.tooth_number}: {f.diagnosis}" + 
                    (f" ({f.surface})" if f.surface else "")
                    for f in findings
                ])
            
            # Create the prompt with BEMA/GOZ catalog
            prompt = self._create_extraction_prompt(text, bema_goz_catalog, findings_context)
            
            logger.info("Starting LLM procedure extraction", 
                       text_length=len(text),
                       model=self.model)
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"},  # Force JSON output
                "max_completion_tokens": self.max_completion_tokens
            }
            
            # Only add temperature for models that support it (exclude O3 models)
            if not self.model.startswith("o3"):
                api_params["temperature"] = self.temperature
            
            # Call LLM with structured output
            response = client.chat.completions.create(**api_params)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Parse the response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Validate and enhance the result
            validated_result = self._validate_and_enhance_result(result, bema_goz_catalog)
            
            logger.info("LLM procedure extraction completed",
                       procedures_found=len(validated_result.get("procedures", [])),
                       billing_codes_found=len(validated_result.get("billing_codes", [])),
                       processing_time_ms=processing_time)
            
            return validated_result
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response", error=str(e))
            raise LLMExtractionError(f"Invalid JSON response from LLM: {str(e)}")
        except Exception as e:
            logger.error("LLM procedure extraction failed", error=str(e))
            raise LLMExtractionError(f"LLM processing error: {str(e)}")
    
    @staticmethod
    def _get_system_prompt() -> str:
        """Comprehensive dental billing expert system prompt"""
        return """Du bist ein erfahrener Zahnarzt-Abrechnungsexperte mit umfassenden Kenntnissen der BEMA- und GOZ-Gebührenordnung.

Deine Aufgabe: Analysiere zahnmedizinische Behandlungsdokumentation und erstelle eine vollständige Abrechnung im JSON-Format.

REGELN:
1. Extrahiere ALLE durchgeführten Behandlungen aus dem Text
2. Ordne jeder Behandlung die korrekten Abrechnungsziffern zu
3. Gib Zahnnummern im FDI-Schema an (z.B. 36, 14, 21)
4. Gib Flächen an wo relevant (z.B. MOD, OB, MB)
5. Bei mehreren Zähnen: separate Einträge pro Zahn

Antworte IMMER als JSON-Objekt mit dieser Struktur:
{
  "procedures": [
    {
      "procedure_name": "Name der Behandlung",
      "tooth_number": "Zahnnummer oder null",
      "surfaces": "Flächen oder null",
      "description": "Kurzbeschreibung"
    }
  ],
  "billing_codes": [
    {
      "code": "Abrechnungsziffer (z.B. 13a, Oe1, 2080)",
      "system": "BEMA oder GOZ",
      "description": "Leistungsbeschreibung",
      "tooth_number": "Zahnnummer oder null",
      "quantity": 1,
      "is_zusatzleistung": false
    }
  ]
}

Häufige BEMA-Ziffern: 01 (Untersuchung), 04 (Vitalitätsprüfung), 8 (Sensibilitätsprüfung), Ä925 (Röntgen-Zahnfilm), Ä935a (OPG), IP1-IP4 (Prophylaxe), 13a-13e (Füllungen 1-5-flächig), Oe1/Oe2 (Panorama/Fernröntgen), 47a/47b (Extraktion), cp (Chirurgische Maßnahmen), X1-X3 (Anästhesie).

Häufige GOZ-Ziffern: 0010 (Untersuchung), 2060-2120 (Füllungen), 2080 (Kompositfüllung), 2197 (Adhäsive Befestigung), 1040 (PZR), 3010-3040 (Chirurgie), 5000-5260 (Prothetik), Ä5004 (Röntgen Zahnfilm), Ä5370 (OPG)."""
    
    def _create_extraction_prompt(self, text: str, bema_goz_catalog: dict, findings_context: str, insurance_type: str = "bema") -> str:
        """Direct voice text to Gemini - no extra processing"""
        
        logger.info(f"🎤 Sending direct voice input to Gemini")
        
        # Just the voice text - nothing else!
        return text
    
    def _get_key_codes_for_prompt(self, bema_goz_catalog: dict) -> dict:
        """Extract the most important BEMA/GOZ codes for the prompt"""
        
        # Most common dental procedures
        important_categories = [
            "Füllungstherapie", "Anästhesie", "Chirurgie", "Endodontie", 
            "Diagnostik", "Prophylaxe", "Prothetik"
        ]
        
        key_codes = {"bema": {}, "goz": {}}
        
        # Get key BEMA codes
        for code_id, code_info in bema_goz_catalog.get("bema_codes", {}).items():
            if code_info.get("category") in important_categories:
                key_codes["bema"][code_id] = {
                    "code": code_info["code"],
                    "description": code_info["description"],
                    "points": code_info["points"],
                    "category": code_info.get("category"),
                    "keywords": code_info.get("keywords", [])
                }
        
        # Get key GOZ codes  
        for code_id, code_info in bema_goz_catalog.get("goz_codes", {}).items():
            if code_info.get("category") in important_categories:
                key_codes["goz"][code_id] = {
                    "code": code_info["code"],
                    "description": code_info["description"],
                    "points": code_info["points"],
                    "standard_factor": code_info.get("standard_factor"),
                    "category": code_info.get("category"),
                    "keywords": code_info.get("keywords", [])
                }
        
        return key_codes
    
    def _validate_and_enhance_result(self, result: dict, bema_goz_catalog: dict) -> dict:
        """Validate and enhance the LLM result"""
        
        validated_result = {
            "procedures": [],
            "billing_codes": [],
            "reasoning": result.get("reasoning", ""),
            "confidence_overall": result.get("confidence_overall", 0.5),
            "llm_processing": True
        }
        
        # Validate procedures
        for proc in result.get("procedures", []):
            if self._validate_procedure(proc):
                validated_result["procedures"].append(proc)
        
        # Validate and enhance billing codes
        for code in result.get("billing_codes", []):
            enhanced_code = self._enhance_billing_code(code, bema_goz_catalog)
            if enhanced_code:
                validated_result["billing_codes"].append(enhanced_code)
        
        return validated_result
    
    def _validate_procedure(self, procedure: dict) -> bool:
        """Validate a procedure extraction"""
        required_fields = ["name", "confidence"]
        return all(field in procedure for field in required_fields)
    
    def _enhance_billing_code(self, code: dict, bema_goz_catalog: dict) -> Optional[dict]:
        """Enhance billing code with actual catalog data"""
        
        code_id = code.get("code", "").replace("BEMA ", "").replace("GOZ ", "")
        system = code.get("system", "").lower()
        
        # Look up in catalog
        catalog_key = f"{system}_codes"
        if catalog_key in bema_goz_catalog and code_id in bema_goz_catalog[catalog_key]:
            catalog_info = bema_goz_catalog[catalog_key][code_id]
            
            # No fee calculations - dentists set their own prices
            
            return {
                "code": catalog_info["code"],
                "system": system,
                "description": catalog_info["description"],
                "points": catalog_info["points"],
                "factor": catalog_info.get("standard_factor") if system == "goz" else None,
                "confidence": min(code.get("confidence", 0.5), 0.95),  # Cap LLM confidence
                "reasoning": code.get("reasoning", ""),
                "llm_extracted": True
            }
        
        return None


# Provider switch logic
class ProviderSwitchLLMExtractor:
    def __init__(self):
        from app.core.config import settings
        self.provider = settings.LLM_PROVIDER.lower()
        
        # 🔍 CRITICAL DEBUG: Log provider selection
        logger.info(f"🔧 settings.LLM_PROVIDER: '{settings.LLM_PROVIDER}'")
        logger.info(f"🔧 self.provider (lowercased): '{self.provider}'")
        
        if self.provider == "google":
            self.extractor = GeminiLLMProcedureExtractor()
            logger.info(f"✅ Using Google Gemini as LLM provider: {self.extractor.model}")
            logger.info(f"✅ Gemini API URL: {self.extractor.api_url}")
        else:
            self.extractor = LLMProcedureExtractor()
            logger.error("❌ 🔄 Using OpenAI GPT-4o as LLM provider")
            logger.error(f"❌ OpenAI model: {self.extractor.model}")
            logger.error("❌ This should be Gemini! Check LLM_PROVIDER setting!")

    async def extract_procedures_and_codes(self, *args, **kwargs):
        return await self.extractor.extract_procedures_and_codes(*args, **kwargs)

    # Delegate all attributes and methods to the underlying extractor
    def __getattr__(self, name):
        return getattr(self.extractor, name)


class EnhancedDocumentationProcessor:
    """Enhanced processor that combines traditional and LLM-based extraction"""
    
    def __init__(self):
        self.llm_extractor = ProviderSwitchLLMExtractor()
        self.use_llm = True
        
    async def extract_procedures_intelligent(
        self, 
        text: str, 
        bema_goz_catalog: dict, 
        findings: List = None,
        insurance_type: str = "bema",
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract procedures and billing codes using O3 with insurance type awareness
        """
        
        if not self.use_llm or not self.llm_extractor:
            raise LLMExtractionError("LLM extraction not enabled or configured")
        
        start_time = time.time()
        
        try:
            # Create findings context
            findings_context = "Keine spezifischen Befunde dokumentiert"
            if findings:
                findings_list = []
                for finding in findings:
                    if hasattr(finding, 'diagnosis'):
                        tooth_info = f"Zahn {finding.tooth_number}" if hasattr(finding, 'tooth_number') and finding.tooth_number else ""
                        surface_info = f" {finding.surface}" if hasattr(finding, 'surface') and finding.surface else ""
                        findings_list.append(f"{tooth_info}{surface_info}: {finding.diagnosis}")
                    else:
                        findings_list.append(str(finding))
                findings_context = "\n".join(findings_list)
            
            logger.info(f"LLM extraction starting with {self.llm_extractor.model}, insurance_type: {insurance_type}")
            logger.info(f"🚀 Using provider: {type(self.llm_extractor).__name__}")
            logger.info(f"🔧 Underlying extractor: {type(self.llm_extractor.extractor).__name__}")
            logger.info(f"🔧 Provider setting: {self.llm_extractor.provider}")
            
            # 🔍 CRITICAL DEBUG: Verify Gemini is being used
            if type(self.llm_extractor.extractor).__name__ == "GeminiLLMProcedureExtractor":
                logger.info("✅ Confirmed: Using Gemini 2.5 Pro")
            else:
                logger.error(f"❌ WRONG PROVIDER: Expected GeminiLLMProcedureExtractor, got {type(self.llm_extractor.extractor).__name__}")
            
            # Delegate to the appropriate extractor (OpenAI or Gemini)
            result = await self.llm_extractor.extract_procedures_and_codes(
                text=text,
                bema_goz_catalog=bema_goz_catalog,
                findings=findings,
                insurance_type=insurance_type
            )
            
            # Debug: Log what we actually got back
            logger.info(f"🔍 LLM result keys: {list(result.keys())}")
            logger.info(f"🔍 Result type: {type(result)}")
            if "raw_gemini_response" in result:
                logger.info(f"🎯 Gemini raw response length: {len(result['raw_gemini_response'])}")
                logger.info(f"🎯 Gemini raw response start: {result['raw_gemini_response'][:200]}...")
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Log the extraction result
            logger.info(f"🎉 {type(self.llm_extractor).__name__} extraction completed", 
                       processing_time_ms=processing_time,
                       result_type=type(result).__name__)
            
            # Validate result structure
            if not isinstance(result, dict):
                logger.error(f"Expected dict but got {type(result)}: {result}")
                raise ValueError(f"LLM returned {type(result)} instead of dict")
                
            # Log result summary - prioritize raw response over structured data
            raw_response = result.get("raw_gemini_response", "")
            if raw_response:
                logger.info(f"✅ Raw Gemini response received: {len(raw_response)} chars")
                logger.info(f"🎯 Raw response preview: {raw_response[:100]}...")
            else:
                # Only check for structured fields if no raw response available
                if "billing_codes" in result:
                    billing_codes = result["billing_codes"]
                    logger.info(f"Found billing_codes: {len(billing_codes) if isinstance(billing_codes, list) else 'not a list'} items")
                else:
                    logger.info("No structured billing_codes (raw response expected)")
                    
                if "procedures" in result:
                    procedures = result["procedures"]
                    logger.info(f"Found procedures: {len(procedures) if isinstance(procedures, list) else 'not a list'} items")
                else:
                    logger.info("No structured procedures (raw response expected)")
            
            # Validate and enhance the result
            validated_result = self._validate_and_enhance_result(result, bema_goz_catalog)
            
            logger.info("LLM procedure extraction completed",
                       procedures_found=len(validated_result.get("procedures", [])),
                       billing_codes_found=len(validated_result.get("billing_codes", [])),
                       processing_time_ms=processing_time)
            
            return validated_result
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response", error=str(e))
            raise LLMExtractionError(f"Invalid JSON response from LLM: {str(e)}")
        except Exception as e:
            logger.error("LLM procedure extraction failed", error=str(e))
            raise LLMExtractionError(f"LLM processing error: {str(e)}")
    
    def _format_codes_for_prompt(self, relevant_codes: List[Dict]) -> str:
        """Format retrieved codes for inclusion in LLM prompt"""
        if not relevant_codes:
            return "Keine spezifischen Codes gefunden - verwende Standard-Mapping."
        
        formatted_sections = {
            "BEMA (Kassencodes)": [],
            "GOZ (Privatcodes)": [],
            "GOÄ (Ärztliche Codes)": []
        }
        
        for code_info in relevant_codes:
            system = code_info.get("system", "").upper()
            code = code_info.get("code", "")
            description = code_info.get("description", "")
            points = code_info.get("points", 0)
            factor = code_info.get("factor", "") or code_info.get("standard_factor", "")
            relevance = code_info.get("relevance_score", 0)
            reason = code_info.get("retrieval_reason", "")
            
            # Format code entry
            if system == "BEMA":
                entry = f"- {code}: {description} ({points} Punkte) [Relevanz: {relevance:.1%}]"
                formatted_sections["BEMA (Kassencodes)"].append(entry)
            elif system == "GOZ":
                factor_text = f", Faktor {factor}" if factor else ""
                entry = f"- {code}: {description} ({points} Punkte{factor_text}) [Relevanz: {relevance:.1%}]"
                formatted_sections["GOZ (Privatcodes)"].append(entry)
            elif system == "GOAE":
                factor_text = f", Faktor {factor}" if factor else ""
                entry = f"- {code}: {description} (Faktor {factor_text}) [Relevanz: {relevance:.1%}]"
                formatted_sections["GOÄ (Ärztliche Codes)"].append(entry)
        
        # Build final formatted text
        formatted_text = []
        for section_name, entries in formatted_sections.items():
            if entries:
                formatted_text.append(f"\n{section_name}:")
                formatted_text.extend(entries)
        
        return "\n".join(formatted_text) if formatted_text else "Keine relevanten Codes gefunden."
    
    def _traditional_extraction(self, text: str, bema_goz_catalog: dict) -> Dict[str, Any]:
        """Traditional keyword-based extraction as fallback"""
        # Import the traditional terminology
        from app.services.documentation_processor import GermanDentalTerminology
        
        terminology = GermanDentalTerminology()
        procedures = []
        
        # Simple keyword matching (existing logic)
        for procedure_key, procedure_name in terminology.PROCEDURES.items():
            if procedure_key in text.lower():
                procedures.append({
                    "name": procedure_name,
                    "description": f"Detected via keyword: {procedure_key}",
                    "confidence": 0.7  # Lower confidence for keyword matching
                })
        
        return {
            "procedures": procedures,
            "billing_codes": [],  # Would need traditional mapping
            "reasoning": "Traditional keyword-based extraction",
            "confidence_overall": 0.6,
            "extraction_method": "traditional_fallback",
            "llm_processing": False
        } 

    def _validate_and_enhance_result(self, result: Dict[str, Any], bema_goz_catalog: dict) -> Dict[str, Any]:
        """Validate and enhance the LLM result"""
        
        logger.info(f"Validating LLM result: {type(result)}")
        
        # Handle case where result might not be a dict
        if not isinstance(result, dict):
            logger.error(f"Expected dict but got {type(result)}: {result}")
            return {
                "procedures": [],
                "billing_codes": [],
                "confidence_overall": 0.0,
                "extraction_method": "o3_direct",
                "error": f"Invalid result type: {type(result)}",
                "raw_gemini_response": None  # Can't preserve if not a dict
            }
        
        # Ensure required fields exist with safe access
        try:
            procedures = result.get("procedures", [])
            billing_codes = result.get("billing_codes", [])
            confidence = result.get("confidence_overall", 0.8)
            
            logger.info(f"Raw procedures: {type(procedures)} = {procedures}")
            logger.info(f"Raw billing_codes: {type(billing_codes)} = {billing_codes}")
            
            # Ensure procedures is a list
            if not isinstance(procedures, list):
                logger.warning(f"Procedures is not a list: {type(procedures)}")
                procedures = []
            
            # Ensure billing_codes is a list
            if not isinstance(billing_codes, list):
                logger.warning(f"Billing codes is not a list: {type(billing_codes)}")
                billing_codes = []
            
            validated_result = {
                "procedures": procedures,
                "billing_codes": billing_codes,
                "confidence_overall": confidence,
                "extraction_method": "o3_direct"
            }
            
            # Validate billing codes format safely
            validated_codes = []
            for i, code in enumerate(billing_codes):
                try:
                    logger.info(f"Validating billing code {i}: {type(code)}")
                    
                    if isinstance(code, dict):
                        # Check if code has basic required fields (from Gemini extraction)
                        if "code" in code and "description" in code:
                            # Use Gemini format and add missing fields
                            normalized_code = code.copy()
                            # Add type field if missing (infer from fee_schedule)
                            if "type" not in normalized_code:
                                normalized_code["type"] = normalized_code.get("fee_schedule", "bema").lower()
                            logger.info(f"Using Gemini code {i}: {normalized_code}")
                        else:
                            # Convert German field names to English (traditional extraction)
                            normalized_code = self._normalize_german_billing_code(code)
                            logger.info(f"German-normalized code {i}: {normalized_code}")
                        
                        if normalized_code.get("code"):
                            # Ensure required fields with safe defaults
                            validated_code = {
                                "code": normalized_code.get("code", ""),
                                "description": normalized_code.get("description", ""),
                                "type": normalized_code.get("type", "bema"),
                                "points": normalized_code.get("points", 0),
                                "quantity": normalized_code.get("quantity", 1),
                                "tooth_number": normalized_code.get("tooth_number", ""),
                                "note": normalized_code.get("note", ""),
                                "factor": normalized_code.get("factor", 1.0)
                            }
                            validated_codes.append(validated_code)
                            logger.info(f"✅ Successfully validated billing code {i}: {validated_code['code']}")
                        else:
                            logger.warning(f"❌ No valid code found in {i}: {code}")
                    else:
                        logger.warning(f"❌ Invalid billing code {i}: {type(code)} = {code}")
                        
                except Exception as e:
                    logger.error(f"Error validating billing code {i}: {e}")
                    logger.error(f"Code data: {code}")
                    continue
            
            validated_result["billing_codes"] = validated_codes
            logger.info(f"Validation complete: {len(validated_codes)} billing codes validated")
            
            # CRITICAL: Preserve raw_gemini_response!
            if "raw_gemini_response" in result:
                validated_result["raw_gemini_response"] = result["raw_gemini_response"]
                logger.info(f"✅ Preserving raw_gemini_response: {len(result['raw_gemini_response'])} chars")
            
            return validated_result
            
        except Exception as e:
            logger.error(f"Error in validation process: {e}")
            logger.error(f"Input result: {result}")
            return {
                "procedures": [],
                "billing_codes": [],
                "confidence_overall": 0.0,
                "extraction_method": "o3_direct",
                "error": f"Validation failed: {str(e)}",
                "raw_gemini_response": result.get("raw_gemini_response")  # PRESERVE EVEN ON ERROR!
            }
    
    def _normalize_german_billing_code(self, code: dict) -> dict:
        """Normalisiert die Feldnamen für konsistente interne Verarbeitung
        
        Wir behalten die deutschen Feldnamen bei, da dies natürlicher für die Anwendung ist.
        Die Normalisierung ist trotzdem nötig um verschiedene Schreibweisen zu vereinheitlichen.
        """
        
        # Mapping verschiedener deutscher Schreibweisen auf einheitliche Feldnamen
        field_mapping = {
            "bema_position": "position",
            "goz_position": "position",
            "kurzbezeichnung": "position",
            "position": "position",
            "code": "position",
            
            "beschreibung": "beschreibung", 
            "bezeichnung": "beschreibung",
            "description": "beschreibung",
            
            "anzahl": "anzahl",
            "menge": "anzahl",
            "quantity": "anzahl",
            
            "zahn_region": "zahn",
            "zahn": "zahn", 
            "zahnbereich": "zahn",
            "tooth_number": "zahn",
            
            "punkte": "punkte",
            "punktwert": "punkte",
            "points": "punkte",
            
            "faktor": "faktor",
            "factor": "faktor",
            
            "anmerkung": "anmerkung",
            "bemerkung": "anmerkung", 
            "hinweis": "anmerkung",
            "note": "anmerkung"
        }
        
        normalized = {}
        
        # Convert all fields using mapping
        for german_key, english_key in field_mapping.items():
            if german_key in code:
                value = code[german_key]
                
                # Special handling for tooth regions (convert list to single tooth)
                if english_key == "tooth_number" and isinstance(value, list) and value:
                    normalized[english_key] = str(value[0])  # Take first tooth
                elif english_key == "tooth_number" and value:
                    normalized[english_key] = str(value)
                else:
                    normalized[english_key] = value
        
        # Determine billing type from code prefix
        code_value = normalized.get("code", "")
        if code_value:
            if code_value.startswith(("GOZ", "2", "3", "4", "5", "6", "7", "8", "9")):
                normalized["type"] = "goz"
            elif code_value.startswith(("Ä", "A")):
                normalized["type"] = "goä"
            else:
                normalized["type"] = "bema"
        
        logger.info(f"🔄 German→English: {code} → {normalized}")
        return normalized 