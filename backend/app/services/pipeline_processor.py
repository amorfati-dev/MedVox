"""
Multi-Stage AI Processing Pipeline for Dental Documentation
Implements a sophisticated pipeline using different models for optimal cost/quality balance
"""

import json
import time
from typing import List, Dict, Optional, Any, Tuple
import structlog

from app.core.config import settings
from app.schemas.dental_documentation import DentalFinding, BillingCode, BillingSystem, ConfidenceLevel
from app.services.llm_processor import LLMExtractionError

logger = structlog.get_logger()


class PipelineStage:
    """Base class for pipeline stages"""
    
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.api_key = settings.OPENAI_API_KEY
        
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Override in subclasses"""
        raise NotImplementedError


class TextNormalizationStage(PipelineStage):
    """Stage B: Post-correction & Normalization using GPT-4o-mini"""
    
    def __init__(self):
        super().__init__("Text Normalization", "gpt-4o-mini")
        self.temperature = 0.1
    
    async def process(self, raw_text: str) -> Dict[str, Any]:
        """Clean up transcription with proper punctuation and terminology"""
        start_time = time.time()
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            logger.info("Starting text normalization", 
                       text_length=len(raw_text), 
                       model=self.model)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_normalization_prompt()
                    },
                    {
                        "role": "user",
                        "content": f"Normalisiere diesen zahnärztlichen Text:\n\n{raw_text}"
                    }
                ],
                temperature=self.temperature,
                max_tokens=1000
            )
            
            normalized_text = response.choices[0].message.content.strip()
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info("Text normalization completed",
                       original_length=len(raw_text),
                       normalized_length=len(normalized_text),
                       processing_time_ms=processing_time)
            
            return {
                "normalized_text": normalized_text,
                "original_text": raw_text,
                "processing_time_ms": processing_time,
                "model_used": self.model,
                "stage": "normalization"
            }
            
        except Exception as e:
            logger.error("Text normalization failed", error=str(e))
            # Fallback to original text
            return {
                "normalized_text": raw_text,
                "original_text": raw_text,
                "processing_time_ms": 0,
                "model_used": "fallback",
                "stage": "normalization",
                "error": str(e)
            }
    
    def _get_normalization_prompt(self) -> str:
        return """Du bist ein Experte für deutsche zahnärztliche Dokumentation.

Deine Aufgabe:
1. Korrigiere Satzzeichen und Grammatik
2. Vereinheitliche zahnmedizinische Fachbegriffe (z.B. "Lokalanästhesie" statt "örtliche Betäubung")
3. Standardisiere Zahnbezeichnungen (FDI-Schema: 11-48)
4. Korrigiere offensichtliche Transkriptionsfehler
5. Behalte den medizinischen Inhalt exakt bei

Beispiel:
Input: "zahn sechsunddreißig hat karies hab lokal betäubt und gefüllt"
Output: "Zahn 36 hat Karies. Lokalanästhesie durchgeführt und Füllung gelegt."

