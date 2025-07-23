"""
Enhanced LLM Processor Service
Uses OpenAI's advanced models for intelligent procedure and billing code extraction
"""

import json
import time
from typing import Dict, Any, List, Optional
import structlog

from app.core.config import settings
from app.schemas.dental_documentation import DentalFinding, BillingCode, BillingSystem, ConfidenceLevel
from app.utils.llm_logger import llm_logger

logger = structlog.get_logger()


class LLMExtractionError(Exception):
    """Custom exception for LLM extraction errors"""
    pass


class LLMProcedureExtractor:
    """Extract dental procedures and billing codes using GPT-4o for proven accuracy"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL or "gpt-4o-2024-11-20"  # Default to stable GPT-4o
        self.temperature = settings.LLM_TEMPERATURE
        self.max_completion_tokens = settings.LLM_MAX_TOKENS  # Updated for newer models
        
        # Validate model availability
        self._validate_model_selection()
        
    def _validate_model_selection(self):
        """Validate that the selected model is available and optimal for the task"""
        valid_models = {
            # Generally Available
            "gpt-4o": {"reasoning": "excellent", "cost": "medium", "speed": "fast", "availability": "public"},
            "gpt-4-turbo": {"reasoning": "very good", "cost": "medium", "speed": "fast", "availability": "public"},
            "gpt-4": {"reasoning": "good", "cost": "medium", "speed": "slow", "availability": "public"},
            # Limited Access (waitlist required)
            "o3-mini": {"reasoning": "superior", "cost": "low", "speed": "fast", "availability": "limited_preview"},
            "o3": {"reasoning": "outstanding", "cost": "very_high", "speed": "slow", "availability": "research_preview"}
        }
        
        if self.model not in valid_models:
            logger.warning(f"Model {self.model} not in validated list. Using anyway but results may vary.")
        else:
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
                logger.info("💡 Tip: Consider 'gpt-4o' for excellent medical reasoning with public access")
        
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
    
    def _get_system_prompt(self) -> str:
        """O3-optimized system prompt for German dental billing extraction"""
        return """Du bist ein hochspezialisierter deutscher Zahnarzt-Abrechnungsexperte mit umfassendem Wissen über BEMA und GOZ.

AUFGABE: Analysiere Behandlungsdokumentationen und erstelle präzise BEMA/GOZ-Abrechnungen.

WICHTIGE ABRECHNUNGSLOGIK:

🏥 BEMA-PATIENT (Kassenpatient):
- PRIMÄR: BEMA-Leistungen abrechnen (Kassensachleistungen)  
- ZUSÄTZLICH: GOZ-Leistungen mit Mehrkostenvereinbarung (MKV) möglich
- Bei GOZ-Leistungen: "note": "MKV" hinzufügen

💰 GOZ-PATIENT (Privatpatient):
- NUR GOZ-Leistungen abrechnen
- KEINE BEMA-Leistungen

HÄUFIGE DEUTSCHE ZAHNMEDIZINISCHE BEGRIFFE:
- Karies → BEMA 13a/b/c (je nach Flächen) oder GOZ 2080-2100
- Lokalanästhesie → BEMA L1 oder GOZ 0080
- Röntgen → BEMA Ä 925a oder GOZ Rö2
- Untersuchung → BEMA 01 oder GOZ I
- Füllung → BEMA 13 oder GOZ 2080-2197
- Extraktion → BEMA X1/X2 oder GOZ 3000

AUSGABEFORMAT (JSON):
{
  "procedures": ["Lokalanästhesie", "Kompositfüllung", "Röntgenaufnahme"],
  "billing_codes": [
    {
      "code": "BEMA_01",
      "description": "Untersuchung", 
      "type": "bema",
      "points": 18,
      "fee": "23.61 €"
    },
    {
      "code": "GOZ_2197",
      "description": "Adhäsive Technik",
      "type": "goz", 
      "points": 130,
      "fee": "22.73 €",
      "note": "MKV"
    }
  ],
  "confidence_overall": 0.9
}

