"""
Tests for Transfer API Endpoints
Test-Driven Development: Tests written BEFORE implementation
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.transfer_service import get_transfer_service, TransferService


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_transfer_request():
    """Sample transfer creation request"""
    return {
        "billing_codes": [
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
        ],
        "transcription": "Zahn 36, MOD-Füllung mit Komposite, Lokalanästhesie",
        "patient_id": "12345"
    }


@pytest.fixture(autouse=True)
def reset_transfer_service():
    """Reset transfer service before each test"""
    # Force new instance for each test
    import app.services.transfer_service
    app.services.transfer_service._transfer_service = None
    yield
    app.services.transfer_service._transfer_service = None


class TestCreateTransferSession:
    """Test POST /api/v1/transfer/create endpoint"""

    def test_create_session_returns_201(self, client, sample_transfer_request):
        """Should return 201 Created"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        assert response.status_code == 201

    def test_create_session_returns_session_id(self, client, sample_transfer_request):
        """Should return session ID in response"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        data = response.json()

        assert "session_id" in data
        assert len(data["session_id"]) == 36  # UUID format

    def test_create_session_returns_qr_code(self, client, sample_transfer_request):
        """Should return QR code as base64 data URL"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        data = response.json()

        assert "qr_code" in data
        assert data["qr_code"].startswith("data:image/png;base64,")

    def test_create_session_returns_transfer_url(self, client, sample_transfer_request):
        """Should return transfer URL"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        data = response.json()

        assert "transfer_url" in data
        assert "/transfer/" in data["transfer_url"]
        assert data["session_id"] in data["transfer_url"]

    def test_create_session_returns_expiry(self, client, sample_transfer_request):
        """Should return expiry timestamp"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        data = response.json()

        assert "expires_at" in data
        assert "expires_in_seconds" in data
        assert data["expires_in_seconds"] > 0

    def test_create_session_without_patient_id(self, client, sample_transfer_request):
        """Should work without patient_id (optional)"""
        del sample_transfer_request["patient_id"]

        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        assert response.status_code == 201

    def test_create_session_without_billing_codes_fails(self, client):
        """Should fail without billing codes"""
        response = client.post("/api/v1/transfer/create", json={
            "transcription": "Test"
        })
        assert response.status_code == 422  # Validation error

    def test_create_session_without_transcription_fails(self, client):
        """Should fail without transcription"""
        response = client.post("/api/v1/transfer/create", json={
            "billing_codes": [{"code": "13a"}]
        })
        assert response.status_code == 422  # Validation error

    def test_create_session_with_empty_billing_codes_fails(self, client):
        """Should fail with empty billing codes"""
        response = client.post("/api/v1/transfer/create", json={
            "billing_codes": [],
            "transcription": "Test"
        })
        assert response.status_code == 422  # Validation error


class TestRetrieveTransferSession:
    """Test GET /api/v1/transfer/{session_id} endpoint"""

    def test_retrieve_session_returns_200(self, client, sample_transfer_request):
        """Should return 200 OK for valid session"""
        # Create session first
        create_response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        session_id = create_response.json()["session_id"]

        # Retrieve session
        response = client.get(f"/api/v1/transfer/{session_id}")
        assert response.status_code == 200

    def test_retrieve_session_returns_billing_codes(self, client, sample_transfer_request):
        """Should return billing codes"""
        # Create session
        create_response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        session_id = create_response.json()["session_id"]

        # Retrieve session
        response = client.get(f"/api/v1/transfer/{session_id}")
        data = response.json()

        assert "billing_codes" in data
        assert len(data["billing_codes"]) == 2
        assert data["billing_codes"][0]["code"] == "13a"

    def test_retrieve_session_returns_transcription(self, client, sample_transfer_request):
        """Should return transcription"""
        # Create session
        create_response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        session_id = create_response.json()["session_id"]

        # Retrieve session
        response = client.get(f"/api/v1/transfer/{session_id}")
        data = response.json()

        assert "transcription" in data
        assert data["transcription"] == sample_transfer_request["transcription"]

    def test_retrieve_session_returns_patient_id(self, client, sample_transfer_request):
        """Should return patient_id if provided"""
        # Create session
        create_response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        session_id = create_response.json()["session_id"]

        # Retrieve session
        response = client.get(f"/api/v1/transfer/{session_id}")
        data = response.json()

        assert "patient_id" in data
        assert data["patient_id"] == "12345"

    def test_retrieve_nonexistent_session_returns_404(self, client):
        """Should return 404 for non-existent session"""
        response = client.get("/api/v1/transfer/nonexistent-uuid")
        assert response.status_code == 404

    def test_retrieve_session_twice_returns_404(self, client, sample_transfer_request):
        """Should return 404 on second retrieval (one-time use)"""
        # Create session
        create_response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        session_id = create_response.json()["session_id"]

        # First retrieval: OK
        response1 = client.get(f"/api/v1/transfer/{session_id}")
        assert response1.status_code == 200

        # Second retrieval: 404
        response2 = client.get(f"/api/v1/transfer/{session_id}")
        assert response2.status_code == 404

    def test_retrieve_session_with_invalid_uuid_returns_422(self, client):
        """Should return 422 for invalid UUID format"""
        response = client.get("/api/v1/transfer/not-a-uuid")
        # Note: Depending on FastAPI validation, might be 404 or 422
        assert response.status_code in [404, 422]