Gib NUR den korrigierten Text zurück, keine Erklärungen."""


class BillingMappingStage(PipelineStage):
    """Stage C: BEMA/GOZ Mapping using GPT-4o (full version)"""
    
    def __init__(self):
        super().__init__("Billing Mapping", "gpt-4o")
        self.temperature = 0.1
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract billing codes with reasoning from normalized text"""
        start_time = time.time()
        
        normalized_text = data.get("normalized_text", "")
        findings = data.get("findings", [])
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            logger.info("Starting billing code mapping", 
                       text_length=len(normalized_text),
                       model=self.model)
            
            # Load BEMA/GOZ catalog for context
            bema_goz_catalog = self._load_billing_catalog()
            key_codes = self._get_key_codes_for_context(bema_goz_catalog)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_billing_prompt()
                    },
                    {
                        "role": "user",
                        "content": self._create_billing_query(normalized_text, findings, key_codes)
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content
            billing_result = json.loads(result_text)
            
            # Enhance with actual fee calculations
            enhanced_codes = self._enhance_billing_codes(billing_result.get("billing_codes", []), bema_goz_catalog)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info("Billing mapping completed",
                       codes_extracted=len(enhanced_codes),
                       processing_time_ms=processing_time)
            
            return {
                "billing_codes": enhanced_codes,
                "procedures": billing_result.get("procedures", []),
                "reasoning": billing_result.get("reasoning", ""),
                "confidence": billing_result.get("confidence", 0.8),
                "processing_time_ms": processing_time,
                "model_used": self.model,
                "stage": "billing_mapping"
            }
            
        except Exception as e:
            logger.error("Billing mapping failed", error=str(e))
            return {
                "billing_codes": [],
                "procedures": [],
                "reasoning": f"Billing mapping failed: {str(e)}",
                "confidence": 0.0,
                "processing_time_ms": 0,
                "model_used": "fallback",
                "stage": "billing_mapping",
                "error": str(e)
            }
    
    def _get_billing_prompt(self) -> str:
        return """Du bist ein Abrechnungsexperte für deutsche Zahnmedizin mit jahrelanger Erfahrung.

Deine Aufgabe:
1. Analysiere den zahnärztlichen Text präzise
2. Erkenne ALLE durchgeführten Behandlungen
3. Ordne exakte BEMA/GOZ-Codes zu
4. Berücksichtige Komplexität und Schwierigkeitsgrad
5. Begründe jede Zuordnung detailliert

Wichtige Regeln:
- BEMA für gesetzlich Versicherte, GOZ für Privatpatienten
- Berücksichtige Zahntyp (einwurzelig/mehrwurzelig) für Extraktionen
- Prüfe Flächenanzahl für Füllungen (1-4 Flächen)
- Anästhesie nicht vergessen bei invasiven Eingriffen
- Bei Unsicherheit: niedrigere Konfidenz angeben

Antworte im JSON-Format:
{
    "procedures": [
        {
            "name": "Genaue Bezeichnung",
            "description": "Detaillierte Beschreibung",
            "tooth_numbers": ["36"],
            "complexity": "einfach|mittel|komplex"
        }
    ],
    "billing_codes": [
        {
            "code": "BEMA 13a",
            "system": "bema",
            "description": "Füllung einflächig",
            "procedure_match": "Kompositfüllung",
            "reasoning": "Detaillierte Begründung der Zuordnung",
            "confidence": 0.95,
            "tooth_number": "36"
        }
    ],
    "reasoning": "Gesamtbegründung der Analyse",
    "confidence": 0.9
}"""
    
    def _create_billing_query(self, text: str, findings: List, key_codes: Dict) -> str:
        findings_text = ""
        if findings:
            findings_text = "\n".join([
                f"- Zahn {f.tooth_number}: {f.diagnosis}" + 
                (f" ({f.surface})" if hasattr(f, 'surface') and f.surface else "")
                for f in findings
            ])
        
        return f"""
ZAHNÄRZTLICHER TEXT:
"{text}"

BEFUNDE:
{findings_text}

VERFÜGBARE CODES (Auswahl):
{json.dumps(key_codes, indent=2, ensure_ascii=False)}

Analysiere den Text und extrahiere alle Abrechnungspositionen mit Begründung.
"""
    
    def _load_billing_catalog(self) -> Dict:
        """Load BEMA/GOZ catalog"""
        from pathlib import Path
        
        data_file = Path(__file__).parent.parent.parent / "data" / "bema_goz_codes.json"
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"bema_codes": {}, "goz_codes": {}, "meta": {"bema_point_value": 1.0, "goz_point_value": 0.0582}}
    
    def _get_key_codes_for_context(self, catalog: Dict) -> Dict:
        """Get most relevant codes for context"""
        important_categories = [
            "Füllungstherapie", "Anästhesie", "Chirurgie", "Endodontie", 
            "Diagnostik", "Prophylaxe"
        ]
        
        key_codes = {"bema": {}, "goz": {}}
        
        for code_id, code_info in catalog.get("bema_codes", {}).items():
            if code_info.get("category") in important_categories:
                key_codes["bema"][code_id] = {
                    "code": code_info["code"],
                    "description": code_info["description"],
                    "points": code_info["points"]
                }
        
        for code_id, code_info in catalog.get("goz_codes", {}).items():
            if code_info.get("category") in important_categories:
                key_codes["goz"][code_id] = {
                    "code": code_info["code"],
                    "description": code_info["description"],
                    "points": code_info["points"],
                    "factor": code_info.get("standard_factor", 2.3)
                }
        
        return key_codes
    
    def _enhance_billing_codes(self, codes: List[Dict], catalog: Dict) -> List[Dict]:
        """Enhance billing codes with actual fee calculations"""
        enhanced = []
        
        for code in codes:
            code_id = code.get("code", "").replace("BEMA ", "").replace("GOZ ", "")
            system = code.get("system", "").lower()
            
            catalog_key = f"{system}_codes"
            if catalog_key in catalog and code_id in catalog[catalog_key]:
                catalog_info = catalog[catalog_key][code_id]
                
                if system == "bema":
                    point_value = catalog["meta"]["bema_point_value"]
                    fee_euros = round(catalog_info["points"] * point_value, 2)
                    factor = None
                else:  # GOZ
                    point_value = catalog["meta"]["goz_point_value"]
                    factor = catalog_info.get("standard_factor", 2.3)
                    fee_euros = round(catalog_info["points"] * point_value * factor, 2)
                
                enhanced.append({
                    "code": catalog_info["code"],
                    "system": system,
                    "description": catalog_info["description"],
                    "points": catalog_info["points"],
                    "fee_euros": fee_euros,
                    "factor": factor,
                    "confidence": code.get("confidence", 0.8),
                    "reasoning": code.get("reasoning", ""),
                    "tooth_number": code.get("tooth_number"),
                    "llm_extracted": True
                })
        
        return enhanced


