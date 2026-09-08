from __future__ import annotations

from app.services.identity import is_university_email, university_email_error


def test_worldwide_campus_emails_are_accepted() -> None:
    accepted = [
        "alex.rivera@northbridge.ac.uk",
        "sam.lee@campus.ac.uk",
        "ada@harvard.edu",
        "lin@ox.ac.uk",
        "mei@nus.edu.sg",
        "hiro@u-tokyo.ac.jp",
        "ava@unimelb.edu.au",
        "wei@tsinghua.edu.cn",
        "raj@iitb.ac.in",
        "thabo@uct.ac.za",
        "lena@tum.de",
        "noah@ethz.ch",
        "priya@utoronto.ca",
        "daan@tudelft.nl",
        "ciara@tcd.ie",
        "info@frankvanlaarhoven.co.uk",
        "favl.demo@example.com",
        "student@mail.harvard.edu",
        "name@uni-heidelberg.de",
        "name@maastrichtuniversity.nl",
        "F.Van-Laarhoven2@newcastle.ac.uk",
    ]
    for email in accepted:
        assert is_university_email(email), email
        assert university_email_error(email) is None, email


def test_personal_and_non_campus_emails_are_rejected() -> None:
    rejected = [
        "not-an-email",
        "ada@gmail.com",
        "ada@googlemail.com",
        "ada@outlook.com",
        "ada@outlook.co.uk",
        "ada@hotmail.co.uk",
        "ada@yahoo.com",
        "ada@icloud.com",
        "ada@proton.me",
        "name@company.com",
        "name@frankvanlaarhoven.co.uk",
        "name@something.co.uk",
    ]
    for email in rejected:
        assert not is_university_email(email), email
        assert university_email_error(email)


def test_extra_campus_domains_from_settings(monkeypatch) -> None:
    from app.settings import reset_settings_cache

    monkeypatch.setenv("TERMPILOT_UNIVERSITY_DOMAINS", "special-campus.example, other.edu.local")
    reset_settings_cache()
    try:
        assert is_university_email("jo@special-campus.example")
        assert is_university_email("jo@mail.special-campus.example")
    finally:
        monkeypatch.delenv("TERMPILOT_UNIVERSITY_DOMAINS", raising=False)
        reset_settings_cache()
