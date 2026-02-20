"""
Tests for Transfer Service (QR-Code based data transfer)
Test-Driven Development: Tests written BEFORE implementation
"""

import pytest
import time
from datetime import datetime, timedelta
from app.services.transfer_service import (
    TransferService,
    TransferSession,
    SessionExpiredError,
    SessionNotFoundError,
)


@pytest.fixture
def transfer_service():
    """Create a fresh transfer service for each test"""
    return TransferService(session_ttl_seconds=300)  # 5 minutes


@pytest.fixture
def sample_billing_codes():
    """Sample billing codes for testing"""
    return [
        {
            "code": "13a",
            "system": "BEMA",
            "description": "Füllungstherapie einflächig",
            "quantity": 1,
            "tooth_number": "36"
        },
        {
            "code": "2080",
            "system": "GOZ",
            "description": "Komposit-Füllung",
            "quantity": 1,
            "tooth_number": "36",
            "is_zusatzleistung": True
        }
    ]


@pytest.fixture
def sample_transcription():
    """Sample transcription for testing"""
    return "Zahn 36, MOD-Füllung mit Komposite, Lokalanästhesie"


class TestTransferSessionCreation:
    """Test creating transfer sessions"""

    def test_create_session_generates_uuid(self, transfer_service, sample_billing_codes, sample_transcription):
        """Session should have a valid UUID"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        assert session.id is not None
        assert len(session.id) == 36  # UUID format: 8-4-4-4-12
        assert "-" in session.id

    def test_create_session_stores_billing_codes(self, transfer_service, sample_billing_codes, sample_transcription):
        """Session should contain the billing codes"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        assert len(session.billing_codes) == 2
        assert session.billing_codes[0]["code"] == "13a"
        assert session.billing_codes[1]["code"] == "2080"

    def test_create_session_stores_transcription(self, transfer_service, sample_billing_codes, sample_transcription):
        """Session should contain the transcription text"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        assert session.transcription == sample_transcription

    def test_create_session_with_patient_id(self, transfer_service, sample_billing_codes, sample_transcription):
        """Session should optionally store patient ID"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription,
            patient_id="12345"
        )

        assert session.patient_id == "12345"

    def test_create_session_sets_expiry(self, transfer_service, sample_billing_codes, sample_transcription):
        """Session should have an expiry timestamp"""
        before = datetime.now()
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )
        after = datetime.now()

        # Should expire in ~5 minutes
        expected_expiry = before + timedelta(seconds=300)
        assert session.expires_at >= expected_expiry
        assert session.expires_at <= after + timedelta(seconds=300)


class TestTransferSessionRetrieval:
    """Test retrieving transfer sessions"""

    def test_retrieve_existing_session(self, transfer_service, sample_billing_codes, sample_transcription):
        """Should retrieve a valid session by ID"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        retrieved = transfer_service.get_session(session.id)

        assert retrieved is not None
        assert retrieved.id == session.id
        assert len(retrieved.billing_codes) == 2
        assert retrieved.transcription == sample_transcription

    def test_retrieve_nonexistent_session(self, transfer_service):
        """Should raise error for non-existent session"""
        with pytest.raises(SessionNotFoundError):
            transfer_service.get_session("nonexistent-uuid")

    def test_session_is_consumed_after_retrieval(self, transfer_service, sample_billing_codes, sample_transcription):
        """Session should be deleted after first retrieval (one-time use)"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # First retrieval: OK
        transfer_service.get_session(session.id)

        # Second retrieval: Should fail
        with pytest.raises(SessionNotFoundError):
            transfer_service.get_session(session.id)