class AdvancedBillingStage(PipelineStage):
    """Optional Stage C+: Advanced BEMA/GOZ Mapping using o3 for complex cases"""
    
    def __init__(self):
        super().__init__("Advanced Billing Mapping", "o3")
        self.temperature = 0.1
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced billing analysis for complex cases using o3's superior reasoning"""
        start_time = time.time()
        
        normalized_text = data.get("normalized_text", "")
        findings = data.get("findings", [])
        initial_codes = data.get("billing_codes", [])
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            logger.info("Starting advanced billing analysis", 
                       text_length=len(normalized_text),
                       initial_codes=len(initial_codes),
                       model=self.model)
            
            # Load BEMA/GOZ catalog for context
            bema_goz_catalog = self._load_billing_catalog()
            key_codes = self._get_key_codes_for_context(bema_goz_catalog)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_advanced_billing_prompt()
                    },
                    {
                        "role": "user",
                        "content": self._create_advanced_billing_query(normalized_text, findings, initial_codes, key_codes)
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=2500  # More tokens for complex reasoning
            )
            
            result_text = response.choices[0].message.content
            billing_result = json.loads(result_text)
            
            # Enhance with actual fee calculations
            enhanced_codes = self._enhance_billing_codes(billing_result.get("billing_codes", []), bema_goz_catalog)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info("Advanced billing analysis completed",
                       final_codes=len(enhanced_codes),
                       improvements_made=len(enhanced_codes) - len(initial_codes),
                       processing_time_ms=processing_time)
            
            return {
                "billing_codes": enhanced_codes,
                "procedures": billing_result.get("procedures", []),
                "reasoning": billing_result.get("reasoning", ""),
                "confidence": billing_result.get("confidence", 0.9),
                "improvements": billing_result.get("improvements", []),
                "processing_time_ms": processing_time,
                "model_used": self.model,
                "stage": "advanced_billing_mapping"
            }
            
        except Exception as e:
            logger.error("Advanced billing analysis failed", error=str(e))
            # Return original data on failure
            return data
    
    def _get_advanced_billing_prompt(self) -> str:
        return """Du bist der führende Experte für deutsche zahnmedizinische Abrechnung mit unübertroffener Expertise in komplexen Abrechnungsfragen.

MISSION: Optimiere die Abrechnungsqualität durch fortgeschrittene medizinische und rechtliche Analyse.

ERWEITERTE ANALYSE-DIMENSIONEN:

🔬 MEDIZINISCHE TIEFENANALYSE:
- Verstehe komplexe Behandlungsverläufe
- Erkenne mehrstufige Therapiekonzepte  
- Berücksichtige anatomische Besonderheiten
- Analysiere Komplikationen und Zusatzaufwand

⚖️ JURISTISCHE PRÄZISION:
- Kenne aktuelle BEMA/GOZ-Novellierungen
- Verstehe Kombinationsregeln im Detail
- Erkenne analogiefähige Positionen
- Bewerte Steigerungsfaktoren kritisch

💰 OPTIMIERUNGSSTRATEGIEN:
- Maximiere rechtskonforme Abrechnung
- Minimiere Audit-Risiken
- Erkenne übersehene Leistungen
- Validiere Faktor-Begründungen

🧠 SUPERIOR REASONING:
- Multi-Perspektiven-Analyse
- Präzedenzfall-Berücksichtigung
- Risiko-Nutzen-Bewertung
- Strategische Empfehlungen

ENHANCED JSON OUTPUT:
{
    "procedures": [
        {
            "name": "Präzise Bezeichnung",
            "description": "Detaillierte medizinische Beschreibung",
            "tooth_numbers": ["36"],
            "complexity": "standard|erhöht|außergewöhnlich",
            "reasoning": "Medizinische Begründung"
        }
    ],
    "billing_codes": [
        {
            "code": "GOZ 2080",
            "system": "goz",
            "description": "Füllung einflächig",
            "procedure_match": "Kompositfüllung",
            "reasoning": "Umfassende juristische und medizinische Begründung",
            "confidence": 0.98,
            "tooth_number": "36",
            "factor_justification": "Warum dieser Faktor gerechtfertigt ist",
            "alternative_codes": ["Alternative falls zutreffend"],
            "legal_basis": "Spezifische GOZ/BEMA Referenz"
        }
    ],
    "improvements": [
        {
            "type": "added_code|updated_factor|optimized_description",
            "description": "Was wurde verbessert",
            "financial_impact": 25.50,
            "risk_reduction": "Wie wurde das Audit-Risiko reduziert"
        }
    ],
    "reasoning": "Tiefgehende multi-dimensionale Analyse mit medizinischen, juristischen und strategischen Überlegungen",
    "confidence": 0.95,
    "optimization_summary": "Zusammenfassung der Verbesserungen"
}"""
    
    def _create_advanced_billing_query(self, text: str, findings: List, initial_codes: List[Dict], key_codes: Dict) -> str:
        findings_text = ""
        if findings:
            findings_text = "\n".join([
                f"- Zahn {f.tooth_number}: {f.diagnosis}" + 
                (f" ({f.surface})" if hasattr(f, 'surface') and f.surface else "")
                for f in findings
            ])
        
        initial_codes_text = ""
        if initial_codes:
            initial_codes_text = "\n".join([
                f"- {code['code']}: {code['description']} ({code.get('fee_euros', 0):.2f}€)"
                for code in initial_codes
            ])
        
        return f"""
ZAHNÄRZTLICHER TEXT:
"{text}"

BEFUNDE:
{findings_text}

BEREITS EXTRAHIERTE CODES (zur Optimierung):
{initial_codes_text}

VERFÜGBARE CODES (Auswahl):
{json.dumps(key_codes, indent=2, ensure_ascii=False)}

MISSION: Optimiere die bestehende Abrechnung durch:
1. Validierung der aktuellen Codes
2. Identifikation fehlender Positionen  
3. Optimierung der Steigerungsfaktoren
4. Minimierung von Audit-Risiken
5. Maximierung der rechtmäßigen Vergütung

Führe eine umfassende Analyse durch und gib optimierte Abrechnungsempfehlungen.
"""
    
    # Reuse methods from BillingMappingStage
    def _load_billing_catalog(self) -> Dict:
        """Load BEMA/GOZ catalog"""
        from pathlib import Path
        
        data_file = Path(__file__).parent.parent.parent / "data" / "bema_goz_codes.json"
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"bema_codes": {}, "goz_codes": {}, "meta": {"bema_point_value": 1.0, "goz_point_value": 0.0582}}
    
    def _get_key_codes_for_context(self, catalog: Dict) -> Dict:
        """Get most relevant codes for context"""
        important_categories = [
            "Füllungstherapie", "Anästhesie", "Chirurgie", "Endodontie", 
            "Diagnostik", "Prophylaxe", "Prothetik"
        ]
        
        key_codes = {"bema": {}, "goz": {}}
        
        for code_id, code_info in catalog.get("bema_codes", {}).items():
            if code_info.get("category") in important_categories:
                key_codes["bema"][code_id] = {
                    "code": code_info["code"],
                    "description": code_info["description"],
                    "points": code_info["points"]
                }
        
        for code_id, code_info in catalog.get("goz_codes", {}).items():
            if code_info.get("category") in important_categories:
                key_codes["goz"][code_id] = {
                    "code": code_info["code"],
                    "description": code_info["description"],
                    "points": code_info["points"],
                    "factor": code_info.get("standard_factor", 2.3)
                }
        
        return key_codes
    
    def _enhance_billing_codes(self, codes: List[Dict], catalog: Dict) -> List[Dict]:
        """Enhance billing codes with actual fee calculations"""
        enhanced = []
        
        for code in codes:
            code_id = code.get("code", "").replace("BEMA ", "").replace("GOZ ", "")
            system = code.get("system", "").lower()
            
            catalog_key = f"{system}_codes"
            if catalog_key in catalog and code_id in catalog[catalog_key]:
                catalog_info = catalog[catalog_key][code_id]
                
                if system == "bema":
                    point_value = catalog["meta"]["bema_point_value"]
                    fee_euros = round(catalog_info["points"] * point_value, 2)
                    factor = None
                else:  # GOZ
                    point_value = catalog["meta"]["goz_point_value"]
                    factor = catalog_info.get("standard_factor", 2.3)
                    fee_euros = round(catalog_info["points"] * point_value * factor, 2)
                
                enhanced.append({
                    "code": catalog_info["code"],
                    "system": system,
                    "description": catalog_info["description"],
                    "points": catalog_info["points"],
                    "fee_euros": fee_euros,
                    "factor": factor,
                    "confidence": code.get("confidence", 0.9),
                    "reasoning": code.get("reasoning", ""),
                    "tooth_number": code.get("tooth_number"),
                    "llm_extracted": True,
                    "o3_optimized": True
                })
        
        return enhanced


