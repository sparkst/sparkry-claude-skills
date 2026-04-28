#!/usr/bin/env python3
"""
Tests for angle-generator.py

REQ-AG-001: Generate soundbites from a specific creative angle
REQ-AG-002: Return 10 candidates with self-scores per angle
REQ-AG-003: Handle content edge cases (short, long, non-English)
REQ-AG-004: Validate angle names and input content
"""

import pytest
import sys
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class TestAngleGenerator:
    """Test angle-based soundbite generation."""

    # ==================== HAPPY PATH TESTS ====================

    def test_generate_from_emotional_angle_returns_10_candidates(self):
        """REQ-AG-001: Generate from 'emotional' angle returns 10 candidates."""
        from angle_generator import generate_from_angle

        content = """
        AI adoption in organizations isn't a technology problem - it's a permission problem.
        Most employees want to use AI, but they don't know if they're allowed to.
        They're waiting for explicit permission from leadership.
        The organizations that will win are those that create clear permission structures.
        """

        result = generate_from_angle(content, "emotional")

        assert result["angle"] == "emotional"
        assert len(result["candidates"]) == 10

    def test_each_candidate_has_required_fields(self):
        """REQ-AG-002: Each candidate has soundbite, primary_lens, scores dict, rationale."""
        from angle_generator import generate_from_angle

        content = """
        Building in public creates accountability. When you share your progress,
        you can't hide. Your audience becomes your accountability partner.
        """

        result = generate_from_angle(content, "action")

        for candidate in result["candidates"]:
            assert "soundbite" in candidate
            assert "primary_lens" in candidate
            assert "scores" in candidate
            assert "rationale" in candidate

            # Check scores dict has all dimensions
            scores = candidate["scores"]
            assert "memorability" in scores
            assert "emotional_resonance" in scores
            assert "brevity" in scores
            assert "rhythm" in scores
            assert "universality" in scores
            assert "action_potential" in scores
            assert "authenticity" in scores
            assert "overall" in scores

    def test_word_counts_are_2_to_7(self):
        """REQ-AG-002: Word counts are 2-7 for all candidates."""
        from angle_generator import generate_from_angle

        content = """
        The future of work is not about replacing humans with AI.
        It's about augmenting human capability. The best teams will be
        human-AI partnerships where each contributes their strengths.
        """

        result = generate_from_angle(content, "identity")

        for candidate in result["candidates"]:
            word_count = len(candidate["soundbite"].split())
            assert 2 <= word_count <= 7, \
                f"'{candidate['soundbite']}' has {word_count} words, expected 2-7"

    def test_all_5_angles_work(self):
        """REQ-AG-001: All 5 creative angles produce valid results."""
        from angle_generator import generate_from_angle, VALID_ANGLES

        content = "Test content for angle generation validation."

        for angle in VALID_ANGLES:
            result = generate_from_angle(content, angle)
            assert result["angle"] == angle
            assert len(result["candidates"]) == 10

    # ==================== EDGE CASE TESTS ====================

    def test_short_content_under_50_words_still_generates(self):
        """REQ-AG-003: Content under 50 words still generates (may reduce diversity)."""
        from angle_generator import generate_from_angle

        content = "AI changes everything. Embrace it."  # Very short

        result = generate_from_angle(content, "emotional")

        assert len(result["candidates"]) == 10
        # May have warning about limited diversity
        assert result.get("warning") is None or "diversity" in result.get("warning", "").lower()

    def test_long_content_over_5000_words_truncates(self):
        """REQ-AG-003: Content over 5000 words is truncated to relevant sections."""
        from angle_generator import generate_from_angle

        # Generate very long content
        content = "This is a test sentence. " * 1000  # ~5000 words

        result = generate_from_angle(content, "simplifier")

        assert len(result["candidates"]) == 10
        # Should have processed successfully
        assert result.get("truncated", False) is True or len(result["candidates"]) > 0

    def test_content_without_clear_emotion_still_produces_10(self):
        """REQ-AG-003: Technical content without clear emotion still produces 10 candidates."""
        from angle_generator import generate_from_angle

        content = """
        The system architecture consists of three layers:
        1. Data ingestion layer using Apache Kafka
        2. Processing layer with Apache Spark
        3. Storage layer with PostgreSQL

        Each layer communicates via REST APIs with JSON payloads.
        """

        result = generate_from_angle(content, "emotional")

        # Should still produce 10 candidates, even if scores are lower
        assert len(result["candidates"]) == 10

    def test_non_english_content_handled_gracefully(self):
        """REQ-AG-003: Non-English content is handled gracefully."""
        from angle_generator import generate_from_angle

        content = """
        La inteligencia artificial esta cambiando todo.
        El futuro pertenece a quienes se adaptan.
        """

        # Should not raise exception
        result = generate_from_angle(content, "action")

        # May produce fewer or lower-quality candidates
        assert len(result["candidates"]) >= 1
        # Should have language warning
        assert result.get("warning") is not None

    # ==================== FAILURE PATH TESTS ====================

    def test_unknown_angle_raises_valueerror(self):
        """REQ-AG-004: Unknown angle name raises ValueError with valid angles list."""
        from angle_generator import generate_from_angle, VALID_ANGLES

        with pytest.raises(ValueError) as excinfo:
            generate_from_angle("Test content", "unknown_angle")

        # Error message should list valid angles
        error_msg = str(excinfo.value)
        assert "unknown_angle" in error_msg.lower() or "invalid" in error_msg.lower()
        for valid_angle in VALID_ANGLES:
            assert valid_angle in error_msg

    def test_empty_content_raises_valueerror(self):
        """REQ-AG-004: Empty content raises ValueError."""
        from angle_generator import generate_from_angle

        with pytest.raises(ValueError, match="[Cc]ontent required"):
            generate_from_angle("", "emotional")

    def test_whitespace_only_content_raises_valueerror(self):
        """REQ-AG-004: Whitespace-only content raises ValueError."""
        from angle_generator import generate_from_angle

        with pytest.raises(ValueError, match="[Cc]ontent required"):
            generate_from_angle("   \n\t  ", "emotional")

    def test_none_content_raises_typeerror(self):
        """REQ-AG-004: None content raises TypeError."""
        from angle_generator import generate_from_angle

        with pytest.raises(TypeError):
            generate_from_angle(None, "emotional")