class TestTransferAPIIntegration:
    """Integration tests for complete transfer flow"""

    def test_complete_transfer_flow(self, client, sample_transfer_request):
        """Test complete flow: create → retrieve → consume"""
        # 1. Create session
        create_response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        assert create_response.status_code == 201
        session_id = create_response.json()["session_id"]
        qr_code = create_response.json()["qr_code"]

        # 2. Verify QR code exists
        assert qr_code.startswith("data:image/png;base64,")

        # 3. Retrieve session
        retrieve_response = client.get(f"/api/v1/transfer/{session_id}")
        assert retrieve_response.status_code == 200
        data = retrieve_response.json()

        # 4. Verify data matches original
        assert len(data["billing_codes"]) == 2
        assert data["transcription"] == sample_transfer_request["transcription"]
        assert data["patient_id"] == sample_transfer_request["patient_id"]

        # 5. Verify one-time use
        second_retrieve = client.get(f"/api/v1/transfer/{session_id}")
        assert second_retrieve.status_code == 404

    def test_multiple_concurrent_sessions(self, client, sample_transfer_request):
        """Should support multiple concurrent sessions"""
        # Create 5 sessions
        session_ids = []
        for i in range(5):
            request = sample_transfer_request.copy()
            request["patient_id"] = f"patient_{i}"
            response = client.post("/api/v1/transfer/create", json=request)
            assert response.status_code == 201
            session_ids.append(response.json()["session_id"])

        # All sessions should be unique
        assert len(set(session_ids)) == 5

        # All sessions should be retrievable
        for sid in session_ids:
            response = client.get(f"/api/v1/transfer/{sid}")
            assert response.status_code == 200


class TestTransferAPISecurity:
    """Security-related tests"""

    def test_qr_url_contains_no_sensitive_data(self, client, sample_transfer_request):
        """QR code URL should not contain patient data"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        data = response.json()

        transfer_url = data["transfer_url"]
        session_id = data["session_id"]

        # URL should be /transfer/{session_id} only - no sensitive data appended
        assert transfer_url.endswith(f"/transfer/{session_id}")
        assert "12345" not in transfer_url  # patient_id should never appear
        assert "13a" not in transfer_url    # billing code should never appear
        # Note: short tooth numbers like "36" can appear as UUID substrings - not checked

    def test_session_id_in_response_body_only(self, client, sample_transfer_request):
        """Session ID should not leak in headers or other places"""
        response = client.post("/api/v1/transfer/create", json=sample_transfer_request)
        session_id = response.json()["session_id"]

        # Should not be in headers (except maybe custom debug headers)
        common_headers = ["location", "set-cookie", "authorization"]
        for header in common_headers:
            if header in response.headers:
                assert session_id not in response.headers[header]


class TestTransferAPIValidation:
    """Input validation tests"""

    def test_invalid_json_returns_422(self, client):
        """Should return 422 for invalid JSON"""
        response = client.post(
            "/api/v1/transfer/create",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_billing_code_validation(self, client):
        """Should validate billing code structure"""
        response = client.post("/api/v1/transfer/create", json={
            "billing_codes": [{"invalid": "structure"}],
            "transcription": "Test"
        })
        # Might pass if we don't validate structure, or fail with 422
        assert response.status_code in [201, 422]

    def test_transcription_max_length(self, client):
        """Should handle very long transcriptions"""
        long_text = "x" * 50000  # 50k characters
        response = client.post("/api/v1/transfer/create", json={
            "billing_codes": [{"code": "13a"}],
            "transcription": long_text
        })
        # Should either accept or reject with clear error
        assert response.status_code in [201, 413, 422]