class PlausibilityCheckStage(PipelineStage):
    """Stage D: Plausibility Check using o3 models for superior reasoning"""
    
    def __init__(self):
        # Use configured audit model (o3-mini by default)
        model = settings.PIPELINE_AUDIT_MODEL if self._is_o3_available() else "gpt-4o"
        super().__init__("Plausibility Check", model)
        self.temperature = 0.1
        self.use_o3_for_complex = settings.USE_O3_FOR_COMPLEX_CASES
        self.complexity_threshold = settings.O3_COMPLEXITY_THRESHOLD
        self.reasoning_mode = settings.O3_REASONING_MODE
    
    def _is_o3_available(self) -> bool:
        """Check if o3 models are available"""
        # User confirmed o3 is available!
        return True
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Review and validate billing codes for completeness and accuracy"""
        start_time = time.time()
        
        # Calculate case complexity for intelligent model selection
        total_value = self._calculate_case_value(data.get("billing_codes", []))
        use_full_o3 = (
            self.use_o3_for_complex and 
            total_value > self.complexity_threshold and 
            self._is_o3_available()
        )
        
        # Choose model based on complexity
        selected_model = "o3" if use_full_o3 else self.model
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            logger.info("Starting plausibility check", 
                       model=selected_model,
                       codes_to_review=len(data.get("billing_codes", [])),
                       case_value_euros=total_value,
                       reasoning_mode=self.reasoning_mode,
                       using_full_o3=use_full_o3)
            
            # Adjust max_tokens for o3 models (they can handle more complex reasoning)
            max_tokens = 2000 if selected_model.startswith("o3") else 1000
            
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_audit_prompt(selected_model)
                    },
                    {
                        "role": "user",
                        "content": self._create_audit_query(data)
                    }
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=max_tokens
            )
            
            audit_result = json.loads(response.choices[0].message.content)
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info("Plausibility check completed",
                       issues_found=len(audit_result.get("issues", [])),
                       overall_confidence=audit_result.get("overall_confidence", 0),
                       processing_time_ms=processing_time,
                       model_used=selected_model)
            
            return {
                "audit_result": audit_result,
                "processing_time_ms": processing_time,
                "model_used": selected_model,
                "case_value_euros": total_value,
                "used_full_o3": use_full_o3,
                "stage": "plausibility_check"
            }
            
        except Exception as e:
            logger.error("Plausibility check failed", error=str(e))
            return {
                "audit_result": {
                    "overall_confidence": 0.7,
                    "issues": [],
                    "recommendations": [],
                    "chain_of_thought": f"Audit failed: {str(e)}"
                },
                "processing_time_ms": 0,
                "model_used": "fallback",
                "stage": "plausibility_check",
                "error": str(e)
            }
    
    def _calculate_case_value(self, billing_codes: List[Dict]) -> float:
        """Calculate total value of the case for complexity assessment"""
        total_value = 0.0
        
        for code in billing_codes:
            fee = code.get("fee_euros", 0)
            if isinstance(fee, (int, float)):
                total_value += fee
        
        return total_value
    
    def _get_audit_prompt(self, model: str = "gpt-4o") -> str:
        if model.startswith("o3"):
            # Enhanced prompt for o3 models with superior reasoning
            return f"""Du bist ein Experte für deutsche zahnmedizinische Abrechnung mit jahrzehntelanger Erfahrung und exzellenten analytischen Fähigkeiten.

