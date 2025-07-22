"""
LLM-Enhanced Procedure Extraction Service
Uses OpenAI GPT-4 to intelligently extract dental procedures and map them to BEMA/GOZ codes
"""

import json
import time
from typing import List, Dict, Optional, Any
import structlog

from app.core.config import settings
from app.schemas.dental_documentation import DentalFinding, BillingCode, BillingSystem, ConfidenceLevel

logger = structlog.get_logger()


class LLMExtractionError(Exception):
    """Custom exception for LLM extraction errors"""
    pass


class LLMProcedureExtractor:
    """OpenAI o3/GPT-4 based procedure extraction with configurable models"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL  # Configurable: o3-mini, o3, gpt-4o, etc.
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        
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
            
            # Call LLM with structured output
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},  # Force JSON output
                max_tokens=self.max_tokens
            )
            
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
        """System prompt for the dental procedure extraction AI"""
        return """Du bist ein Experte für deutsche Zahnmedizin und Abrechnung mit fortgeschrittenen Reasoning-Fähigkeiten. 

Deine Aufgabe:
1. Analysiere deutschen zahnärztlichen Text mit tiefem Verständnis
2. Erkenne alle durchgeführten Behandlungen/Prozeduren durch kontextuelle Analyse
3. Ordne passende BEMA/GOZ-Abrechnungsziffern zu basierend auf komplexem medizinischen Reasoning
4. Berücksichtige medizinische Zusammenhänge, Synonyme und komplexe klinische Beschreibungen

Erweiterte Fähigkeiten:
- Erkenne implizite Behandlungen (z.B. "Schmerzen gelindert" → Anästhesie wahrscheinlich)
- Verstehe kausale Ketten ("starke Karies → Schmerzen → Anästhesie → Entfernung → Versorgung")
- Berücksichtige anatomische Details (Zahntyp, Wurzelanzahl, Schwierigkeit)
- Bewerte Behandlungskomplexität für akkurate Faktor-Auswahl bei GOZ

Wichtige Regeln:
- Erkenne auch umgangssprachliche Formulierungen ("Zahn ziehen" = Extraktion)
- Berücksichtige Flächenanzahl bei Füllungen (1-4 Flächen)
- Unterscheide zwischen einwurzeligen und mehrwurzeligen Zähnen
- Priorisiere GOZ bei privaten Leistungen, BEMA bei Kassenleistungen
- Gib Konfidenzwerte für jede Zuordnung an (0.0-1.0)
- Begründe komplexe Entscheidungen ausführlich

Antworte IMMER im folgenden JSON-Format:
{
    "procedures": [
        {
            "name": "Genaue Bezeichnung der Prozedur",
            "description": "Detaillierte Beschreibung",
            "tooth_numbers": ["16", "17"],
            "surfaces": ["okklusal", "mesial"],
            "confidence": 0.95,
            "reasoning": "Begründung basierend auf Textanalyse"
        }
    ],
    "billing_codes": [
        {
            "code": "BEMA 13a",
            "system": "bema",
            "description": "Füllung einflächig",
            "procedure_match": "Kompositfüllung",
            "confidence": 0.9,
            "reasoning": "Einflächige Füllung erkannt durch Kontext-Analyse"
        }
    ],
    "reasoning": "Gesamtbegründung der medizinischen Interpretationen",
    "confidence_overall": 0.85
}"""
    
    def _create_extraction_prompt(self, text: str, bema_goz_catalog: dict, findings_context: str) -> str:
        """Create the extraction prompt with context"""
        
        # Extract key BEMA/GOZ codes for the prompt (to avoid token limit)
        key_codes = self._get_key_codes_for_prompt(bema_goz_catalog)
        
        prompt = f"""
ZAHNÄRZTLICHER DOKUMENTATIONSTEXT:
"{text}"

BEFUNDE (falls vorhanden):
{findings_context}

VERFÜGBARE BEMA/GOZ ABRECHNUNGSZIFFERN (Auswahl):
{json.dumps(key_codes, indent=2, ensure_ascii=False)}

AUFGABE:
Analysiere den Text und erkenne alle durchgeführten zahnärztlichen Behandlungen.
Ordne jedem Verfahren die passenden BEMA/GOZ-Codes zu.

Achte besonders auf:
- Zahnbezeichnungen (FDI-Schema: 11-48)
- Flächenangaben (okklusal, mesial, distal, vestibulär, palatinal/lingual)
- Anästhesie-Arten (Infiltration, Leitung)
- Materialien (Komposit, Amalgam, etc.)
- Komplexität der Behandlung

Beispiele für Interpretationen:
- "Füllung gelegt" → Prüfe Flächenanzahl → BEMA 13a-13d oder GOZ 2080-2110
- "Zahn entfernt" → Prüfe Wurzelanzahl → BEMA 43/44 oder GOZ 3000
- "Lokalanästhesie" → BEMA 41 oder GOZ 0080
"""
        
        return prompt
    
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
        findings: List[DentalFinding] = None,
        fallback_to_traditional: bool = True
    ) -> Dict[str, Any]:
        """
        Intelligent procedure extraction using LLM with traditional fallback
        
        Args:
            text: Dental documentation text
            bema_goz_catalog: BEMA/GOZ code database
            findings: Extracted findings for context
            fallback_to_traditional: Whether to use traditional method as fallback
            
        Returns:
            Dict with procedures and billing codes
        """
        
        if self.use_llm:
            try:
                logger.info("Using LLM-based procedure extraction")
                result = await self.llm_extractor.extract_procedures_and_codes(
                    text, bema_goz_catalog, findings
                )
                
                # Enhance with confidence scoring
                result["extraction_method"] = "llm_primary"
                return result
                
            except LLMExtractionError as e:
                logger.warning("LLM extraction failed, falling back to traditional method", 
                             error=str(e))
                
                if not fallback_to_traditional:
                    raise
        
        # Fallback to traditional method
        logger.info("Using traditional keyword-based extraction")
        return self._traditional_extraction(text, bema_goz_catalog)
    
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