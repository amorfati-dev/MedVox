"""
Documentation Processor Service
Converts transcribed speech into structured dental documentation using AI/LLM
"""

import re
import json
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import structlog
import time

from app.schemas.dental_documentation import (
    DentalDocumentation, DentalFinding, BillingCode, TreatmentPlan,
    TranscriptionResult, AudioMetadata, TreatmentType, BillingSystem,
    ConfidenceLevel
)
from app.services.llm_processor import EnhancedDocumentationProcessor, LLMExtractionError
from app.services.pipeline_processor import ProcessingPipeline
from app.services.documentation_error import DocumentationError
from app.core.config import settings

logger = structlog.get_logger()


class GermanDentalTerminology:
    """German dental terminology and mappings"""
    
    # Tooth number mappings (spoken to FDI)
    TOOTH_NUMBERS = {
        # Spoken German to FDI notation
        "eins eins": "11", "eins-eins": "11", "elf": "11",
        "eins zwei": "12", "eins-zwei": "12", "zwölf": "12",
        "eins drei": "13", "eins-drei": "13", "dreizehn": "13",
        "eins vier": "14", "eins-vier": "14", "vierzehn": "14",
        "eins fünf": "15", "eins-fünf": "15", "fünfzehn": "15",
        "eins sechs": "16", "eins-sechs": "16", "sechzehn": "16",
        "eins sieben": "17", "eins-sieben": "17", "siebzehn": "17",
        "eins acht": "18", "eins-acht": "18", "achtzehn": "18",
        
        "zwei eins": "21", "zwei-eins": "21", "einundzwanzig": "21",
        "zwei zwei": "22", "zwei-zwei": "22", "zweiundzwanzig": "22",
        "zwei drei": "23", "zwei-drei": "23", "dreiundzwanzig": "23",
        "zwei vier": "24", "zwei-vier": "24", "vierundzwanzig": "24",
        "zwei fünf": "25", "zwei-fünf": "25", "fünfundzwanzig": "25",
        "zwei sechs": "26", "zwei-sechs": "26", "sechsundzwanzig": "26",
        "zwei sieben": "27", "zwei-sieben": "27", "siebenundzwanzig": "27",
        "zwei acht": "28", "zwei-acht": "28", "achtundzwanzig": "28",
        
        "drei eins": "31", "drei-eins": "31", "einunddreißig": "31",
        "drei zwei": "32", "drei-zwei": "32", "zweiunddreißig": "32",
        "drei drei": "33", "drei-drei": "33", "dreiunddreißig": "33",
        "drei vier": "34", "drei-vier": "34", "vierunddreißig": "34",
        "drei fünf": "35", "drei-fünf": "35", "fünfunddreißig": "35",
        "drei sechs": "36", "drei-sechs": "36", "sechsunddreißig": "36",
        "drei sieben": "37", "drei-sieben": "37", "siebenunddreißig": "37",
        "drei acht": "38", "drei-acht": "38", "achtunddreißig": "38",
        
        "vier eins": "41", "vier-eins": "41", "einundvierzig": "41",
        "vier zwei": "42", "vier-zwei": "42", "zweiundvierzig": "42",
        "vier drei": "43", "vier-drei": "43", "dreiundvierzig": "43",
        "vier vier": "44", "vier-vier": "44", "vierundvierzig": "44",
        "vier fünf": "45", "vier-fünf": "45", "fünfundvierzig": "45",
        "vier sechs": "46", "vier-sechs": "46", "sechsundvierzig": "46",
        "vier sieben": "47", "vier-sieben": "47", "siebenundvierzig": "47",
        "vier acht": "48", "vier-acht": "48", "achtundvierzig": "48",
    }
    
    # Surface terminology
    SURFACES = {
        "okklusal": "okklusal", "okklusional": "okklusal", "kaufläche": "okklusal",
        "mesial": "mesial", "mesialer": "mesial", "zur mitte": "mesial",
        "distal": "distal", "distaler": "distal", "zur seite": "distal",
        "vestibulär": "vestibulär", "labial": "labial", "bukkaler": "bukkal",
        "palatinal": "palatinal", "lingual": "lingual", "zungenseitig": "lingual",
        "approximal": "approximal", "cervical": "cervical"
    }
    
    # Common diagnoses and findings
    DIAGNOSES = {
        "karies": "Karies",
        "karies profunda": "Karies profunda", 
        "karies media": "Karies media",
        "karies superficialis": "Karies superficialis",
        "pulpitis": "Pulpitis",
        "parodontitis": "Parodontitis",
        "gingivitis": "Gingivitis",
        "abrasion": "Abrasion",
        "attrition": "Attrition",
        "erosion": "Erosion",
        "fraktur": "Fraktur",
        "wurzelkaries": "Wurzelkaries",
        "sekundärkaries": "Sekundärkaries"
    }
    
    # Treatment procedures
    PROCEDURES = {
        "füllung": "Füllung",
        "kompositfüllung": "Kompositfüllung", 
        "amalgamfüllung": "Amalgamfüllung",
        "inlay": "Inlay",
        "onlay": "Onlay",
        "krone": "Krone",
        "teilkrone": "Teilkrone",
        "extraktion": "Extraktion",
        "wurzelkanalbehandlung": "Wurzelkanalbehandlung",
        "wurzelfüllung": "Wurzelfüllung",
        "trepanation": "Trepanation",
        "lokalanästhesie": "Lokalanästhesie",
        "infiltrationsanästhesie": "Infiltrationsanästhesie",
        "leitungsanästhesie": "Leitungsanästhesie",
        "professionelle zahnreinigung": "Professionelle Zahnreinigung",
        "zahnsteinentfernung": "Zahnsteinentfernung",
        "politur": "Politur",
        "fluoridierung": "Fluoridierung"
    }