MISSION: Führe eine tiefgehende, systematische Analyse der Abrechnungspositionen durch.

ANALYSE-FRAMEWORK:
1. 📋 VOLLSTÄNDIGKEITS-ANALYSE
   - Alle durchgeführten Behandlungen erfasst?
   - Versteckte/implizite Leistungen erkannt?
   - Vorbereitende Maßnahmen berücksichtigt?

2. 🔍 PLAUSIBILITÄTS-PRÜFUNG
   - Logische Behandlungssequenz?
   - Anatomische Korrektheit?
   - Kombinationsregeln eingehalten?

3. ⚖️ RECHTLICHE VALIDIERUNG
   - BEMA/GOZ-Konformität?
   - Ausschluss-Kriterien beachtet?
   - Faktor-Begründung angemessen?

4. 💰 ÖKONOMISCHE BEWERTUNG
   - Verhältnismäßigkeit der Kosten?
   - Optimierungspotential?
   - Audit-Risiko-Assessment?

REASONING-MODUS: {self.reasoning_mode}
- "detailed": Vollständige Schritt-für-Schritt Analyse
- "concise": Fokus auf kritische Punkte  
- "audit": Compliance- und Risiko-orientiert

ADVANCED OUTPUT (JSON):
{{
    "overall_confidence": 0.95,
    "total_value_analysis": {{
        "documented_value": 150.50,
        "potential_missing": 25.00,
        "risk_score": "low|medium|high"
    }},
    "issues": [
        {{
            "type": "missing_code|incorrect_code|compliance_risk",
            "description": "Detaillierte Problembeschreibung",
            "severity": "critical|high|medium|low",
            "financial_impact": 15.50,
            "suggestion": "Konkrete Handlungsempfehlung",
            "legal_basis": "BEMA/GOZ Referenz"
        }}
    ],
    "recommendations": [
        "Strategische Verbesserungsvorschläge"
    ],
    "chain_of_thought": "Detaillierte multi-level Reasoning-Kette mit medizinischen, rechtlichen und ökonomischen Überlegungen",
    "audit_readiness": {{
        "score": 0.9,
        "weak_points": ["Bereiche die bei Prüfung problematisch sein könnten"],
        "documentation_quality": "excellent|good|needs_improvement"
    }}
}}"""
        else:
            # Standard prompt for other models
            return """Du bist ein erfahrener Abrechnungsauditor für deutsche Zahnmedizin.

