"""
LLM Logging Utility
Logs prompts and responses for debugging and optimization
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class LLMLogger:
    """Logger for LLM prompts and responses"""
    
    def __init__(self, log_dir: str = "logs/llm_interactions"):
        self.log_dir = log_dir
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """Ensure the log directory exists"""
        os.makedirs(self.log_dir, exist_ok=True)
    
    def log_interaction(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response: str,
        insurance_type: str = "unknown",
        patient_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a complete LLM interaction
        
        Args:
            model: LLM model used
            system_prompt: System prompt sent
            user_prompt: User prompt sent  
            response: LLM response received
            insurance_type: BEMA or GOZ
            patient_id: Patient identifier if available
            processing_time_ms: Processing time in milliseconds
            metadata: Additional metadata
        """
        
        timestamp = datetime.now()
        interaction_id = f"llm_{timestamp.strftime('%Y%m%d_%H%M%S')}_{hash(user_prompt) % 10000:04d}"
        
        # Create structured log entry
        log_entry = {
            "interaction_id": interaction_id,
            "timestamp": timestamp.isoformat(),
            "model": model,
            "insurance_type": insurance_type,
            "patient_id": patient_id,
            "processing_time_ms": processing_time_ms,
            "prompts": {
                "system": system_prompt,
                "user": user_prompt
            },
            "response": response,
            "metadata": metadata or {}
        }
        
        # Log to structured logger
        logger.info("LLM Interaction",
                   interaction_id=interaction_id,
                   model=model,
                   insurance_type=insurance_type,
                   user_prompt_length=len(user_prompt),
                   response_length=len(response),
                   processing_time_ms=processing_time_ms)
        
        # Save detailed log to file
        self._save_to_file(interaction_id, log_entry)
        
        # Also save human-readable version
        self._save_human_readable(interaction_id, log_entry)
    
    def _save_to_file(self, interaction_id: str, log_entry: Dict[str, Any]):
        """Save structured log entry to JSON file"""
        try:
            filename = f"{interaction_id}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
                
            logger.debug("LLM interaction saved to file", filepath=filepath)
            
        except Exception as e:
            logger.error("Failed to save LLM interaction to file", error=str(e))
    
    def _save_human_readable(self, interaction_id: str, log_entry: Dict[str, Any]):
        """Save human-readable version for easy review"""
        try:
            filename = f"{interaction_id}.txt"
            filepath = os.path.join(self.log_dir, filename)
            
            content = f"""
=== MedVox LLM Interaction Log ===
ID: {interaction_id}
Timestamp: {log_entry['timestamp']}
Model: {log_entry['model']}
Insurance Type: {log_entry['insurance_type']}
Patient ID: {log_entry['patient_id']}
Processing Time: {log_entry['processing_time_ms']}ms

=== SYSTEM PROMPT ===
{log_entry['prompts']['system']}

=== USER PROMPT ===
{log_entry['prompts']['user']}

=== LLM RESPONSE ===
{log_entry['response']}

=== METADATA ===
{json.dumps(log_entry['metadata'], indent=2, ensure_ascii=False)}
"""
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            logger.error("Failed to save human-readable LLM log", error=str(e))
    
    def get_recent_interactions(self, limit: int = 10) -> list:
        """Get recent LLM interactions for analysis"""
        try:
            files = []
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.log_dir, filename)
                    files.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time, newest first
            files.sort(key=lambda x: x[1], reverse=True)
            
            interactions = []
            for filepath, _ in files[:limit]:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        interaction = json.load(f)
                        interactions.append(interaction)
                except Exception as e:
                    logger.warning("Failed to load interaction file", filepath=filepath, error=str(e))
            
            return interactions
            
        except Exception as e:
            logger.error("Failed to get recent interactions", error=str(e))
            return []


# Global LLM logger instance
llm_logger = LLMLogger() 