class BEMAGOZMapper:
    """Enhanced BEMA/GOZ mapper with real database"""
    
    def __init__(self):
        self.codes_data = self._load_codes_database()
        self.bema_point_value = self.codes_data["meta"]["bema_point_value"]
        self.goz_point_value = self.codes_data["meta"]["goz_point_value"]
        
        logger.info("BEMA/GOZ database loaded", 
                   version=self.codes_data["meta"]["version"],
                   bema_codes=len(self.codes_data["bema_codes"]),
                   goz_codes=len(self.codes_data["goz_codes"]))
    
    def _load_codes_database(self) -> dict:
        """Load BEMA/GOZ codes from JSON database"""
        import json
        from pathlib import Path
        
        # Try to load from data directory
        data_file = Path(__file__).parent.parent.parent / "data" / "bema_goz_codes.json"
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("BEMA/GOZ database file not found, using fallback codes")
            # Fallback to minimal hardcoded data
            return self._get_fallback_codes()
    
    def _get_fallback_codes(self) -> dict:
        """Fallback BEMA/GOZ codes if database file not available"""
        return {
            "meta": {
                "version": "fallback",
                "bema_point_value": 1.1271,
                "goz_point_value": 0.0582873
            },
            "bema_codes": {
                "13a": {"code": "BEMA 13a", "points": 8, "description": "Füllung einflächig", "keywords": ["füllung"]},
                "41": {"code": "BEMA 41", "points": 3, "description": "Infiltrationsanästhesie", "keywords": ["lokalanästhesie"]}
            },
            "goz_codes": {
                "2080": {"code": "GOZ 2080", "points": 48, "standard_factor": 2.3, "description": "Füllung einflächig", "keywords": ["füllung"]},
                "0080": {"code": "GOZ 0080", "points": 48, "standard_factor": 2.3, "description": "Infiltrationsanästhesie", "keywords": ["lokalanästhesie"]}
            },
            "procedure_mappings": {
                "füllung": {"bema_default": "13a", "goz_default": "2080"},
                "lokalanästhesie": {"bema_default": "41", "goz_default": "0080"}
            }
        }
    
    def find_codes_for_procedure(self, procedure: str, procedure_details: dict = None) -> List[dict]:
        """
        Find appropriate BEMA/GOZ codes for a procedure
        
        Args:
            procedure: Procedure name (e.g., "Lokalanästhesie")
            procedure_details: Additional details like surfaces, tooth type, etc.
            
        Returns:
            List of matching code dictionaries
        """
        procedure_lower = procedure.lower()
        matching_codes = []
        
        # Check procedure mappings first
        mappings = self.codes_data.get("procedure_mappings", {})
        for mapped_procedure, mapping in mappings.items():
            if mapped_procedure in procedure_lower:
                # Get specific mapping based on details
                codes_to_use = self._get_specific_mapping(mapping, procedure_details)
                
                for system, code_id in codes_to_use.items():
                    if system == "bema" and code_id in self.codes_data["bema_codes"]:
                        code_info = self.codes_data["bema_codes"][code_id].copy()
                        code_info["system"] = "bema"
                        code_info["fee_euros"] = self._calculate_bema_fee(code_info["points"])
                        matching_codes.append(code_info)
                    elif system == "goz" and code_id in self.codes_data["goz_codes"]:
                        code_info = self.codes_data["goz_codes"][code_id].copy() 
                        code_info["system"] = "goz"
                        factor = code_info.get("standard_factor", 2.3)
                        code_info["fee_euros"] = self._calculate_goz_fee(code_info["points"], factor)
                        code_info["factor"] = factor
                        matching_codes.append(code_info)
        
        # Fallback: search by keywords if no direct mapping found
        if not matching_codes:
            matching_codes = self._search_by_keywords(procedure_lower)
        
        return matching_codes
    
    def _get_specific_mapping(self, mapping: dict, details: dict = None) -> dict:
        """Get specific code mapping based on procedure details"""
        codes = {}
        
        # Handle surface-based mappings (fillings)
        if "surface_mapping" in mapping and details and "surfaces" in details:
            surface_count = len(details["surfaces"])
            surface_key = f"{['einflächig', 'zweiflächig', 'dreiflächig', 'vierflächig'][min(surface_count-1, 3)]}"
            
            if surface_key in mapping["surface_mapping"]:
                return mapping["surface_mapping"][surface_key]
        
        # Handle tooth-based mappings (extractions, root canals)
        if "tooth_mapping" in mapping and details and "tooth_type" in details:
            tooth_type = details["tooth_type"]
            if tooth_type in mapping["tooth_mapping"]:
                tooth_codes = mapping["tooth_mapping"][tooth_type]
                codes.update(tooth_codes)
        
        # Use defaults
        if "bema_default" in mapping:
            codes["bema"] = mapping["bema_default"]
        if "goz_default" in mapping:
            codes["goz"] = mapping["goz_default"]
            
        return codes
    
    def _search_by_keywords(self, procedure: str) -> List[dict]:
        """Search codes by matching keywords"""
        matching_codes = []
        
        # Search BEMA codes
        for code_id, code_info in self.codes_data["bema_codes"].items():
            if any(keyword in procedure for keyword in code_info.get("keywords", [])):
                enhanced_info = code_info.copy()
                enhanced_info["system"] = "bema"
                enhanced_info["fee_euros"] = self._calculate_bema_fee(code_info["points"])
                matching_codes.append(enhanced_info)
        
        # Search GOZ codes
        for code_id, code_info in self.codes_data["goz_codes"].items():
            if any(keyword in procedure for keyword in code_info.get("keywords", [])):
                enhanced_info = code_info.copy()
                enhanced_info["system"] = "goz"
                factor = code_info.get("standard_factor", 2.3)
                enhanced_info["fee_euros"] = self._calculate_goz_fee(code_info["points"], factor)
                enhanced_info["factor"] = factor
                matching_codes.append(enhanced_info)
        
        return matching_codes
    
    def _calculate_goz_fee(self, points: int, factor: float = 2.3) -> float:
        """Calculate GOZ fee based on points and factor"""
        return round(points * self.goz_point_value * factor, 2)
    
    def _calculate_bema_fee(self, points: int) -> float:
        """Calculate BEMA fee based on points"""
        return round(points * self.bema_point_value, 2)