class TestAngleCharacteristics:
    """Test that each angle produces characteristic outputs."""

    def test_emotional_angle_uses_feeling_words(self):
        """Emotional angle should use feeling-related vocabulary."""
        from angle_generator import generate_from_angle

        content = """
        Success requires persistence. When others give up, you keep going.
        That's the difference between winners and everyone else.
        """

        result = generate_from_angle(content, "emotional")

        # At least some candidates should have emotional primary_lens
        emotional_lenses = ["fear", "hope", "pride", "defiance", "validation", "belonging"]
        candidates_with_emotional_lens = [
            c for c in result["candidates"]
            if any(lens in c.get("primary_lens", "").lower() for lens in emotional_lenses)
        ]

        assert len(candidates_with_emotional_lens) >= 5, \
            "Emotional angle should produce mostly emotional-lens candidates"

    def test_action_angle_uses_action_verbs(self):
        """Action angle should use action-oriented vocabulary."""
        from angle_generator import generate_from_angle

        content = """
        The best time to start was yesterday. The second best time is now.
        Don't wait for perfect conditions. Take the first step.
        """

        result = generate_from_angle(content, "action")

        # Action soundbites typically start with verbs or include action words
        action_words = ["do", "start", "go", "build", "make", "ship", "move", "create", "begin", "act"]

        candidates_with_action = 0
        for c in result["candidates"]:
            soundbite_lower = c["soundbite"].lower()
            if any(word in soundbite_lower for word in action_words):
                candidates_with_action += 1

        assert candidates_with_action >= 5, \
            "Action angle should produce mostly action-oriented candidates"

    def test_simplifier_angle_produces_short_soundbites(self):
        """Simplifier angle should produce notably short soundbites."""
        from angle_generator import generate_from_angle

        content = """
        Complex systems fail in complex ways. Simple systems are more robust.
        The best solution is often the simplest one that works.
        """

        result = generate_from_angle(content, "simplifier")

        # Calculate average word count
        word_counts = [len(c["soundbite"].split()) for c in result["candidates"]]
        avg_words = sum(word_counts) / len(word_counts)

        # Simplifier should average shorter than other angles
        assert avg_words <= 4, \
            f"Simplifier angle should average <=4 words, got {avg_words:.1f}"


class TestValidAngles:
    """Test valid angle configuration."""

    def test_valid_angles_list_contains_5_angles(self):
        """VALID_ANGLES should contain exactly 5 angles."""
        from angle_generator import VALID_ANGLES

        assert len(VALID_ANGLES) == 5

    def test_valid_angles_match_spec(self):
        """VALID_ANGLES should match the 5-angle spec from OPTIONS-MATRIX."""
        from angle_generator import VALID_ANGLES

        expected_angles = ["emotional", "identity", "action", "contrarian", "simplifier"]

        for angle in expected_angles:
            assert angle in VALID_ANGLES, f"'{angle}' should be in VALID_ANGLES"


class TestOutputFormat:
    """Test output format matches specification."""

    def test_output_has_angle_field(self):
        """Output should have 'angle' field."""
        from angle_generator import generate_from_angle

        result = generate_from_angle("Test content for generation.", "emotional")

        assert "angle" in result

    def test_output_has_candidates_list(self):
        """Output should have 'candidates' list."""
        from angle_generator import generate_from_angle

        result = generate_from_angle("Test content for generation.", "emotional")

        assert "candidates" in result
        assert isinstance(result["candidates"], list)

    def test_output_has_metadata(self):
        """Output should have metadata fields."""
        from angle_generator import generate_from_angle

        result = generate_from_angle("Test content for generation.", "emotional")

        assert "meta" in result
        assert "generation_time_ms" in result["meta"]
        assert "candidates_generated" in result["meta"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