Deine Aufgabe:
1. Prüfe die Vollständigkeit der Abrechnungspositionen
2. Erkenne fehlende oder falsche Codes
3. Validiere die Plausibilität der Kombinationen
4. Gib konkrete Verbesserungsvorschläge

Chain-of-Thought Reasoning:
- Schritt 1: Was wurde dokumentiert?
- Schritt 2: Welche Codes wurden zugeordnet?
- Schritt 3: Was könnte fehlen?
- Schritt 4: Sind die Codes plausibel?
- Schritt 5: Finale Bewertung

Antworte im JSON-Format:
{
    "overall_confidence": 0.9,
    "issues": [
        {
            "type": "missing_code",
            "description": "Anästhesie fehlt bei invasivem Eingriff",
            "severity": "medium",
            "suggestion": "BEMA 41 hinzufügen"
        }
    ],
    "recommendations": [
        "Prüfe ob Anästhesie dokumentiert werden sollte"
    ],
    "chain_of_thought": "Detaillierte Schritt-für-Schritt Analyse..."
}"""
    
    def _create_audit_query(self, data: Dict[str, Any]) -> str:
        normalized_text = data.get("normalized_text", "")
        billing_codes = data.get("billing_codes", [])
        procedures = data.get("procedures", [])
        
        codes_summary = "\n".join([
            f"- {code['code']}: {code['description']} (Konfidenz: {code.get('confidence', 0)})"
            for code in billing_codes
        ])
        
        return f"""
