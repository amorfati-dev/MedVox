"""
RAG-based Retrieval System for German Dental Billing Codes
Provides semantic search over BEMA/GOZ/GOÄ catalogs for relevant code extraction
"""

import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
import structlog
from difflib import SequenceMatcher

logger = structlog.get_logger()


class DentalCodeRetriever:
    """RAG-based retrieval system for German dental billing codes"""
    
    def __init__(self):
        self.catalogs = self._load_all_catalogs()
        self.code_embeddings = self._prepare_embeddings()
        
        logger.info("🔍 RAG Dental Code Retriever initialized",
                   bema_codes=len(self.catalogs.get("bema_codes", {})),
                   goz_codes=len(self.catalogs.get("goz_codes", {})),
                   goae_codes=len(self.catalogs.get("goae_codes", {})))
    
    def _load_all_catalogs(self) -> Dict[str, Any]:
        """Load all available dental billing catalogs"""
        data_dir = Path(__file__).parent.parent.parent / "data"
        
        catalogs = {
            "bema_codes": {},
            "goz_codes": {},
            "goae_codes": {},
            "meta": {}
        }
        
        # Load existing catalog
        try:
            catalog_file = data_dir / "bema_goz_codes.json"
            if catalog_file.exists():
                with open(catalog_file, 'r', encoding='utf-8') as f:
                    existing_catalog = json.load(f)
                    catalogs.update(existing_catalog)
                    logger.info("✅ Loaded existing BEMA/GOZ catalog")
        except Exception as e:
            logger.warning(f"Could not load existing catalog: {e}")
        
        # Load additional catalogs if available
        for catalog_name in ["bema_complete.json", "goz_complete.json", "goae_complete.json"]:
            try:
                catalog_file = data_dir / catalog_name
                if catalog_file.exists():
                    with open(catalog_file, 'r', encoding='utf-8') as f:
                        additional_catalog = json.load(f)
                        catalogs.update(additional_catalog)
                        logger.info(f"✅ Loaded additional catalog: {catalog_name}")
            except Exception as e:
                logger.debug(f"Additional catalog {catalog_name} not found: {e}")
        
        return catalogs
    
    def _prepare_embeddings(self) -> Dict[str, Dict]:
        """Prepare searchable embeddings for all codes"""
        embeddings = {}
        
        for system_name in ["bema_codes", "goz_codes", "goae_codes"]:
            system_codes = self.catalogs.get(system_name, {})
            embeddings[system_name] = {}
            
            for code_id, code_info in system_codes.items():
                # Create searchable text combining all relevant fields
                searchable_text = self._create_searchable_text(code_info)
                embeddings[system_name][code_id] = {
                    "text": searchable_text,
                    "keywords": code_info.get("keywords", []),
                    "category": code_info.get("category", ""),
                    "description": code_info.get("description", ""),
                    "code": code_info.get("code", "")
                }
        
        return embeddings
    
    def _create_searchable_text(self, code_info: Dict) -> str:
        """Create comprehensive searchable text for a code"""
        text_parts = []
        
        # Add description
        if "description" in code_info:
            text_parts.append(code_info["description"])
        
        # Add keywords
        if "keywords" in code_info:
            text_parts.extend(code_info["keywords"])
        
        # Add category
        if "category" in code_info:
            text_parts.append(code_info["category"])
        
        # Add subcategory
        if "subcategory" in code_info:
            text_parts.append(code_info["subcategory"])
        
        # Add alternative descriptions
        if "alternatives" in code_info:
            text_parts.extend(code_info["alternatives"])
        
        return " ".join(text_parts).lower()
    
    def retrieve_relevant_codes(
        self, 
        query_text: str, 
        insurance_type: str = "bema",
        max_codes: int = 20,
        relevance_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve most relevant billing codes for given text
        
        Args:
            query_text: Treatment description text
            insurance_type: "bema" or "goz" 
            max_codes: Maximum codes to return
            relevance_threshold: Minimum relevance score
            
        Returns:
            List of relevant billing codes with relevance scores
        """
        query_normalized = self._normalize_query(query_text)
        relevant_codes = []
        
        # Determine which systems to search
        systems_to_search = self._get_systems_for_insurance(insurance_type)
        
        for system_name in systems_to_search:
            system_embeddings = self.code_embeddings.get(system_name, {})
            
            for code_id, embedding_info in system_embeddings.items():
                relevance_score = self._calculate_relevance(
                    query_normalized, 
                    embedding_info
                )
                
                if relevance_score >= relevance_threshold:
                    code_info = self.catalogs[system_name][code_id].copy()
                    code_info["relevance_score"] = relevance_score
                    code_info["system"] = system_name.replace("_codes", "")
                    code_info["retrieval_reason"] = self._get_retrieval_reason(
                        query_normalized, embedding_info
                    )
                    relevant_codes.append(code_info)
        
        # Sort by relevance and return top codes
        relevant_codes.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        logger.info(f"🔍 Retrieved {len(relevant_codes[:max_codes])} relevant codes",
                   query_length=len(query_text),
                   insurance_type=insurance_type,
                   top_relevance=relevant_codes[0]["relevance_score"] if relevant_codes else 0)
        
        return relevant_codes[:max_codes]
    
    def _normalize_query(self, text: str) -> str:
        """Normalize query text for better matching"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize dental terminology
        dental_normalizations = {
            "lokalanästhesie": ["betäubung", "infiltration", "anesthesie"],
            "füllung": ["komposit", "plombe", "füllungstherapie"],
            "extraktion": ["ziehen", "entfernung", "zahnentfernung"],
            "röntgen": ["röntgenbild", "aufnahme", "bildgebung", "zahnfilm"],
            "wurzelbehandlung": ["endodontie", "wurzelkanal", "endo"],
            "parodontitis": ["zahnfleisch", "parodontium", "paro"],
            "prophylaxe": ["zahnreinigung", "pzr", "professionelle"],
            "krone": ["überkronung", "zahnkrone"],
            "implantat": ["implantation", "titan"]
        }
        
        for standard_term, variations in dental_normalizations.items():
            for variation in variations:
                if variation in text:
                    text = text.replace(variation, standard_term)
        
        return text
    
    def _get_systems_for_insurance(self, insurance_type: str) -> List[str]:
        """Get relevant billing systems for insurance type"""
        if insurance_type.lower() == "bema":
            return ["bema_codes", "goz_codes", "goae_codes"]  # BEMA + GOZ/GOÄ for MKV
        else:  # GOZ
            return ["goz_codes", "goae_codes"]  # Only private billing
    
    def _calculate_relevance(self, query: str, embedding_info: Dict) -> float:
        """Calculate relevance score between query and code"""
        relevance_scores = []
        
        # Exact keyword matches (highest weight)
        for keyword in embedding_info["keywords"]:
            if keyword.lower() in query:
                relevance_scores.append(1.0)
        
        # Description similarity
        description_similarity = SequenceMatcher(
            None, 
            query, 
            embedding_info["description"].lower()
        ).ratio()
        relevance_scores.append(description_similarity * 0.8)
        
        # Full text similarity
        text_similarity = SequenceMatcher(
            None, 
            query, 
            embedding_info["text"]
        ).ratio()
        relevance_scores.append(text_similarity * 0.6)
        
        # Category matching
        if embedding_info["category"].lower() in query:
            relevance_scores.append(0.7)
        
        # Return maximum relevance score
        return max(relevance_scores) if relevance_scores else 0.0
    
    def _get_retrieval_reason(self, query: str, embedding_info: Dict) -> str:
        """Get human-readable reason for code retrieval"""
        reasons = []
        
        # Check for exact keyword matches
        matched_keywords = [
            kw for kw in embedding_info["keywords"] 
            if kw.lower() in query
        ]
        if matched_keywords:
            reasons.append(f"Keywords: {', '.join(matched_keywords)}")
        
        # Check for description match
        description_similarity = SequenceMatcher(
            None, query, embedding_info["description"].lower()
        ).ratio()
        if description_similarity > 0.5:
            reasons.append(f"Description match ({description_similarity:.1%})")
        
        # Check for category match
        if embedding_info["category"].lower() in query:
            reasons.append(f"Category: {embedding_info['category']}")
        
        return "; ".join(reasons) if reasons else "General similarity"
    
    def get_catalog_info(self) -> Dict[str, Any]:
        """Get information about loaded catalogs"""
        return {
            "bema_codes_count": len(self.catalogs.get("bema_codes", {})),
            "goz_codes_count": len(self.catalogs.get("goz_codes", {})),
            "goae_codes_count": len(self.catalogs.get("goae_codes", {})),
            "last_updated": self.catalogs.get("meta", {}).get("last_updated", "unknown"),
            "version": self.catalogs.get("meta", {}).get("version", "unknown")
        }
    
    def search_codes_by_category(self, category: str, insurance_type: str = "bema") -> List[Dict]:
        """Search codes by specific category"""
        matching_codes = []
        systems_to_search = self._get_systems_for_insurance(insurance_type)
        
        for system_name in systems_to_search:
            system_codes = self.catalogs.get(system_name, {})
            for code_id, code_info in system_codes.items():
                if code_info.get("category", "").lower() == category.lower():
                    code_copy = code_info.copy()
                    code_copy["system"] = system_name.replace("_codes", "")
                    matching_codes.append(code_copy)
        
        return matching_codes 