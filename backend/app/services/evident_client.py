"""
Evident PMS Integration Client
Interface for communicating with Evident practice management system
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()


class EvidentPatient:
    """Patient data structure for Evident"""
    
    def __init__(
        self,
        patient_id: str,
        first_name: str,
        last_name: str,
        birth_date: Optional[datetime] = None,
        insurance_number: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[Dict[str, str]] = None,
    ):
        self.patient_id = patient_id
        self.first_name = first_name
        self.last_name = last_name
        self.birth_date = birth_date
        self.insurance_number = insurance_number
        self.phone = phone
        self.email = email
        self.address = address or {}


class EvidentTreatment:
    """Treatment data structure for Evident"""
    
    def __init__(
        self,
        treatment_id: str,
        patient_id: str,
        treatment_date: datetime,
        diagnosis: Optional[str] = None,
        notes: Optional[str] = None,
        codes: Optional[List[str]] = None,
    ):
        self.treatment_id = treatment_id
        self.patient_id = patient_id
        self.treatment_date = treatment_date
        self.diagnosis = diagnosis
        self.notes = notes
        self.codes = codes or []


class EvidentClient(ABC):
    """
    Abstract base class for Evident PMS integration
    Implements adapter pattern for different Evident API versions
    """
    
    def __init__(self, api_url: str, api_key: str, client_id: Optional[str] = None):
        self.api_url = api_url
        self.api_key = api_key
        self.client_id = client_id
        self.logger = logger.bind(service="evident_client")
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to Evident API"""
        pass
    
    @abstractmethod
    async def get_patient(self, patient_id: str) -> Optional[EvidentPatient]:
        """Retrieve patient data from Evident"""
        pass
    
    @abstractmethod
    async def search_patients(self, query: str) -> List[EvidentPatient]:
        """Search for patients in Evident"""
        pass
    
    @abstractmethod
    async def create_treatment(self, treatment: EvidentTreatment) -> bool:
        """Create a new treatment record in Evident"""
        pass
    
    @abstractmethod
    async def update_treatment(self, treatment_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing treatment record"""
        pass
    
    @abstractmethod
    async def get_medical_codes(self) -> List[Dict[str, str]]:
        """Get available medical codes (GOZ/BEMA) from Evident"""
        pass
    
    @abstractmethod
    async def export_document(self, treatment_id: str, document_content: str) -> bool:
        """Export document content to Evident"""
        pass


class EvidentClientV1(EvidentClient):
    """
    Implementation for Evident API v1
    Placeholder implementation - to be filled with actual API calls
    """
    
    async def test_connection(self) -> bool:
        """Test connection to Evident API"""
        self.logger.info("Testing Evident API connection", api_url=self.api_url)
        # TODO: Implement actual API connection test
        return True
    
    async def get_patient(self, patient_id: str) -> Optional[EvidentPatient]:
        """Retrieve patient data from Evident"""
        self.logger.info("Fetching patient from Evident", patient_id=patient_id)
        # TODO: Implement actual API call to get patient
        return None
    
    async def search_patients(self, query: str) -> List[EvidentPatient]:
        """Search for patients in Evident"""
        self.logger.info("Searching patients in Evident", query=query)
        # TODO: Implement actual API call to search patients
        return []
    
    async def create_treatment(self, treatment: EvidentTreatment) -> bool:
        """Create a new treatment record in Evident"""
        self.logger.info("Creating treatment in Evident", 
                        treatment_id=treatment.treatment_id,
                        patient_id=treatment.patient_id)
        # TODO: Implement actual API call to create treatment
        return True
    
    async def update_treatment(self, treatment_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing treatment record"""
        self.logger.info("Updating treatment in Evident", 
                        treatment_id=treatment_id,
                        updates=updates)
        # TODO: Implement actual API call to update treatment
        return True
    
    async def get_medical_codes(self) -> List[Dict[str, str]]:
        """Get available medical codes (GOZ/BEMA) from Evident"""
        self.logger.info("Fetching medical codes from Evident")
        # TODO: Implement actual API call to get medical codes
        return []
    
    async def export_document(self, treatment_id: str, document_content: str) -> bool:
        """Export document content to Evident"""
        self.logger.info("Exporting document to Evident", 
                        treatment_id=treatment_id,
                        content_length=len(document_content))
        # TODO: Implement actual API call to export document
        return True


class EvidentClientFactory:
    """Factory for creating Evident client instances"""
    
    @staticmethod
    def create_client(
        api_url: str, 
        api_key: str, 
        client_id: Optional[str] = None,
        version: str = "v1"
    ) -> EvidentClient:
        """Create Evident client based on version"""
        
        if version == "v1":
            return EvidentClientV1(api_url, api_key, client_id)
        else:
            raise ValueError(f"Unsupported Evident API version: {version}") 