ORIGINALTEXT:
"{normalized_text}"

EXTRAHIERTE CODES:
{codes_summary}

PROZEDUREN:
{json.dumps(procedures, indent=2, ensure_ascii=False)}

Prüfe die Vollständigkeit und Korrektheit der Abrechnung.
Verwende Chain-of-Thought Reasoning für deine Analyse.
"""


class ProcessingPipeline:
    """Main pipeline coordinator that orchestrates all stages"""
    
    def __init__(self):
        self.stages = {
            "normalization": TextNormalizationStage(),
            "billing_mapping": BillingMappingStage(),
            "advanced_billing": AdvancedBillingStage(),  # Optional o3-powered optimization
            "plausibility_check": PlausibilityCheckStage()
        }
        self.use_advanced_billing = settings.USE_O3_FOR_COMPLEX_CASES
        self.advanced_billing_threshold = settings.O3_COMPLEXITY_THRESHOLD
        
    async def process_complete(
        self, 
        raw_text: str, 
        findings: List[DentalFinding] = None
    ) -> Dict[str, Any]:
        """Run complete pipeline from raw text to validated billing codes"""
        
        pipeline_start = time.time()
        results = {
            "raw_text": raw_text,
            "pipeline_stages": {},
            "final_output": {}
        }
        
        logger.info("Starting complete processing pipeline", 
                   text_length=len(raw_text))
        
        try:
            # Stage B: Text Normalization
            logger.info("🔧 Stage B: Text Normalization")
            norm_result = await self.stages["normalization"].process(raw_text)
            results["pipeline_stages"]["normalization"] = norm_result
            
            # Stage C: Billing Mapping
            logger.info("💰 Stage C: Billing Code Mapping")
            billing_input = {
                **norm_result,
                "findings": findings or []
            }
            billing_result = await self.stages["billing_mapping"].process(billing_input)
            results["pipeline_stages"]["billing_mapping"] = billing_result
            
            # Stage C+: Advanced Billing Optimization (optional, for complex cases)
            final_billing_result = billing_result
            if self.use_advanced_billing and self._should_use_advanced_billing(billing_result):
                logger.info("🧠 Stage C+: Advanced Billing Optimization (o3)")
                advanced_input = {
                    **norm_result,
                    **billing_result,
                    "findings": findings or []
                }
                advanced_result = await self.stages["advanced_billing"].process(advanced_input)
                results["pipeline_stages"]["advanced_billing"] = advanced_result
                final_billing_result = advanced_result
                
                logger.info("Advanced billing optimization completed",
                           original_codes=len(billing_result.get("billing_codes", [])),
                           optimized_codes=len(advanced_result.get("billing_codes", [])),
                           improvements=len(advanced_result.get("improvements", [])))
            
            # Stage D: Plausibility Check
            logger.info("🔍 Stage D: Plausibility Check")
            audit_input = {
                **norm_result,
                **final_billing_result
            }
            audit_result = await self.stages["plausibility_check"].process(audit_input)
            results["pipeline_stages"]["plausibility_check"] = audit_result
            
            # Compile final output
            total_time = int((time.time() - pipeline_start) * 1000)
            
            # Determine pipeline type used
            pipeline_type = "multi_stage_ai"
            if "advanced_billing" in results["pipeline_stages"]:
                pipeline_type = "multi_stage_ai_with_o3_optimization"
            
            results["final_output"] = {
                "normalized_text": norm_result.get("normalized_text", raw_text),
                "procedures": final_billing_result.get("procedures", []),
                "billing_codes": final_billing_result.get("billing_codes", []),
                "confidence": final_billing_result.get("confidence", 0.7),
                "audit_result": audit_result.get("audit_result", {}),
                "improvements": final_billing_result.get("improvements", []),
                "total_processing_time_ms": total_time,
                "pipeline_used": pipeline_type,
                "o3_enhanced": "advanced_billing" in results["pipeline_stages"]
            }
            
            logger.info("🎯 Pipeline completed successfully",
                       total_processing_time_ms=total_time,
                       codes_extracted=len(final_billing_result.get("billing_codes", [])),
                       overall_confidence=final_billing_result.get("confidence", 0),
                       pipeline_type=pipeline_type,
                       o3_optimization_used="advanced_billing" in results["pipeline_stages"])
            
            return results
            
        except Exception as e:
            logger.error("💥 Pipeline processing failed", error=str(e))
            total_time = int((time.time() - pipeline_start) * 1000)
            
            results["final_output"] = {
                "normalized_text": raw_text,
                "procedures": [],
                "billing_codes": [],
                "confidence": 0.0,
                "audit_result": {"error": str(e)},
                "total_processing_time_ms": total_time,
                "pipeline_used": "failed",
                "error": str(e)
            }
            
            return results
    
    def _should_use_advanced_billing(self, billing_result: Dict[str, Any]) -> bool:
        """Determine if advanced o3 billing optimization should be used"""
        
        # Calculate total case value
        billing_codes = billing_result.get("billing_codes", [])
        total_value = 0.0
        
        for code in billing_codes:
            fee = code.get("fee_euros", 0)
            if isinstance(fee, (int, float)):
                total_value += fee
        
        # Use advanced billing if:
        # 1. Case value exceeds threshold
        # 2. OR low confidence in initial billing
        # 3. OR complex procedures detected
        
        value_threshold_met = total_value >= self.advanced_billing_threshold
        low_confidence = billing_result.get("confidence", 1.0) < 0.8
        complex_procedures = self._has_complex_procedures(billing_result.get("procedures", []))
        
        should_use = value_threshold_met or low_confidence or complex_procedures
        
        logger.info("Advanced billing decision", 
                   case_value=total_value,
                   threshold=self.advanced_billing_threshold,
                   confidence=billing_result.get("confidence", 1.0),
                   complex_procedures=complex_procedures,
                   decision=should_use)
        
        return should_use
    
    def _has_complex_procedures(self, procedures: List[Dict]) -> bool:
        """Check if procedures indicate complexity requiring o3 analysis"""
        complex_keywords = [
            "wurzelkanal", "extraktion", "implant", "chirurg", "komplex", 
            "schwierig", "mehrfläch", "bridge", "crown", "prothetik"
        ]
        
        for proc in procedures:
            proc_name = proc.get("name", "").lower()
            proc_desc = proc.get("description", "").lower()
            
            if any(keyword in proc_name or keyword in proc_desc for keyword in complex_keywords):
                return True
                
        return False 