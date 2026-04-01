"""
Discovery keywords for fitness coach prospecting.

Organized into tiers by ICP priority for a cold email campaign selling a low-ticket
digital product. Geography is NOT used — any English-speaking fitness coach globally is a
potential lead. Keywords that identify coaches already selling digitally are highest priority.
"""

from config.blocklists import COACH_DIRECTORY_DOMAINS, COACH_PLATFORM_DOMAINS

# Tier 1: Coaches already selling digital products (highest conversion intent)
# These coaches understand digital products and low-ticket offers.
DIGITAL_SELLER_KEYWORDS = [
    "fitness ebook author",
    "training guide download",
    "fitness workbook",
    "coaching template",
    "fitness challenge free",
    "nutrition guide download",
    "fitness swipe file",
    "workout program pdf",
    "meal plan template",
    "fitness tracker printable",
    "macro calculator coach",
]

# Tier 2: Coaches who coach online (understands digital delivery)
ONLINE_COACH_KEYWORDS = [
    "online fitness coach",
    "online personal trainer",
    "remote personal trainer",
    "virtual fitness coach",
    "online nutrition coach",
    "1:1 online coaching",
    "online coaching program",
    "remote coaching fitness",
    "virtual personal training",
]

# Tier 3: Transformation and results-based coaches (motivated buyers)
TRANSFORMATION_KEYWORDS = [
    "fat loss coach",
    "body transformation coach",
    "weight loss coach",
    "body recomposition coach",
    "muscle gain coach",
    "strength coach online",
    "body reset coach",
    "fitness transformation coach",
]

# Tier 4: Niche audience coaches (higher ticket, more desperate for content)
NICHE_COACH_KEYWORDS = [
    "macro coach",
    "macro nutrition coach",
    "women's fitness coach",
    "postpartum fitness coach",
    "pcos fitness coach",
    "fitness coach for women over 40",
    "fitness coach for men over 40",
    "busy mom fitness coach",
    "wedding fitness coach",
    "mobility coach",
    "functional fitness coach",
    "running coach online",
    "calisthenics coach",
    "glute coach",
    "sports performance coach",
]

# Tier 5: Business-minded coaches (buyers of business resources)
BUSINESS_COACH_KEYWORDS = [
    "fitness coach business coach",
    "personal trainer marketing",
    "fitness coach mindset",
    "online trainer tools",
    "fitness business coach",
    "trainer growth coach",
]

# Combine all keywords — tier order matters for query rotation
DISCOVERY_KEYWORDS = (
    DIGITAL_SELLER_KEYWORDS
    + ONLINE_COACH_KEYWORDS
    + TRANSFORMATION_KEYWORDS
    + NICHE_COACH_KEYWORDS
    + BUSINESS_COACH_KEYWORDS
)

# Intent modifiers — adds urgency and action signals to base keywords
DISCOVERY_MODIFIERS = [
    "apply now",
    "book a call",
    "work with me",
    "1:1 coaching",
    "online coaching",
    "client results",
    "free consultation",
    "start today",
    "coaching program",
    "join now",
]
