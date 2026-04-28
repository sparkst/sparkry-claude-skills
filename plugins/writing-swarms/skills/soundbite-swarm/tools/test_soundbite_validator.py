#!/usr/bin/env python3
"""
Tests for soundbite-validator.py

REQ-SV-001: Validate soundbites against quality gates
REQ-SV-002: Authenticity >= 60 (hard gate)
REQ-SV-003: Brevity >= 50 (max 7 words)
REQ-SV-004: Overall >= 75 to advance
REQ-SV-005: Detect and block banned cliches
"""

import pytest
import sys
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class TestValidationGates:
    """Test quality gate validation logic."""

    # ==================== HAPPY PATH TESTS ====================

    def test_valid_soundbite_passes_all_gates(self):
        """REQ-SV-001: Valid soundbite passes all gates."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Think Different",
            "scores": {
                "memorability": 90,
                "emotional_resonance": 85,
                "brevity": 95,
                "rhythm": 88,
                "universality": 82,
                "action_potential": 80,
                "authenticity": 88,
                "overall": 87
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is True
        assert len(result["failed_gates"]) == 0

    def test_soundbite_with_high_scores_passes(self):
        """REQ-SV-001: Soundbite with overall=80, auth=70, brevity=75 passes."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Just Do It",
            "scores": {
                "memorability": 80,
                "emotional_resonance": 80,
                "brevity": 75,
                "rhythm": 80,
                "universality": 80,
                "action_potential": 80,
                "authenticity": 70,
                "overall": 80
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is True

    def test_returns_failed_gates_when_rejected(self):
        """REQ-SV-001: Returns list of failed gates when rejected."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "This is a very long soundbite that exceeds seven words easily",
            "scores": {
                "memorability": 50,
                "emotional_resonance": 50,
                "brevity": 20,  # Fails < 50
                "rhythm": 50,
                "universality": 50,
                "action_potential": 50,
                "authenticity": 55,  # Fails < 60
                "overall": 50  # Fails < 75
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        assert len(result["failed_gates"]) == 4  # authenticity, brevity, overall, word_count

        gate_names = [g["gate"] for g in result["failed_gates"]]
        assert "authenticity" in gate_names
        assert "brevity" in gate_names
        assert "overall" in gate_names
        assert "word_count" in gate_names  # 11 words exceeds 7-word limit

    # ==================== EDGE CASE TESTS ====================

    def test_overall_exactly_75_passes(self):
        """REQ-SV-004: Overall score of exactly 75 (threshold) passes."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Test Boundary",
            "scores": {
                "memorability": 75,
                "emotional_resonance": 75,
                "brevity": 75,
                "rhythm": 75,
                "universality": 75,
                "action_potential": 75,
                "authenticity": 75,
                "overall": 75
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is True

    def test_authenticity_59_fails(self):
        """REQ-SV-002: Authenticity of 59 (just below threshold) fails."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Test Auth",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 85,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 59,  # Just below 60
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        assert len(result["failed_gates"]) == 1
        assert result["failed_gates"][0]["gate"] == "authenticity"
        assert result["failed_gates"][0]["threshold"] == 60
        assert result["failed_gates"][0]["actual"] == 59

    def test_authenticity_exactly_60_passes(self):
        """REQ-SV-002: Authenticity of exactly 60 passes."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Test Auth Pass",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 85,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 60,  # Exactly 60
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        # Should pass authenticity gate
        auth_failures = [g for g in result["failed_gates"] if g["gate"] == "authenticity"]
        assert len(auth_failures) == 0

    def test_brevity_exactly_50_passes(self):
        """REQ-SV-003: Brevity of exactly 50 passes (boundary)."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Test",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 50,  # Exactly at threshold
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        brevity_failures = [g for g in result["failed_gates"] if g["gate"] == "brevity"]
        assert len(brevity_failures) == 0

    def test_7_words_exactly_passes_brevity(self):
        """REQ-SV-003: Soundbite with 7 words exactly passes brevity check."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "This Is What We All Live For",  # 7 words
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 50,  # 7 words should be able to score 40+
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        # Word count check should pass (7 is max allowed)
        word_count_failures = [g for g in result.get("failed_gates", [])
                               if g.get("gate") == "word_count"]
        assert len(word_count_failures) == 0

    def test_8_words_fails_brevity(self):
        """REQ-SV-003: Soundbite with 8+ words fails word count check."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "This Is What We Are All Living For Now",  # 9 words
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 20,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 75
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        # Should fail word_count gate
        word_count_failures = [g for g in result["failed_gates"]
                               if g.get("gate") == "word_count"]
        assert len(word_count_failures) == 1


class TestClicheDetection:
    """Test banned cliche detection."""

    def test_unlock_potential_detected(self):
        """REQ-SV-005: 'unlock potential' cliche is detected."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Unlock Your Potential",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 90,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        cliche_failures = [g for g in result["failed_gates"] if g["gate"] == "cliche"]
        assert len(cliche_failures) == 1
        assert "unlock" in cliche_failures[0]["matched_cliche"].lower()

    def test_next_level_detected(self):
        """REQ-SV-005: 'next level' cliche is detected."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Take It Next Level",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 90,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        cliche_failures = [g for g in result["failed_gates"] if g["gate"] == "cliche"]
        assert len(cliche_failures) == 1

    def test_be_the_best_you_detected(self):
        """REQ-SV-005: 'be the best you' cliche is detected."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Be The Best You",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 90,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False

    def test_case_insensitive_cliche_detection(self):
        """REQ-SV-005: Cliche detection is case-insensitive."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "UNLOCK POTENTIAL NOW",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 90,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        cliche_failures = [g for g in result["failed_gates"] if g["gate"] == "cliche"]
        assert len(cliche_failures) == 1

    def test_valid_soundbite_no_cliches(self):
        """REQ-SV-005: Valid soundbite without cliches passes."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Just Do It",  # Not a cliche in our blocklist
            "scores": {
                "memorability": 90,
                "emotional_resonance": 90,
                "brevity": 100,
                "rhythm": 90,
                "universality": 90,
                "action_potential": 95,
                "authenticity": 90,
                "overall": 92
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is True
        cliche_failures = [g for g in result.get("failed_gates", []) if g.get("gate") == "cliche"]
        assert len(cliche_failures) == 0


class TestBatchValidation:
    """Test batch validation functionality."""

    def test_validate_batch_filters_invalid(self):
        """Batch validation filters out invalid soundbites."""
        from soundbite_validator import validate_batch

        soundbites = [
            {
                "soundbite": "Think Different",
                "scores": {"memorability": 90, "emotional_resonance": 90, "brevity": 95,
                          "rhythm": 90, "universality": 90, "action_potential": 90,
                          "authenticity": 90, "overall": 90}
            },
            {
                "soundbite": "Unlock Your Potential Today",  # Cliche
                "scores": {"memorability": 80, "emotional_resonance": 80, "brevity": 75,
                          "rhythm": 80, "universality": 80, "action_potential": 80,
                          "authenticity": 80, "overall": 80}
            },
            {
                "soundbite": "Just Do It",
                "scores": {"memorability": 95, "emotional_resonance": 90, "brevity": 100,
                          "rhythm": 92, "universality": 95, "action_potential": 98,
                          "authenticity": 90, "overall": 93}
            }
        ]

        result = validate_batch(soundbites)

        assert result["total"] == 3
        assert result["valid_count"] == 2
        assert result["invalid_count"] == 1
        assert len(result["valid_soundbites"]) == 2
        assert len(result["invalid_soundbites"]) == 1

    # ==================== FAILURE PATH TESTS ====================

    def test_missing_scores_raises_validationerror(self):
        """REQ-SV-001: Missing scores object raises ValidationError."""
        from soundbite_validator import validate_soundbite, ValidationError

        soundbite = {
            "soundbite": "Test",
            # Missing "scores" key
        }

        with pytest.raises(ValidationError, match="scores"):
            validate_soundbite(soundbite)

    def test_scores_not_numeric_raises_typeerror(self):
        """REQ-SV-001: Non-numeric scores raise TypeError."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "Test",
            "scores": {
                "memorability": "high",  # Should be numeric
                "emotional_resonance": 85,
                "brevity": 85,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        with pytest.raises(TypeError, match="numeric"):
            validate_soundbite(soundbite)

    def test_none_soundbite_raises_valueerror(self):
        """REQ-SV-001: None soundbite text raises ValueError."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": None,
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 85,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        with pytest.raises(ValueError, match="soundbite text"):
            validate_soundbite(soundbite)

    def test_empty_string_soundbite_fails_brevity(self):
        """REQ-SV-003: Empty string soundbite fails brevity check."""
        from soundbite_validator import validate_soundbite

        soundbite = {
            "soundbite": "",
            "scores": {
                "memorability": 85,
                "emotional_resonance": 85,
                "brevity": 0,
                "rhythm": 85,
                "universality": 85,
                "action_potential": 85,
                "authenticity": 85,
                "overall": 85
            }
        }

        result = validate_soundbite(soundbite)

        assert result["valid"] is False
        # Should have word_count failure
        failures = [g for g in result["failed_gates"] if g.get("gate") == "word_count"]
        assert len(failures) == 1


class TestClicheBlocklist:
    """Test the cliche blocklist configuration."""

    def test_blocklist_contains_required_cliches(self):
        """Blocklist should contain all required banned phrases."""
        from soundbite_validator import CLICHE_BLOCKLIST

        required_cliches = [
            "unlock potential",
            "next level",
            "be the best you",
            "game changer",
            "paradigm shift",
            "think outside the box",
            "move the needle",
            "low-hanging fruit",
            "synergy",
            "leverage"
        ]

        for cliche in required_cliches:
            assert any(cliche in blocked.lower() for blocked in CLICHE_BLOCKLIST), \
                f"'{cliche}' should be in blocklist"

    def test_blocklist_is_not_empty(self):
        """Blocklist should not be empty."""
        from soundbite_validator import CLICHE_BLOCKLIST

        assert len(CLICHE_BLOCKLIST) >= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