class DocumentationProcessor:
    """Main processor for converting speech to structured documentation"""
    
    def __init__(self):
        self.terminology = GermanDentalTerminology()
        self.billing_mapper = BEMAGOZMapper()
        self.llm_processor = EnhancedDocumentationProcessor()
        
        # Only initialize pipeline processor if multi-stage pipeline is enabled
        if settings.USE_MULTI_STAGE_PIPELINE:
            self.pipeline_processor = ProcessingPipeline()
        else:
            self.pipeline_processor = None
            
        self.use_llm_extraction = settings.OPENAI_API_KEY is not None
        self.use_multi_stage_pipeline = settings.USE_MULTI_STAGE_PIPELINE and settings.OPENAI_API_KEY is not None
        
    async def process_transcription(
        self, 
        transcription_result: TranscriptionResult, 
        audio_metadata: AudioMetadata,
        insurance_type: str = "bema",
        patient_id: Optional[str] = None,
        dentist_id: Optional[str] = None
    ) -> DentalDocumentation:
        """
        Process transcription result into structured dental documentation
        """
        start_time = time.time()
        
        logger.info("Starting transcription processing", 
                   text_length=len(transcription_result.text),
                   confidence=transcription_result.confidence)
        
        try:
            # Normalize the text
            normalized_text = self._normalize_text(transcription_result.text)
            
            # Extract dental findings (tooth-specific conditions)
            findings = self._extract_dental_findings(normalized_text)
            
            # Load BEMA/GOZ codes catalog
            bema_goz_catalog = self.billing_mapper.codes_data
            
            # Choose processing method based on configuration
            if self.use_multi_stage_pipeline:
                logger.info("Using sophisticated multi-stage pipeline")
                try:
                    # Run the sophisticated multi-stage pipeline
                    logger.info(f"Starting pipeline with insurance_type: {insurance_type}")
                    pipeline_result = await self.pipeline_processor.process_complete(
                        normalized_text, 
                        findings,
                        insurance_type=insurance_type,
                        patient_id=patient_id,
                        dentist_id=dentist_id
                    )
                    logger.info(f"Pipeline completed successfully: {bool(pipeline_result)}")
                    logger.info(f"Pipeline result keys: {list(pipeline_result.keys()) if pipeline_result else 'None'}")
                    
                    if pipeline_result and 'billing_codes' in pipeline_result:
                        logger.info(f"Billing codes in pipeline result: {len(pipeline_result['billing_codes'])}")
                    else:
                        logger.warning("No billing codes found in pipeline result")
                    
                    final_output = pipeline_result.get("final_output", {})
                    
                    # Extract procedures from pipeline result
                    procedures = [proc["name"] for proc in final_output.get("procedures", [])]
                    billing_codes_data = final_output.get("billing_codes", [])
                    
                    # Convert billing codes format
                    billing_codes = []
                    for code_data in billing_codes_data:
                        billing_code = BillingCode(
                            code=code_data["code"],
                            system=BillingSystem.BEMA if code_data["system"] == "bema" else BillingSystem.GOZ,
                            description=code_data["description"],
                            factor=code_data.get("factor"),
                            points=code_data.get("points"),
                            fee_euros=code_data.get("fee_euros"),
                            confidence=ConfidenceLevel.HIGH if code_data.get("confidence", 0) > 0.8 else ConfidenceLevel.MEDIUM
                        )
                        billing_codes.append(billing_code)
                    
                    # Log pipeline stages performance
                    stages = pipeline_result.get("pipeline_stages", {})
                    logger.info("🎯 Multi-stage pipeline completed",
                               normalization_time=stages.get("normalization", {}).get("processing_time_ms", 0),
                               billing_mapping_time=stages.get("billing_mapping", {}).get("processing_time_ms", 0),
                               audit_time=stages.get("plausibility_check", {}).get("processing_time_ms", 0),
                               total_time=final_output.get("total_processing_time_ms", 0),
                               procedures_found=len(procedures),
                               billing_codes=len(billing_codes),
                               pipeline_confidence=final_output.get("confidence", 0))
                    
                except Exception as e:
                    logger.warning("🚨 Multi-stage pipeline failed, falling back to simple LLM", error=str(e))
                    # Fallback to simple LLM method with error handling
                    if self.use_llm_extraction:
                        try:
                            logger.info("🔄 Pipeline fallback: attempting LLM extraction")
                            llm_result = await self.llm_processor.extract_procedures_intelligent(
                                normalized_text, bema_goz_catalog, findings
                            )
                            logger.info(f"🔄 Pipeline fallback LLM result type: {type(llm_result)}")
                            logger.info(f"🔄 Pipeline fallback LLM result: {llm_result}")
                            
                            # Ensure llm_result is a dict before processing
                            if isinstance(llm_result, dict):
                                procedures_raw = llm_result.get("procedures", [])
                                billing_codes_raw = llm_result.get("billing_codes", [])
                                
                                logger.info(f"🔄 Pipeline fallback procedures (raw): {procedures_raw}")
                                logger.info(f"🔄 Pipeline fallback billing codes (raw): {billing_codes_raw}")
                                
                                procedures = [proc["name"] if isinstance(proc, dict) else str(proc) for proc in procedures_raw]
                                billing_codes = self._convert_llm_billing_codes(billing_codes_raw)
                                
                                logger.info(f"🔄 Pipeline fallback procedures (processed): {procedures}")
                                logger.info(f"🔄 Pipeline fallback billing codes (processed): {len(billing_codes)} codes")
                            else:
                                logger.error(f"🔄 Pipeline fallback: LLM returned non-dict result: {type(llm_result)} = {llm_result}")
                                procedures = self._extract_procedures(normalized_text)
                                billing_codes = self._generate_billing_codes(procedures, findings)
                        except Exception as llm_error:
                            logger.error(f"🔄 Pipeline fallback: LLM extraction also failed: {llm_error}")
                            logger.error(f"🔄 Pipeline fallback: Exception type: {type(llm_error).__name__}")
                            procedures = self._extract_procedures(normalized_text)
                            billing_codes = self._generate_billing_codes(procedures, findings)
                    else:
                        procedures = self._extract_procedures(normalized_text)
                        billing_codes = self._generate_billing_codes(procedures, findings)
                        
            elif self.use_llm_extraction:
                try:
                    logger.info("🧠 Using O3-mini direct extraction")
                    llm_result = await self.llm_processor.extract_procedures_intelligent(
                        normalized_text, 
                        bema_goz_catalog, 
                        findings,
                        insurance_type=insurance_type,
                        patient_id=patient_id
                    )
                    
                    # Ensure llm_result is a dict before processing
                    if not isinstance(llm_result, dict):
                        logger.error(f"LLM returned non-dict result: {type(llm_result)} = {llm_result}")
                        raise ValueError(f"LLM returned {type(llm_result)} instead of dict")
                    
                    # Convert LLM result to our format
                    procedures_raw = llm_result.get("procedures", [])
                    logger.info(f"🧠 LLM procedures extracted (raw): {procedures_raw}")
                    
                    # Handle both string and dict formats for procedures
                    procedures = [proc["name"] if isinstance(proc, dict) else str(proc) for proc in procedures_raw]
                    logger.info(f"🧠 LLM procedures processed: {procedures}")
                    
                    llm_billing_codes_raw = llm_result.get("billing_codes", [])
                    logger.info(f"🧠 LLM billing codes (raw): {llm_billing_codes_raw}")
                    
                    billing_codes = self._convert_llm_billing_codes(llm_billing_codes_raw)
                    logger.info(f"🧠 Converted billing codes: {[{
                        'code': bc.code, 
                        'system': bc.system, 
                        'description': bc.description,
                        'fee_euros': bc.fee_euros
                    } for bc in billing_codes]}")
                    
                    logger.info("O3-mini extraction completed",
                               procedures_found=len(procedures),
                               billing_codes=len(billing_codes),
                               overall_confidence=llm_result.get("confidence_overall", 0))
                    
                except Exception as e:
                    logger.error(f"🚨 O3-mini extraction failed, falling back to traditional method", error=str(e))
                    logger.error(f"🚨 Exception details: {type(e).__name__}: {str(e)}")
                    logger.error(f"🚨 LLM result that caused failure: {llm_result if 'llm_result' in locals() else 'Not available'}")
                    # Fallback to traditional method
                    logger.warning("📝 Using fallback: traditional keyword extraction")
                    procedures = self._extract_procedures(normalized_text)
                    logger.warning(f"📝 Fallback procedures: {procedures}")
                    billing_codes = self._generate_billing_codes(procedures, findings)
                    logger.warning(f"📝 Fallback billing codes: {[{
                        'code': bc.code, 
                        'description': bc.description
                    } for bc in billing_codes]}")
            else:
                # Traditional extraction method
                logger.info("📝 Using traditional keyword-based extraction")
                procedures = self._extract_procedures(normalized_text)
                billing_codes = self._generate_billing_codes(procedures, findings)
            
            # Generate treatment plan
            treatment_plan = self._generate_treatment_plan(findings, procedures)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info("Transcription processing completed",
                       findings_count=len(findings),
                       procedures_count=len(procedures),
                       billing_codes_count=len(billing_codes),
                       processing_time_ms=processing_time)
            
            # Generate required IDs
            import uuid
            recording_id = f"rec_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            return DentalDocumentation(
                recording_id=recording_id,
                dentist_id="system",  # Default dentist
                transcription=transcription_result,
                audio_metadata=audio_metadata,
                findings=findings,
                procedures_performed=procedures,
                billing_codes=billing_codes,
                treatment_plan=treatment_plan
            )
            
        except Exception as e:
            logger.error("Transcription processing failed", error=str(e))
            raise DocumentationError(f"Processing failed: {str(e)}")
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better processing"""
        # Convert to lowercase
        text = text.lower()
        
        # Replace tooth number variations
        for spoken, fdi in self.terminology.TOOTH_NUMBERS.items():
            text = text.replace(spoken, fdi)
        
        # Normalize common variations
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        text = text.strip()
        
        return text
    
    def _identify_treatment_type(self, text: str) -> Optional[TreatmentType]:
        """Identify the primary treatment type from text"""
        
        treatment_keywords = {
            TreatmentType.FILLING: ["füllung", "komposit", "amalgam", "inlay", "onlay"],
            TreatmentType.EXTRACTION: ["extraktion", "ziehen", "entfernung"],
            TreatmentType.ROOT_CANAL: ["wurzelkanal", "wurzelfüllung", "trepanation", "endodontie"],
            TreatmentType.CROWN: ["krone", "überkronung"],
            TreatmentType.PROPHYLAXIS: ["prophylaxe", "zahnreinigung", "scaling", "politur"],
            TreatmentType.EXAMINATION: ["untersuchung", "kontrolle", "befundung"],
            TreatmentType.SURGERY: ["chirurgie", "operation", "schnitt", "naht"]
        }
        
        for treatment_type, keywords in treatment_keywords.items():
            if any(keyword in text for keyword in keywords):
                return treatment_type
                
        return None
    
    def _extract_findings(self, text: str) -> List[DentalFinding]:
        """Extract dental findings and diagnoses"""
        findings = []
        
        # Pattern to match: "Zahn X [surface] [diagnosis]"
        patterns = [
            r'zahn\s+(\d{1,2})\s+(okklusal|mesial|distal|vestibulär|palatinal)?\s*(karies\s*\w*)',
            r'(\d{1,2})\s+(okklusal|mesial|distal|vestibulär|palatinal)\s+(karies\s*\w*)',
            r'(\d{1,2})\s+(pulpitis|parodontitis|gingivitis)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) >= 3:  # zahn pattern
                    tooth_number = groups[0]
                    surface = self._normalize_surface(groups[1]) if groups[1] else None
                    diagnosis = self._normalize_diagnosis(groups[2])
                elif len(groups) == 2:  # simple pattern
                    tooth_number = groups[0]
                    surface = None
                    diagnosis = self._normalize_diagnosis(groups[1])
                else:
                    continue
                
                if diagnosis:
                    finding = DentalFinding(
                        tooth_number=tooth_number,
                        surface=surface,
                        diagnosis=diagnosis,
                        confidence=ConfidenceLevel.MEDIUM
                    )
                    findings.append(finding)
        
        return findings
    
    def _extract_procedures(self, text: str) -> List[str]:
        """Extract performed procedures"""
        procedures = []
        
        for procedure_key, procedure_name in self.terminology.PROCEDURES.items():
            if procedure_key in text:
                procedures.append(procedure_name)
        
        return list(set(procedures))  # Remove duplicates
    
    def _generate_billing_codes(self, procedures: List[str], findings: List[DentalFinding]) -> List[BillingCode]:
        """Generate appropriate billing codes based on procedures and findings"""
        billing_codes = []
        
        for procedure in procedures:
            # Determine procedure details for better code selection
            procedure_details = self._analyze_procedure_context(procedure, findings)
            
            # Find matching codes using enhanced mapper
            matching_codes = self.billing_mapper.find_codes_for_procedure(procedure, procedure_details)
            
            for code_info in matching_codes:
                # Create BillingCode object
                billing_code = BillingCode(
                    code=code_info["code"],
                    system=BillingSystem.BEMA if code_info["system"] == "bema" else BillingSystem.GOZ,
                    description=code_info["description"],
                    factor=code_info.get("factor"),
                    points=code_info.get("points"),
                    fee_euros=code_info.get("fee_euros"),
                    confidence=ConfidenceLevel.HIGH if len(matching_codes) == 1 else ConfidenceLevel.MEDIUM
                )
                billing_codes.append(billing_code)
        
        return billing_codes
    
    def _analyze_procedure_context(self, procedure: str, findings: List[DentalFinding]) -> dict:
        """Analyze procedure context to determine specific billing requirements"""
        context = {}
        
        # Analyze surface count for fillings
        if "füllung" in procedure.lower():
            # Count affected surfaces from findings
            surfaces = set()
            for finding in findings:
                if finding.surface:
                    surfaces.add(finding.surface)
            
            if surfaces:
                context["surfaces"] = list(surfaces)
                context["surface_count"] = len(surfaces)
        
        # Analyze tooth type for extractions/root canals
        if any(term in procedure.lower() for term in ["extraktion", "wurzelkanal"]):
            # Determine if teeth are anterior (single root) or posterior (multi-root)
            tooth_types = set()
            for finding in findings:
                if finding.tooth_number:
                    tooth_num = int(finding.tooth_number) if finding.tooth_number.isdigit() else 0
                    # Molars (6,7,8) are multi-root, others typically single-root
                    if tooth_num % 10 in [6, 7, 8]:
                        tooth_types.add("mehrwurzelig")
                    else:
                        tooth_types.add("einwurzelig")
            
            if tooth_types:
                # Use most conservative (single root) if mixed
                context["tooth_type"] = "einwurzelig" if "einwurzelig" in tooth_types else "mehrwurzelig"
        
        return context
    
    def _generate_treatment_plan(self, findings: List[DentalFinding], procedures: List[str]) -> Optional[TreatmentPlan]:
        """Generate treatment planning recommendations"""
        recommendations = []
        
        # Look for planning keywords in findings
        if findings:
            all_diagnoses = " ".join([f.diagnosis.lower() for f in findings])
            
            if "kontrolle" in all_diagnoses or "nachkontrolle" in all_diagnoses:
                recommendations.append("Nachkontrolle in 1-2 Wochen")
            
            if "wurzelkanal" in all_diagnoses and "abschluss" not in all_diagnoses:
                recommendations.append("Wurzelkanalbehandlung fortsetzen")
        
        # Look for planning keywords in procedures
        all_procedures = " ".join([p.lower() for p in procedures])
        
        if "extraktion" in all_procedures:
            recommendations.append("Nachkontrolle in 3-5 Tagen")
            
        if "füllung" in all_procedures:
            recommendations.append("Kaufläche prüfen bei nächstem Termin")
        
        # Check for caries in findings
        if findings and any("karies" in finding.diagnosis.lower() for finding in findings):
            recommendations.append("Weitere kariöse Läsionen prüfen")
        
        if recommendations:
            return TreatmentPlan(
                recommendation="; ".join(recommendations),
                priority="routine",
                follow_up_weeks=2
            )
        
        return None
    
    def _format_clinical_notes(self, findings: List[DentalFinding], procedures: List[str], original_text: str) -> str:
        """Format structured clinical notes"""
        notes = []
        
        # Add findings
        for finding in findings:
            note = f"Zahn {finding.tooth_number}"
            if finding.surface:
                note += f" {finding.surface}"
            note += f": {finding.diagnosis}"
            notes.append(note)
        
        # Add procedures
        if procedures:
            notes.append(f"Durchgeführt: {', '.join(procedures)}")
        
        # Add original transcription as reference
        notes.append(f"Originaltext: {original_text}")
        
        return ". ".join(notes)
    
    def _extract_materials(self, text: str) -> List[str]:
        """Extract materials and medications used"""
        materials = []
        
        material_keywords = {
            "komposit": "Komposit",
            "amalgam": "Amalgam", 
            "keramik": "Keramik",
            "artikain": "Artikain",
            "lidocain": "Lidocain",
            "fluorid": "Fluorid",
            "chlorhexidin": "Chlorhexidin"
        }
        
        for keyword, material in material_keywords.items():
            if keyword in text:
                materials.append(material)
        
        return materials
    
    def _extract_anesthesia(self, text: str) -> Optional[str]:
        """Extract anesthesia type if mentioned"""
        anesthesia_types = {
            "lokalanästhesie": "Lokalanästhesie",
            "infiltrationsanästhesie": "Infiltrationsanästhesie", 
            "leitungsanästhesie": "Leitungsanästhesie",
            "oberflächenanästhesie": "Oberflächenanästhesie"
        }
        
        for keyword, anesthesia in anesthesia_types.items():
            if keyword in text:
                return anesthesia
        
        return None
    
    def _normalize_surface(self, surface_text: str) -> Optional[str]:
        """Normalize surface descriptions"""
        surface_text = surface_text.lower().strip()
        return self.terminology.SURFACES.get(surface_text)
    
    def _normalize_diagnosis(self, diagnosis_text: str) -> str:
        """Normalize diagnosis descriptions"""
        diagnosis_text = diagnosis_text.lower().strip()
        return self.terminology.DIAGNOSES.get(diagnosis_text, diagnosis_text.title())
    
    def _extract_dental_findings(self, text: str) -> List[DentalFinding]:
        """Extract dental findings from normalized text"""
        findings = []
        
        # Use existing findings extraction but format for DentalFinding objects
        raw_findings = self._extract_findings(text)
        
        for finding in raw_findings:
            # Extract tooth number from finding text
            tooth_match = re.search(r'\b(\d{1,2})\b', finding)
            tooth_number = tooth_match.group(1) if tooth_match else None
            
            # Extract surface information
            surface = None
            for surface_term in ['okklusal', 'mesial', 'distal', 'vestibulär', 'palatinal', 'lingual']:
                if surface_term in finding.lower():
                    surface = surface_term
                    break
            
            dental_finding = DentalFinding(
                tooth_number=tooth_number,
                diagnosis=finding,
                surface=surface,
                severity="normal",  # Could be enhanced with LLM
                confidence=ConfidenceLevel.MEDIUM
            )
            findings.append(dental_finding)
        
        return findings
    
    def _convert_llm_billing_codes(self, llm_billing_codes: List[Dict]) -> List[BillingCode]:
        """Convert LLM billing codes format to BillingCode objects"""
        billing_codes = []
        
        logger.info(f"Converting LLM billing codes: {type(llm_billing_codes)}")
        logger.info(f"LLM billing codes content: {llm_billing_codes}")
        
        # Handle case where llm_billing_codes might be a string or None
        if not llm_billing_codes:
            logger.warning("No billing codes provided to convert")
            return billing_codes
            
        if isinstance(llm_billing_codes, str):
            logger.error(f"Expected list but got string: {llm_billing_codes}")
            return billing_codes
            
        if not isinstance(llm_billing_codes, list):
            logger.error(f"Expected list but got {type(llm_billing_codes)}: {llm_billing_codes}")
            return billing_codes
        
        for i, code_data in enumerate(llm_billing_codes):
            try:
                logger.info(f"Processing billing code {i}: {type(code_data)} = {code_data}")
                
                # Handle case where code_data might be a string
                if isinstance(code_data, str):
                    logger.warning(f"Billing code {i} is a string, skipping: {code_data}")
                    continue
                    
                if not isinstance(code_data, dict):
                    logger.warning(f"Billing code {i} is not a dict, skipping: {code_data}")
                    continue
                
                # Extract type from the format used by O3
                code_type = code_data.get("type", "unknown")
                if code_type == "unknown":
                    # Try to infer from code prefix
                    code = code_data.get("code", "")
                    if "BEMA" in code or "bema" in code.lower():
                        code_type = "bema"
                    elif "GOZ" in code or "goz" in code.lower():
                        code_type = "goz"
                
                billing_code = BillingCode(
                    code=code_data.get("code", ""),
                    system=BillingSystem.BEMA if code_type == "bema" else BillingSystem.GOZ,
                    description=code_data.get("description", ""),
                    factor=code_data.get("factor"),
                    points=code_data.get("points", 0),
                    fee_euros=self._parse_fee_amount(code_data.get("fee", "0.00")),
                    confidence=ConfidenceLevel.HIGH if code_data.get("confidence", 0) > 0.8 else ConfidenceLevel.MEDIUM
                )
                billing_codes.append(billing_code)
                
            except Exception as e:
                logger.error(f"Error converting billing code {i}: {e}")
                logger.error(f"Code data: {code_data}")
                continue
        
        logger.info(f"Successfully converted {len(billing_codes)} billing codes")
        return billing_codes
    
    def _parse_fee_amount(self, fee_string: str) -> float:
        """Parse fee amount from string like '23.61 €' to float"""
        if isinstance(fee_string, (int, float)):
            return float(fee_string)
        
        if isinstance(fee_string, str):
            # Remove currency symbols and spaces
            cleaned = fee_string.replace('€', '').replace(' ', '').replace(',', '.')
            try:
                return float(cleaned)
            except ValueError:
                logger.warning(f"Could not parse fee amount: {fee_string}")
                return 0.0
        
        return 0.0
    
    def _calculate_goz_fee(self, points: int, factor: float = 2.3) -> float:
        """Calculate GOZ fee based on points and factor using current point values"""
        return self.billing_mapper._calculate_goz_fee(points, factor)
    
    def _calculate_bema_fee(self, points: int) -> float:
        """Calculate BEMA fee based on points using current point values"""
        return self.billing_mapper._calculate_bema_fee(points) 