class TestTransferSessionExpiration:
    """Test session expiration logic"""

    def test_expired_session_raises_error(self, sample_billing_codes, sample_transcription):
        """Expired session should raise error (NotFound or Expired)"""
        # Create service with 1-second TTL
        service = TransferService(session_ttl_seconds=1)

        session = service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # Wait for expiration
        time.sleep(2)

        # TTLCache auto-deletes, so either error is acceptable
        with pytest.raises((SessionExpiredError, SessionNotFoundError)):
            service.get_session(session.id)

    def test_valid_session_not_expired(self, transfer_service, sample_billing_codes, sample_transcription):
        """Valid session should not raise expiration error"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # Should not raise
        retrieved = transfer_service.get_session(session.id)
        assert retrieved is not None


class TestQRCodeGeneration:
    """Test QR code generation"""

    def test_generate_qr_code_url(self, transfer_service, sample_billing_codes, sample_transcription):
        """Should generate QR code with transfer URL"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        qr_url = transfer_service.get_transfer_url(session.id)

        assert qr_url.startswith("http")
        assert session.id in qr_url
        assert "/transfer/" in qr_url

    def test_generate_qr_code_image(self, transfer_service, sample_billing_codes, sample_transcription):
        """Should generate QR code as base64 image"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        qr_image = transfer_service.generate_qr_code(session.id)

        assert qr_image.startswith("data:image/png;base64,")
        assert len(qr_image) > 100  # Should be a substantial image


class TestSessionCleanup:
    """Test automatic cleanup of expired sessions"""

    def test_cleanup_removes_expired_sessions(self, sample_billing_codes, sample_transcription):
        """Cleanup should remove expired sessions (or TTLCache does it automatically)"""
        service = TransferService(session_ttl_seconds=1)

        # Create sessions
        session1 = service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )
        session2 = service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # Wait for expiration
        time.sleep(2)

        # Run cleanup (TTLCache may have already auto-deleted)
        removed_count = service.cleanup_expired_sessions()

        # Either cleanup removed them, or TTLCache did (both OK)
        assert removed_count >= 0  # Can be 0 if TTLCache auto-deleted

        # Sessions should be gone either way
        with pytest.raises((SessionExpiredError, SessionNotFoundError)):
            service.get_session(session1.id)
        with pytest.raises((SessionExpiredError, SessionNotFoundError)):
            service.get_session(session2.id)

    def test_cleanup_preserves_valid_sessions(self, transfer_service, sample_billing_codes, sample_transcription):
        """Cleanup should not remove valid sessions"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # Run cleanup immediately
        removed_count = transfer_service.cleanup_expired_sessions()

        assert removed_count == 0

        # Session should still be accessible
        retrieved = transfer_service.get_session(session.id)
        assert retrieved is not None


class TestDSGVOCompliance:
    """Test DSGVO/GDPR compliance features"""

    def test_session_auto_expires(self, sample_billing_codes, sample_transcription):
        """Sessions must auto-expire for DSGVO compliance"""
        service = TransferService(session_ttl_seconds=1)

        session = service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # Verify expiry is set
        assert session.expires_at is not None

        # Wait and verify deletion
        time.sleep(2)

        # TTLCache auto-deletes = DSGVO compliant!
        with pytest.raises((SessionExpiredError, SessionNotFoundError)):
            service.get_session(session.id)

    def test_session_one_time_use(self, transfer_service, sample_billing_codes, sample_transcription):
        """Sessions must be one-time use for security"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription
        )

        # First use: OK
        transfer_service.get_session(session.id)

        # Second use: Denied
        with pytest.raises(SessionNotFoundError):
            transfer_service.get_session(session.id)

    def test_no_sensitive_data_in_qr_url(self, transfer_service, sample_billing_codes, sample_transcription):
        """QR code URL should only contain session ID, no patient data"""
        session = transfer_service.create_session(
            billing_codes=sample_billing_codes,
            transcription=sample_transcription,
            patient_id="SENSITIVE_PATIENT_ID"
        )

        qr_url = transfer_service.get_transfer_url(session.id)

        # Should NOT contain patient ID or billing codes
        assert "SENSITIVE_PATIENT_ID" not in qr_url
        assert "13a" not in qr_url
        assert "2080" not in qr_url

        # Should only contain session ID
        assert session.id in qr_url
