from extraction.email_guesser import _extract_real_name, guess_emails


def test_extract_real_name_filters_generic_words() -> None:
    assert _extract_real_name("Coach Alex Nutrition") == ("alex", "")
    assert _extract_real_name("Online Fitness Coach") == ("", "")


def test_guess_emails_returns_top_three_generic_patterns_first() -> None:
    guesses = guess_emails("Alex Carter", "coach.example.com")

    assert guesses == [
        "hello@coach.example.com",
        "info@coach.example.com",
        "contact@coach.example.com",
    ]


def test_guess_emails_requires_domain() -> None:
    assert guess_emails("Alex Carter", "") == []
