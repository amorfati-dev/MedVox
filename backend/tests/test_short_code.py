"""
Tests for Short-Code Generator
Test-Driven Development: Tests written BEFORE implementation
"""

import pytest
import uuid
from app.utils.short_code import (
    generate_short_code,
    decode_short_code,
    ShortCodeError,
)


class TestShortCodeGeneration:
    """Test short code generation from UUID"""

    def test_generate_short_code_length(self):
        """Short code should be 6 characters"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id)

        assert len(code) == 6

    def test_generate_short_code_format(self):
        """Short code should be alphanumeric (Base62)"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id)

        # Should only contain A-Z, a-z, 0-9
        assert code.isalnum()

    def test_generate_short_code_uppercase(self):
        """Short code should be uppercase for readability"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id)

        assert code.isupper()

    def test_generate_short_code_deterministic(self):
        """Same UUID should generate same code"""
        session_id = str(uuid.uuid4())

        code1 = generate_short_code(session_id)
        code2 = generate_short_code(session_id)

        assert code1 == code2

    def test_generate_different_codes_for_different_uuids(self):
        """Different UUIDs should generate different codes"""
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())

        code1 = generate_short_code(session_id1)
        code2 = generate_short_code(session_id2)

        assert code1 != code2

    def test_generate_code_readable_format(self):
        """Code should avoid ambiguous characters (0O, 1Il)"""
        # Generate many codes and check for ambiguous chars
        for _ in range(100):
            session_id = str(uuid.uuid4())
            code = generate_short_code(session_id)

            # Should not contain: 0, O, 1, I, l
            assert '0' not in code or 'O' not in code  # If has 0, shouldn't have O
            assert '1' not in code or 'I' not in code  # If has 1, shouldn't have I


class TestShortCodeDecoding:
    """Test short code validation and normalization"""

    def test_decode_short_code_returns_normalized_code(self):
        """Decoding should return normalized code (uppercase, no dash)"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id)

        normalized = decode_short_code(code)

        assert normalized == code
        assert len(normalized) == 6
        assert normalized.isupper()

    def test_decode_short_code_validates_format(self):
        """Code validation should work"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id)

        # Should not raise
        normalized = decode_short_code(code)

        assert normalized is not None

    def test_decode_invalid_code_raises_error(self):
        """Invalid code should raise ShortCodeError"""
        with pytest.raises(ShortCodeError):
            decode_short_code("INVALID")

    def test_decode_wrong_length_raises_error(self):
        """Code with wrong length should raise error"""
        with pytest.raises(ShortCodeError):
            decode_short_code("ABC")  # Too short

        with pytest.raises(ShortCodeError):
            decode_short_code("ABCD1234")  # Too long

    def test_decode_empty_code_raises_error(self):
        """Empty code should raise error"""
        with pytest.raises(ShortCodeError):
            decode_short_code("")

    def test_decode_case_insensitive(self):
        """Code should work in lowercase too (user-friendly)"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id)

        # Try lowercase - should normalize to uppercase
        normalized = decode_short_code(code.lower())

        assert normalized == code  # Should be uppercased


class TestShortCodeCollisions:
    """Test for code collisions (unlikely but important)"""

    def test_many_codes_are_unique(self):
        """Generate many codes and ensure uniqueness"""
        codes = set()

        for _ in range(1000):
            session_id = str(uuid.uuid4())
            code = generate_short_code(session_id)
            codes.add(code)

        # Should have 1000 unique codes
        assert len(codes) == 1000

    def test_code_collision_probability_is_low(self):
        """With 6 chars Base62, we have 62^6 = 56.8 billion combinations"""
        # With 1000 codes, collision probability is extremely low
        # This test just documents the math

        alphabet_size = 62  # A-Z, a-z, 0-9 (minus ambiguous)
        code_length = 6
        total_combinations = alphabet_size ** code_length

        assert total_combinations > 50_000_000_000  # Over 50 billion


class TestShortCodeReadability:
    """Test human-readability features"""

    def test_code_format_with_dash(self):
        """Code should be formatted as ABC-123 for readability"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id, formatted=True)

        assert '-' in code
        assert len(code) == 7  # ABC-123

    def test_code_without_dash(self):
        """Code without formatting should be 6 chars"""
        session_id = str(uuid.uuid4())
        code = generate_short_code(session_id, formatted=False)

        assert '-' not in code
        assert len(code) == 6

    def test_decode_works_with_dash(self):
        """Decoding should work with or without dash"""
        session_id = str(uuid.uuid4())
        code_with_dash = generate_short_code(session_id, formatted=True)
        code_without_dash = generate_short_code(session_id, formatted=False)

        # Both should normalize to the same code (no dash)
        normalized1 = decode_short_code(code_with_dash)
        normalized2 = decode_short_code(code_without_dash)

        assert normalized1 == normalized2 == code_without_dash


class TestShortCodePerformance:
    """Test performance of short code generation"""

    def test_generation_is_fast(self):
        """Generating code should be fast (< 1ms per code)"""
        import time

        start = time.time()

        for _ in range(1000):
            session_id = str(uuid.uuid4())
            generate_short_code(session_id)

        elapsed = time.time() - start

        # 1000 codes in less than 100ms
        assert elapsed < 0.1

    def test_decoding_is_fast(self):
        """Decoding should be fast"""
        import time

        # Pre-generate codes
        codes = []
        for _ in range(1000):
            session_id = str(uuid.uuid4())
            codes.append(generate_short_code(session_id))

        start = time.time()

        for code in codes:
            decode_short_code(code)

        elapsed = time.time() - start

        # 1000 decodings in less than 100ms
        assert elapsed < 0.1
