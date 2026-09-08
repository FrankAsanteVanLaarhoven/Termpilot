"""Student identity helpers. No institutional SSO in this deployment."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import SourceConnection
from app.settings import get_settings

DEMO_EMAIL = "demo@termpilot.org"
DEMO_EMAILS = {DEMO_EMAIL}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ACADEMIC_SLDS = frozenset({"edu", "ac"})
CONSUMER_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.uk",
        "yahoo.fr",
        "yahoo.de",
        "yahoo.es",
        "yahoo.it",
        "yahoo.ca",
        "yahoo.com.au",
        "ymail.com",
        "hotmail.com",
        "hotmail.co.uk",
        "hotmail.fr",
        "hotmail.de",
        "hotmail.es",
        "hotmail.it",
        "hotmail.ca",
        "outlook.com",
        "outlook.co.uk",
        "outlook.fr",
        "outlook.de",
        "outlook.es",
        "live.com",
        "live.co.uk",
        "msn.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "pm.me",
        "zoho.com",
        "gmx.com",
        "gmx.de",
        "gmx.net",
        "web.de",
        "mail.com",
        "yandex.com",
        "yandex.ru",
        "qq.com",
        "163.com",
        "126.com",
        "sina.com",
        "naver.com",
        "daum.net",
        "rediffmail.com",
        "fastmail.com",
        "tutanota.com",
        "mailbox.org",
        "hey.com",
        "duck.com",
        "icloud.com.cn",
        "onmicrosoft.com",
        "outlook.office365.com",
    }
)
CAMPUS_NAME_RE = re.compile(
    r"(university|universidad|universidade|universitaet|universitat|"
    r"universita|universite|universiteit|hogeschool|hochschule|"
    r"polytechnique|politecnico|polytechnic)",
    re.IGNORECASE,
)
CAMPUS_PREFIXES = ("uni-", "univ-", "tu-", "fh-", "haw-", "hs-", "rwth-", "th-")
# Campuses whose public mail domain is not .edu / .ac.* / .edu.*.
UNIVERSITY_DOMAINS = frozenset(
    {
        "tum.de",
        "lmu.de",
        "rwth-aachen.de",
        "fau.de",
        "hhu.de",
        "kit.edu",
        "fu-berlin.de",
        "hu-berlin.de",
        "tu-berlin.de",
        "ethz.ch",
        "epfl.ch",
        "uzh.ch",
        "unige.ch",
        "unibas.ch",
        "unibe.ch",
        "unil.ch",
        "unifr.ch",
        "usi.ch",
        "utoronto.ca",
        "ubc.ca",
        "sfu.ca",
        "mcgill.ca",
        "uwaterloo.ca",
        "uottawa.ca",
        "ualberta.ca",
        "ucalgary.ca",
        "umontreal.ca",
        "ulaval.ca",
        "queensu.ca",
        "mcmaster.ca",
        "yorku.ca",
        "concordia.ca",
        "carleton.ca",
        "dal.ca",
        "uvic.ca",
        "umanitoba.ca",
        "usask.ca",
        "uwo.ca",
        "torontomu.ca",
        "ryerson.ca",
        "uoguelph.ca",
        "uwindsor.ca",
        "mun.ca",
        "unb.ca",
        "uva.nl",
        "vu.nl",
        "tudelft.nl",
        "tue.nl",
        "utwente.nl",
        "rug.nl",
        "leidenuniv.nl",
        "eur.nl",
        "ru.nl",
        "uu.nl",
        "maastrichtuniversity.nl",
        "wur.nl",
        "tilburguniversity.edu",
        "tcd.ie",
        "ucd.ie",
        "ucc.ie",
        "dcu.ie",
        "ul.ie",
        "nuigalway.ie",
        "universityofgalway.ie",
        "maynoothuniversity.ie",
        "tudublin.ie",
        "rcsi.ie",
        "sorbonne-universite.fr",
        "psl.eu",
        "sciencespo.fr",
        "polytechnique.edu",
        "centralesupelec.fr",
        "hec.fr",
        "upm.es",
        "ucm.es",
        "uam.es",
        "uv.es",
        "us.es",
        "unizar.es",
        "unav.es",
        "uab.cat",
        "ugr.es",
        "polimi.it",
        "polito.it",
        "unibo.it",
        "uniroma1.it",
        "sapienza.it",
        "unifi.it",
        "unipd.it",
        "unimi.it",
        "unina.it",
        "unitn.it",
        "unipi.it",
        "unito.it",
        "bocconi.it",
        "ulisboa.pt",
        "unl.pt",
        "uc.pt",
        "up.pt",
        "uminho.pt",
        "kth.se",
        "su.se",
        "uu.se",
        "lu.se",
        "chalmers.se",
        "liu.se",
        "ki.se",
        "gu.se",
        "uio.no",
        "ntnu.no",
        "uib.no",
        "ku.dk",
        "aau.dk",
        "au.dk",
        "dtu.dk",
        "sdu.dk",
        "cbs.dk",
        "helsinki.fi",
        "aalto.fi",
        "tuni.fi",
        "utu.fi",
        "jyu.fi",
        "oulu.fi",
        "kuleuven.be",
        "ugent.be",
        "uclouvain.be",
        "ulb.be",
        "vub.be",
        "uantwerpen.be",
        "cuni.cz",
        "cvut.cz",
        "muni.cz",
        "elte.hu",
        "bme.hu",
        "uoa.gr",
        "auth.gr",
        "ntua.gr",
        "unibuc.ro",
        "msu.ru",
        "spbu.ru",
        "hse.ru",
        "itmo.ru",
        "usp.br",
        "unicamp.br",
        "ufrj.br",
        "unesp.br",
        "ufrgs.br",
        "ufmg.br",
        "unb.br",
        "puc-rio.br",
        "unam.mx",
        "itesm.mx",
        "tec.mx",
        "ipn.mx",
        "uam.mx",
        "uba.ar",
        "uchile.cl",
        "puc.cl",
        "uc.cl",
        "hku.hk",
        "ust.hk",
        "cuhk.edu.hk",
        "waseda.jp",
        "keio.jp",
        "um.edu.my",
        "utm.my",
        "ukm.my",
        "usm.my",
        "knu.ua",
        "kpi.ua",
        "hi.is",
    }
)
UNIVERSITY_EMAIL_HINT = (
    "Use a real university email from your campus — .edu, .ac.uk, .edu.au, "
    ".ac.jp, .edu.sg, .edu.cn and other university domains worldwide. "
    "Personal Gmail or Outlook is not accepted."
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(email)))


def is_demo_email(email: str) -> bool:
    return normalize_email(email) in DEMO_EMAILS


def _host_parents(host: str) -> list[str]:
    labels = [part for part in host.split(".") if part]
    return [".".join(labels[index:]) for index in range(len(labels) - 1)]


def _extra_university_domains() -> set[str]:
    raw = get_settings().university_domains_extra
    return {item.strip().lower().lstrip("@") for item in raw.split(",") if item.strip()}


def _is_consumer_host(host: str) -> bool:
    return any(parent in CONSUMER_DOMAINS for parent in _host_parents(host))


def _is_academic_tld(host: str) -> bool:
    labels = [part for part in host.split(".") if part]
    if not labels:
        return False
    if labels[-1] == "edu":
        return True
    return len(labels) >= 3 and labels[-2] in ACADEMIC_SLDS


def _looks_like_campus_name(host: str) -> bool:
    labels = [part for part in host.split(".") if part]
    if len(labels) < 2:
        return False
    sld = labels[-2]
    if labels[-2] in {"co", "com", "org", "net", "gov"} and len(labels) >= 3:
        sld = labels[-3]
    if sld.startswith(CAMPUS_PREFIXES):
        return True
    if sld in {"uni", "univ"}:
        return True
    return bool(CAMPUS_NAME_RE.search(sld))


def is_university_email(email: str) -> bool:
    """Campus inbox from any country, plus the public demo account."""
    if not is_valid_email(email):
        return False
    if is_demo_email(email):
        return True
    host = normalize_email(email).rsplit("@", 1)[-1]
    if _is_consumer_host(host):
        return False
    parents = _host_parents(host)
    allowed = UNIVERSITY_DOMAINS | _extra_university_domains()
    if any(parent in allowed for parent in parents):
        return True
    return _is_academic_tld(host) or _looks_like_campus_name(host)


def university_email_error(email: str) -> str | None:
    if not is_valid_email(email):
        return "Enter a valid student email."
    if is_university_email(email):
        return None
    host = normalize_email(email).rsplit("@", 1)[-1]
    if _is_consumer_host(host):
        return "Use your university email, not a personal Gmail or Outlook address."
    return UNIVERSITY_EMAIL_HINT


def user_id_from_email(email: str) -> str:
    if is_demo_email(email):
        return get_settings().demo_user_id
    digest = hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()[:10]
    return f"stu_{digest}"


def display_name_from_email(email: str) -> str:
    if is_demo_email(email):
        return "Demo student"
    local = normalize_email(email).split("@")[0]
    parts = [part for part in re.split(r"[._+\-]+", local) if part]
    if not parts:
        return "Student"
    return " ".join(part[:1].upper() + part[1:] for part in parts[:3])


def scoped_id(user_id: str, raw_id: str) -> str:
    if user_id == get_settings().demo_user_id:
        return raw_id
    return f"{raw_id}__{user_id}"


def connection_id_for(user_id: str, catalog_id: str) -> str:
    return scoped_id(user_id, catalog_id)


def catalog_id_of(row_id: str, user_id: str) -> str:
    suffix = f"__{user_id}"
    if row_id.endswith(suffix):
        return row_id[: -len(suffix)]
    return row_id


async def get_connection(
    session: AsyncSession, user_id: str, catalog_id: str
) -> SourceConnection | None:
    scoped = connection_id_for(user_id, catalog_id)
    row = await session.get(SourceConnection, scoped)
    if row is not None and row.user_id == user_id:
        return row
    if scoped != catalog_id:
        row = await session.get(SourceConnection, catalog_id)
        if row is not None and row.user_id == user_id:
            return row
    return None
