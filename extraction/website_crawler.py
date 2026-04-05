from __future__ import annotations

import re
import time
from typing import Dict, List
from urllib.parse import urljoin, urlparse

from scrapling.fetchers import Fetcher

from config.settings import settings
from extraction.email_extractor import extract_emails


PATH_HINTS = ["", "/about", "/contact", "/services", "/coaching", "/work-with-me"]
SOCIAL_PATTERNS = {
    "linkedin.com": "linkedin_url",
    "youtube.com": "youtube_url",
    "youtu.be": "youtube_url",
    "tiktok.com": "tiktok_url",
    "instagram.com": "instagram_url",
}
BOOKING_HINTS = ["calendly.com", "acuityscheduling.com", "tidycal.com"]
LEAD_MAGNET_HINTS = [
    "free guide",
    "freebie",
    "ebook",
    "download",
    "challenge",
    "lead magnet",
]
SERVICE_HINTS = [
    "1:1 coaching",
    "online coaching",
    "nutrition coaching",
    "fat loss",
    "strength training",
    "macro coaching",
]

# Generic words that are NOT part of a person's name
_NAME_NOISE = {
    "fitness",
    "coach",
    "coaching",
    "trainer",
    "personal",
    "online",
    "training",
    "nutrition",
    "wellness",
    "health",
    "home",
    "about",
    "contact",
    "services",
    "blog",
    "official",
    "site",
    "website",
    "welcome",
    "the",
    "and",
    "of",
    "for",
    "my",
    "your",
    "our",
    "get",
    "certified",
    "nasm",
    "issa",
    "ace",
    "train",
    "performance",
    "strength",
    "studio",
    "gym",
    "body",
    "macro",
    "macros",
    "transform",
    "transformation",
    "liberty",
    "phoenix",
    "rose",
    "iron",
    "elite",
    "premier",
    "prime",
    "peak",
    "summit",
    "apex",
    "core",
    "pro",
    # Common CTA / UI words that get extracted from page text
    "here",
    "click",
    "start",
    "stop",
    "now",
    "join",
    "sign",
    "up",
    "free",
    "mobile",
    "menu",
    "close",
    "open",
    "read",
    "more",
    "view",
    "skip",
    "next",
    "back",
    "send",
    "submit",
    "download",
    "learn",
    "book",
    "call",
    "apply",
    "schedule",
    "reserve",
    "buy",
    "shop",
    # Business suffixes
    "llc",
    "inc",
    "ltd",
    "corp",
    "co",
    # US city names (common false positives)
    "new",
    "york",
    "los",
    "angeles",
    "chicago",
    "houston",
    "phoenix",
    "philadelphia",
    "san",
    "antonio",
    "diego",
    "dallas",
    "austin",
    "jacksonville",
    "columbus",
    "charlotte",
    "denver",
    "seattle",
    "boston",
    "nashville",
    "atlanta",
    "miami",
    "portland",
    "las",
    "vegas",
    "ny",
    "nyc",
    "la",
}

_COMMON_FIRST_NAMES = {
    "alex",
    "alexis",
    "amanda",
    "amy",
    "andrew",
    "anna",
    "anthony",
    "ashley",
    "ben",
    "brandon",
    "brian",
    "brittany",
    "cameron",
    "carlos",
    "chris",
    "christina",
    "courtney",
    "dan",
    "daniel",
    "david",
    "devin",
    "dylan",
    "elizabeth",
    "emily",
    "emma",
    "eric",
    "ethan",
    "hannah",
    "heather",
    "jacob",
    "jake",
    "james",
    "jason",
    "jennifer",
    "jessica",
    "joe",
    "john",
    "jon",
    "jordan",
    "josh",
    "julia",
    "kaitlyn",
    "karen",
    "kate",
    "katie",
    "kayla",
    "kevin",
    "kim",
    "kristen",
    "kyle",
    "lauren",
    "lisa",
    "luke",
    "maria",
    "mark",
    "matt",
    "matthew",
    "megan",
    "melissa",
    "michael",
    "mike",
    "molly",
    "natalie",
    "nick",
    "nicole",
    "olivia",
    "patrick",
    "paul",
    "rachel",
    "rebecca",
    "ryan",
    "sam",
    "samantha",
    "sarah",
    "scott",
    "shannon",
    "steph",
    "stephanie",
    "steven",
    "taylor",
    "thomas",
    "tiffany",
    "tyler",
    "victoria",
    "zach",
}


def _fetch(url: str):
    response = Fetcher.get(
        url,
        headers={"User-Agent": settings.user_agent},
        timeout=settings.request_timeout_seconds,
    )
    if response.status >= 400:
        reason = getattr(response, "reason", "")
        if reason:
            raise RuntimeError(f"HTTP {response.status} {reason} for {url}")
        raise RuntimeError(f"HTTP {response.status} for {url}")
    time.sleep(settings.website_delay_seconds)
    return response


def _response_html(response) -> str:
    body = response.body
    if isinstance(body, bytes):
        return body.decode(response.encoding, errors="replace")
    return body