QUALITÄTSANFORDERUNGEN:
- Extrahiere ALLE relevanten Behandlungen
- Verwende korrekte deutsche BEMA/GOZ-Codes  
- Berechne realistische Honorare
- Berücksichtige Versicherungstyp (BEMA vs GOZ)"""
    
    def _create_extraction_prompt(self, text: str, bema_goz_catalog: dict, findings_context: str, insurance_type: str = "bema") -> str:
        """Create extraction prompt with insurance type context"""
        
        # Insurance-specific instruction
        if insurance_type.lower() == "bema":
            insurance_instruction = """
🏥 KASSENPATIENT (BEMA):
- Rechne PRIMÄR alle Standard-Leistungen nach BEMA ab
- Hochwertige Zusatzleistungen (Komposit, Adhäsive, etc.) als GOZ mit MKV
- Beispiel: BEMA 13c + GOZ 2197 (MKV - Adhäsive Technik)"""
        else:
            insurance_instruction = """
💰 PRIVATPATIENT (GOZ):
- Rechne ALLE Leistungen ausschließlich nach GOZ ab
- KEINE BEMA-Codes verwenden
- Vollständige Privatabrechnung"""
        
        return f"""
BEHANDLUNGSTEXT:
{text}

BEFUNDE:
{findings_context}

VERSICHERUNGSTYP: {insurance_type.upper()}
{insurance_instruction}

