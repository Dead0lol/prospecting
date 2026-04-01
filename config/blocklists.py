from __future__ import annotations

from urllib.parse import urlparse


GENERAL_DOMAIN_BLOCKLIST = {
    "reddit.com",
    "quora.com",
    "zhihu.com",
    "wikipedia.org",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "linkedin.com",
    "medium.com",
    "substack.com",
    "amazon.com",
    "ebay.com",
    "etsy.com",
    "yelp.com",
    "bbb.org",
    "glassdoor.com",
    "nytimes.com",
    "forbes.com",
    "businessinsider.com",
    "huffpost.com",
    "healthline.com",
    "webmd.com",
    "mayoclinic.org",
    "indeed.com",
    "ziprecruiter.com",
    "blogili.com",
    "wikihow.com",
    "allrecipes.com",
    "buzzfeed.com",
    "buzzfeednews.com",
    "goodreads.com",
    "imdb.com",
    "tripadvisor.com",
    "boredpanda.com",
    "garagegymreviews.com",
    "menshealth.com",
    "womenshealthmag.com",
    "self.com",
    "shape.com",
    "bodybuilding.com",
    "muscleandstrength.com",
    "t-nation.com",
    "nasm.org",
    "acefitness.org",
    "precisionnutrition.com",
    "cash.app",
    "venmo.com",
    "paypal.com",
    "paypal.me",
    "gofundme.com",
    "ko-fi.com",
    "buymeacoffee.com",
    "everydev.ai",
    "envato.com",
    "elements.envato.com",
    "themeforest.net",
    "uk.coach.com",
    "coach.com",
    "easycoachkenya.com",
    "fiverr.com",
    "upwork.com",
    "imginn.com",
    "picuki.com",
    "instanavigation.com",
    "storiesig.net",
    "inflact.com",
    "gramhir.com",
    "dumpor.com",
    "pixwox.com",
    "yoloco.io",
    "hypeauditor.com",
    "socialblade.com",
    "ninjalitics.com",
    "biographytribune.com",
    "pouipouilabs.net",
    "coyotestudentnews.com",
    "jessmcdougallcreative.com",
    "fitnesstrainer.nyc",
}

CHAIN_GYM_DOMAINS = {
    "anytimefitness.com",
    "snapfitness.com",
    "planetfitness.com",
    "orangetheory.com",
    "24hourfitness.com",
    "equinox.com",
    "goldsgym.com",
    "lafitness.com",
    "crunchfitness.com",
}

COACH_PLATFORM_DOMAINS = {
    "kajabi.com",
    "gumroad.com",
    "thinkific.com",
    "teachable.com",
    "trainerize.com",
    "everfit.io",
    "caliber.com",
}

LINK_HUB_DOMAINS = {
    "linktr.ee",
    "beacons.ai",
    "stan.store",
    "linkpop.com",
    "koji.io",
}

COACH_DIRECTORY_DOMAINS = {
    "getmisfit.com",
    "coachcaller.com",
    "yogaia.com",
    "fitnessnetwork.com",
}

AGGREGATOR_DOMAINS = {
    "playbookapp.io",
    "my.playbookapp.io",
    "trainiac.com",
    "future.co",
    "thumbtack.com",
    "bark.com",
    "optimocoach.com",
    "find-a-trainer.com",
    "personaltrainerdirectory.com",
    "wellnessliving.com",
    "mindbodyonline.com",
    "influencer-hero.com",
    "msha.ke",
    "myfit.app",
    "coachhub.io",
    "pixnoy.com",
    "newie.app",
    "share.newie.app",
    "storeplum.com",
    "aguea.net",
}

DOMAIN_BLOCKLIST = GENERAL_DOMAIN_BLOCKLIST | CHAIN_GYM_DOMAINS | AGGREGATOR_DOMAINS
JUNK_DOMAINS = {
    "blogili.com",
    "wikihow.com",
    "allrecipes.com",
    "buzzfeed.com",
    "goodreads.com",
    "imdb.com",
    "tripadvisor.com",
}
ACCEPTED_SOURCE_DOMAINS = (
    LINK_HUB_DOMAINS | COACH_PLATFORM_DOMAINS | COACH_DIRECTORY_DOMAINS
)


def canonical_domain(url: str) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower().lstrip("www.")


def domain_matches(domain: str, domains: set[str]) -> bool:
    if not domain:
        return False
    return any(domain == item or domain.endswith(f".{item}") for item in domains)


def is_blocked_domain(domain: str) -> bool:
    return domain_matches(domain, DOMAIN_BLOCKLIST)


def is_link_hub_domain(domain: str) -> bool:
    return domain_matches(domain, LINK_HUB_DOMAINS)


def is_accepted_source_domain(domain: str) -> bool:
    return domain_matches(domain, ACCEPTED_SOURCE_DOMAINS)


def is_non_primary_website_domain(domain: str) -> bool:
    return is_blocked_domain(domain) or domain_matches(domain, CHAIN_GYM_DOMAINS)