def crawl_website(base_url: str) -> Dict[str, object]:
    """Fetch likely contact pages and extract lead signals from the site."""
    parsed = urlparse(base_url)
    if not parsed.scheme:
        base_url = f"https://{base_url}"
    crawl_base_url = base_url

    pages: Dict[str, str] = {}
    emails: List[str] = []
    socials: Dict[str, str] = {}
    booking_link = ""
    pricing_page = ""
    text_chunks: List[str] = []
    services: List[str] = []
    platform = "unknown"
    title = ""
    description = ""
    has_lead_magnet = False
    has_testimonials = False
    phone = ""

    for path in PATH_HINTS[: settings.max_pages_per_site]:
        page_url = urljoin(crawl_base_url, path)
        try:
            response = _fetch(page_url)
        except Exception:
            continue

        final_page_url = str(getattr(response, "url", "") or page_url)
        if not path:
            crawl_base_url = final_page_url

        html = _response_html(response)
        pages[final_page_url] = html
        text = str(response.get_all_text(separator=" ", strip=True))
        text_chunks.append(text)
        emails.extend(extract_emails(text))

        if not title:
            title = (response.css("title::text").get() or "").strip()
        if not description:
            description = (
                response.css('meta[name="description"]::attr(content)').get() or ""
            ).strip()

        lower_html = html.lower()
        lower_text = text.lower()

        if "wp-content" in lower_html:
            platform = "wordpress"
        elif "squarespace" in lower_html:
            platform = "squarespace"
        elif "wix" in lower_html:
            platform = "wix"
        elif "kajabi" in lower_html:
            platform = "kajabi"
        elif "showit" in lower_html:
            platform = "showit"

        if any(hint in lower_text for hint in LEAD_MAGNET_HINTS):
            has_lead_magnet = True
        if "testimonial" in lower_text or "client results" in lower_text:
            has_testimonials = True
        if ("pricing" in lower_text or "investment" in lower_text) and not pricing_page:
            pricing_page = final_page_url

        for service_hint in SERVICE_HINTS:
            if service_hint in lower_text and service_hint not in services:
                services.append(service_hint)

        for anchor in response.css("a[href]"):
            href = anchor.attrib.get("href", "").strip()
            if not href:
                continue
            full_url = urljoin(response.url, href)
            href_lower = full_url.lower()

            if href_lower.startswith("mailto:"):
                emails.extend(extract_emails(href_lower))

            for pattern, field_name in SOCIAL_PATTERNS.items():
                if pattern in href_lower and not socials.get(field_name):
                    socials[field_name] = full_url

            if any(hint in href_lower for hint in BOOKING_HINTS) and not booking_link:
                booking_link = full_url

            if any(key in href_lower for key in ["pricing", "investment", "plans"]) and (
                not pricing_page or pricing_page == final_page_url
            ):
                pricing_page = full_url

        if not phone:
            phone = _extract_phone(text)

        if emails and services and (booking_link or pricing_page):
            break

    unique_emails = sorted(set(emails))
    full_text = "\n".join(text_chunks)
    _online_hints = [
        "online coaching",
        "virtual coaching",
        "remote coaching",
        "online personal training",
        "virtual personal training",
        "remote personal training",
        "1:1 online",
        "1-on-1 online",
        "online 1:1",
        "online 1-on-1",
        "train from anywhere",
        "coach you online",
        "coaching online",
        "train online",
        "virtual training",
        "remote training",
    ]
    lower_full = full_text.lower()
    offers_online_coaching = (
        "yes" if any(h in lower_full for h in _online_hints) else "unknown"
    )

    # Try to extract a person's name from the site title or meta description
    contact_name = _extract_contact_name(title, description)

    return {
        "website": crawl_base_url,
        "website_title": title,
        "website_description": description,
        "contact_name": contact_name,
        "pages": list(pages.keys()),
        "page_text": full_text,
        "emails": unique_emails,
        "phone": phone,
        "booking_link": booking_link,
        "pricing_page": pricing_page,
        "has_pricing_page": bool(pricing_page),
        "has_lead_magnet": has_lead_magnet,
        "has_testimonials": has_testimonials,
        "services_found": services,
        "socials": socials,
        "platform": platform,
        "offers_online_coaching": offers_online_coaching,
    }


def _extract_contact_name(title: str, description: str) -> str:
    """Try to extract a person's name from the site title or meta description.

    Common patterns:
      "Samantha Jones Fitness" -> "Samantha Jones"
      "Train with Sarah | Online Coach" -> "Sarah"
      "Coach Mike's Fitness Studio" -> "Mike"
    """
    for text in [title, description]:
        if not text:
            continue
        # Split on common separators
        for sep in ["|", " - ", "•", "·", "–", "—"]:
            if sep in text:
                parts = [p.strip() for p in text.split(sep)]
                for part in parts:
                    name = _clean_name_candidate(part)
                    if name:
                        return name
                break
        else:
            # No separator — try the whole text
            name = _clean_name_candidate(text)
            if name:
                return name
    return ""


def _clean_name_candidate(text: str) -> str:
    """Check if text contains a likely person's name and extract it."""
    # Remove common prefixes
    for prefix in [
        "coach ",
        "train with ",
        "meet ",
        "about ",
        "hi i'm ",
        "i'm ",
        "hey i'm ",
    ]:
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]

    # Remove possessives
    text = re.sub(r"'s\b", "", text)

    text = re.sub(r"[^A-Za-z'\-\s]", " ", text)
    words = text.split()
    name_words = []
    for w in words:
        clean = w.strip(",.!?()[]{}\"'")
        if not clean:
            continue
        if clean.lower() in _NAME_NOISE:
            continue
        # A name word should start with uppercase and be mostly alpha
        if clean[0].isupper() and clean.replace("'", "").replace("-", "").isalpha():
            name_words.append(clean)
        else:
            # Stop at first non-name word.
            break

    if not name_words or len(name_words) > 3:
        return ""

    first = name_words[0].lower()
    if first not in _COMMON_FIRST_NAMES:
        return ""

    if len(name_words) == 1 and len(name_words[0]) < 4:
        return ""

    return " ".join(name_words)


def _extract_phone(text: str) -> str:
    match = re.search(r"(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}", text)
    return match.group(0) if match else ""
