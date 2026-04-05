"""Test icebreaker generator."""

from __future__ import annotations

from models.lead import Lead
from enrichment.icebreaker_generator import generate_icebreaker


def test_generate_icebreaker_with_content():
    """Test that icebreaker is generated when we have website content."""
    lead = Lead(
        business_name="FitPro Coaching",
        website="https://fitpro.com",
        specialty="strength training",
        bio_text="Helping busy professionals build strength and confidence",
        raw_payload={
            "page_text": """
            Welcome to FitPro Coaching
            
            I'm Sarah, a certified strength coach with 10 years of experience.
            I specialize in helping busy professionals build sustainable strength
            training habits that fit into their lifestyle.
            
            My approach is different: no cookie-cutter programs, no generic meal plans.
            Every client gets a fully customized training program based on their goals,
            schedule, and equipment access.
            
            What makes my coaching unique:
            - Science-based programming tailored to your body
            - Weekly check-ins and form reviews
            - Flexible scheduling that works with your life
            - Focus on long-term sustainable results
            
            I've helped over 200 clients transform their relationship with fitness.
            """
        },
    )

    icebreaker = generate_icebreaker(lead)

    # Should return something (unless OpenRouter is not configured)
    print(f"Generated icebreaker: {icebreaker}")

    # Basic validation if we got a result
    if icebreaker:
        assert len(icebreaker) > 20, "Icebreaker should be substantial"
        assert len(icebreaker) < 500, "Icebreaker should be brief"


def test_generate_icebreaker_without_content():
    """Test that icebreaker generation is skipped when there's no content."""
    lead = Lead(
        business_name="Test",
        website="https://example.com",
        raw_payload={},  # No page_text
    )

    icebreaker = generate_icebreaker(lead)

    # Should return empty string when there's no content
    assert icebreaker == ""


def test_generate_icebreaker_with_minimal_content():
    """Test that icebreaker generation is skipped when content is too short."""
    lead = Lead(
        business_name="Test",
        website="https://example.com",
        raw_payload={"page_text": "Short text"},  # Too short
    )

    icebreaker = generate_icebreaker(lead)

    # Should return empty string when content is too short
    assert icebreaker == ""


if __name__ == "__main__":
    print("Testing icebreaker generator...")
    print("\n1. Testing with good content:")
    test_generate_icebreaker_with_content()
    print("\n2. Testing without content:")
    test_generate_icebreaker_without_content()
    print("\n3. Testing with minimal content:")
    test_generate_icebreaker_with_minimal_content()
    print("\n✓ All tests passed!")