Analysiere den Text und erstelle eine vollständige Abrechnung nach den oben genannten Regeln.
Antworte im JSON-Format wie im System-Prompt beschrieben."""
    
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
            
            # Calculate fees
            if system == "bema":
                point_value = bema_goz_catalog["meta"]["bema_point_value"]
                fee_euros = round(catalog_info["points"] * point_value, 2)
            else:  # GOZ
                point_value = bema_goz_catalog["meta"]["goz_point_value"]
                factor = catalog_info.get("standard_factor", 2.3)
                fee_euros = round(catalog_info["points"] * point_value * factor, 2)
            
            return {
                "code": catalog_info["code"],
                "system": system,
                "description": catalog_info["description"],
                "points": catalog_info["points"],
                "fee_euros": fee_euros,
                "factor": catalog_info.get("standard_factor") if system == "goz" else None,
                "confidence": min(code.get("confidence", 0.5), 0.95),  # Cap LLM confidence
                "reasoning": code.get("reasoning", ""),
                "llm_extracted": True
            }
        
        return None


class EnhancedDocumentationProcessor:
    """Enhanced processor that combines traditional and LLM-based extraction"""
    
    def __init__(self):
        self.llm_extractor = LLMProcedureExtractor() if settings.USE_LLM_EXTRACTION else None
        self.use_llm = settings.USE_LLM_EXTRACTION and settings.OPENAI_API_KEY is not None
        
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
            import openai
            client = openai.OpenAI(api_key=self.llm_extractor.api_key)
            
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
            
            logger.info(f"LLM extraction starting with O3-mini, insurance_type: {insurance_type}")
            
            # Create extraction query with insurance type
            query = self.llm_extractor._create_extraction_prompt(text, bema_goz_catalog, findings_context, insurance_type)
            system_prompt = self.llm_extractor._get_system_prompt()
            
            logger.info(f"Sending prompt to O3-mini (model: {self.llm_extractor.model})")
            
            # Prepare API call parameters
            api_params = {
                "model": self.llm_extractor.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": query
                    }
                ],
                "response_format": {"type": "json_object"},  # Force JSON output
                "max_completion_tokens": self.llm_extractor.max_completion_tokens
            }
            
            # Only add temperature for models that support it (exclude O3 models)
            if not self.llm_extractor.model.startswith("o3"):
                api_params["temperature"] = self.llm_extractor.temperature
            
            # Call O3-mini for dental analysis
            response = client.chat.completions.create(**api_params)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Parse the response
            result_text = response.choices[0].message.content
            
            # Log the complete LLM interaction
            llm_logger.log_interaction(
                model=self.llm_extractor.model,
                system_prompt=system_prompt,
                user_prompt=query,
                response=result_text,
                insurance_type=insurance_type,
                patient_id=patient_id,
                processing_time_ms=processing_time,
                metadata={
                    "temperature": self.llm_extractor.temperature,
                    "max_completion_tokens": self.llm_extractor.max_completion_tokens,
                    "findings_count": len(findings) if findings else 0,
                    "text_length": len(text)
                }
            )
            
            # Parse and validate JSON response
            try:
                logger.info(f"Parsing O3 response (length: {len(result_text)})")
                logger.info(f"Raw O3 response: {result_text[:500]}...")  # First 500 chars
                
                result = json.loads(result_text)
                logger.info(f"JSON parsing successful, type: {type(result)}")
                logger.info(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                
                # Validate that result is a dictionary
                if not isinstance(result, dict):
                    logger.error(f"Expected dict but got {type(result)}: {result}")
                    raise ValueError(f"LLM returned {type(result)} instead of dict")
                
                # Check for required fields
                if "billing_codes" in result:
                    billing_codes = result["billing_codes"]
                    logger.info(f"Found billing_codes: {type(billing_codes)} with {len(billing_codes) if isinstance(billing_codes, list) else 'not a list'} items")
                    if isinstance(billing_codes, list) and billing_codes:
                        logger.info(f"First billing code: {type(billing_codes[0])} = {billing_codes[0]}")
                else:
                    logger.warning("No 'billing_codes' field in O3 response")
                    
                if "procedures" in result:
                    procedures = result["procedures"]
                    logger.info(f"Found procedures: {type(procedures)} = {procedures}")
                else:
                    logger.warning("No 'procedures' field in O3 response")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                logger.error(f"Raw response: {result_text}")
                # Return a safe fallback
                result = {
                    "procedures": [],
                    "billing_codes": [],
                    "confidence_overall": 0.0,
                    "error": f"JSON parsing failed: {str(e)}"
                }
            except Exception as e:
                logger.error(f"Response processing failed: {e}")
                logger.error(f"Raw response: {result_text}")
                # Return a safe fallback
                result = {
                    "procedures": [],
                    "billing_codes": [],
                    "confidence_overall": 0.0,
                    "error": f"Response processing failed: {str(e)}"
                }
            
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
                "error": f"Invalid result type: {type(result)}"
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
                    
                    if isinstance(code, dict) and "code" in code:
                        # Ensure required fields with safe defaults
                        validated_code = {
                            "code": code.get("code", ""),
                            "description": code.get("description", ""),
                            "type": code.get("type", "unknown"),
                            "points": code.get("points", 0),
                            "fee": code.get("fee", "0.00 €"),
                            "note": code.get("note", ""),
                            "factor": code.get("factor", 1.0)
                        }
                        validated_codes.append(validated_code)
                        logger.info(f"Successfully validated billing code {i}")
                    else:
                        logger.warning(f"Invalid billing code {i}: {type(code)} = {code}")
                        
                except Exception as e:
                    logger.error(f"Error validating billing code {i}: {e}")
                    logger.error(f"Code data: {code}")
                    continue
            
            validated_result["billing_codes"] = validated_codes
            logger.info(f"Validation complete: {len(validated_codes)} billing codes validated")
            
            return validated_result
            
        except Exception as e:
            logger.error(f"Error in validation process: {e}")
            logger.error(f"Input result: {result}")
            return {
                "procedures": [],
                "billing_codes": [],
                "confidence_overall": 0.0,
                "extraction_method": "o3_direct",
                "error": f"Validation failed: {str(e)}"
            } 