"""Generate personalized icebreakers for outreach using OpenRouter AI."""

from __future__ import annotations

import json
import time
from typing import Any, Dict
from urllib import request

from config.settings import settings
from logging_utils import get_logger
from models.lead import Lead


logger = get_logger("icebreaker_generator")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_icebreaker(lead: Lead) -> str:
    """Generate a personalized icebreaker/compliment for a lead.

    Args:
        lead: The lead to generate an icebreaker for

    Returns:
        A personalized icebreaker string, or empty string if generation fails
    """
    # Skip if OpenRouter is not configured
    if not settings.openrouter_api_key:
        logger.debug(
            "OpenRouter API key not configured, skipping icebreaker generation"
        )
        return ""

    # Skip if we don't have enough content
    website_text = lead.raw_payload.get("page_text", "") if lead.raw_payload else ""
    if not website_text or len(website_text.strip()) < 100:
        logger.debug(
            f"Not enough website content for {lead.website}, skipping icebreaker"
        )
        return ""

    try:
        icebreaker = _call_openrouter(lead, website_text)
        logger.info(f"Generated icebreaker for {lead.website}: {icebreaker[:50]}...")
        return icebreaker
    except Exception as e:
        logger.warning(f"Failed to generate icebreaker for {lead.website}: {e}")
        return ""


def _call_openrouter(lead: Lead, website_text: str) -> str:
    """Call OpenRouter API to generate icebreaker."""

    logger.info(f"Calling OpenRouter API for {lead.website}...")

    # Build the system prompt
    system_prompt = f"""You are an expert at writing personalized, authentic compliments for cold outreach emails.

Your task: Write a {settings.icebreaker_length}-sentence icebreaker that is {settings.icebreaker_tone}.

Rules:
- Be SPECIFIC to their actual website content (mention something you noticed)
- Be AUTHENTIC (no generic "nice website" or "great content")
- Be BRIEF ({settings.icebreaker_length} sentences max)
- NO sales pitch, NO questions, just a genuine observation or compliment
- Focus on their unique approach, content, or value proposition
- Write in a {settings.icebreaker_tone} tone

Return ONLY the icebreaker text, nothing else.""".strip()

    # Build the user prompt with lead context
    user_prompt = f"""Business: {lead.business_name or "Unknown"}
Website: {lead.website}
Specialty: {lead.specialty or "fitness"}
Instagram Bio: {lead.bio_text or "N/A"}

Website Content (first 3000 chars):
{website_text[:3000]}

Write a {settings.icebreaker_length}-sentence icebreaker for this business.""".strip()

    body = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,  # Slightly creative but not too random
        "max_tokens": 150,  # Enough for 2-3 sentences
    }

    req = request.Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Dead0lol/prospecting",
            "X-Title": "Fitness Coach Prospecting Pipeline - Icebreaker Generator",
        },
        method="POST",
    )

    logger.debug(
        f"Making request to OpenRouter (model: {settings.openrouter_model})..."
    )

    try:
        with request.urlopen(req, timeout=settings.request_timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
        logger.debug("OpenRouter request successful")
    except Exception as e:
        logger.error(f"OpenRouter request failed: {e}")
        raise

    # Respect rate limiting
    time.sleep(settings.openrouter_delay_seconds)

    choices = raw.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter returned no choices")

    message = choices[0].get("message", {})
    content = message.get("content", "")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter returned empty content")

    # Clean up the icebreaker
    icebreaker = content.strip()

    # Remove quotes if the AI wrapped it
    if icebreaker.startswith('"') and icebreaker.endswith('"'):
        icebreaker = icebreaker[1:-1].strip()
    if icebreaker.startswith("'") and icebreaker.endswith("'"):
        icebreaker = icebreaker[1:-1].strip()

    return icebreaker
