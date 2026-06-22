import copy
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

try:
    from agents import function_tool
except Exception:
    # Allows the Streamlit UI to run even if openai-agents is not installed yet.
    def function_tool(func=None, **kwargs):
        def decorator(f):
            return f
        return decorator(func) if func else decorator


# -----------------------------
# Text helpers
# -----------------------------

def _normalise(text: str) -> str:
    text = text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    return text


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip(" .,:;-\n\t")
    return value or None


def _sentences(text: str) -> List[str]:
    text = _normalise(text)
    parts: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip(" -•\t")
        if not line:
            continue
        # Keep labelled/bullet lines as independent facts.
        if ":" in line or len(line) < 160:
            parts.append(line)
            continue
        parts.extend([s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()])
    return parts


def _line_value(text: str, label: str) -> Optional[str]:
    """Extract a value from a labelled line like 'Client name: Priya Kapoor'."""
    pattern = rf"(?im)^\s*{re.escape(label)}\s*[:\-]\s*(.+?)\s*$"
    match = re.search(pattern, _normalise(text))
    return _clean(match.group(1)) if match else None


def _first_match(text: str, patterns: List[str], flags: int = re.I) -> Optional[str]:
    text = _normalise(text)
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return _clean(match.group(1))
    return None


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        cleaned = _clean(str(item))
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _split_list(value: str) -> List[str]:
    value = _normalise(value)
    value = re.sub(r"\band\b", ",", value, flags=re.I)
    parts = [p.strip(" .,-•\t") for p in value.split(",")]
    return _dedupe([p for p in parts if p])


# -----------------------------
# Field extractors
# -----------------------------

def _extract_name(text: str) -> Optional[str]:
    transcript_name = _first_match(
        text,
        [
            r"^\s*Call Transcript(?:\s+\d+)?\s*[-:]\s*"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}?)\s+"
            r"(?:Initial|Follow-up|Follow up|Discovery|Clarification)\b",
            r"\b(?:my\s+)?full name is\s+"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*(?:[,.]|$)",
        ],
        flags=re.I | re.M,
    )
    if transcript_name:
        return transcript_name

    # Paragraph-style notes: "Client: Anika Sharma, age 42. Works as..."
    inline = _first_match(
        text,
        [
            r"\bClient\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*(?:,|\.)",
            r"\bClient name\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*(?:,|\.)",
            r"\bName\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*(?:,|\.)",
        ],
        flags=re.I,
    )
    if inline:
        return inline

    value = _line_value(text, "Client name") or _line_value(text, "Client") or _line_value(text, "Name")
    if value:
        # Stop at inline field markers, not just "Age:" labels.
        value = re.split(
            r"\s*,\s*age\b|\s*\.\s|\b(?:Age|Occupation|Marital status|Dependents)\b\s*[:\-]",
            value,
            maxsplit=1,
            flags=re.I,
        )[0]
        return _clean(value)

    return _first_match(
        text,
        [
            r"\bclient\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
            r"\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
        ],
        flags=0,
    )


def _extract_gender(text: str) -> Optional[str]:
    value = _line_value(text, "Gender")
    if not value:
        return None

    aliases = {
        "female": "Female",
        "woman": "Female",
        "male": "Male",
        "man": "Male",
        "nonbinary": "Non-binary",
        "non-binary": "Non-binary",
        "prefer not to say": "Prefer not to say",
    }
    normalised = re.sub(r"\s+", " ", value).strip().lower()
    return aliases.get(normalised, value)


def _extract_pronouns(text: str) -> Optional[str]:
    return _line_value(text, "Pronouns") or _first_match(
        text,
        [r"\bpronouns?\s+(?:are|is)\s+([^\n.,;]+(?:/[^\n.,;]+)?)"],
    )


def calculate_age(date_of_birth: str, as_of: Optional[date] = None) -> Optional[int]:
    """Calculate age from an ISO date of birth, accounting for the birthday."""
    try:
        born = date.fromisoformat(date_of_birth)
    except (TypeError, ValueError):
        return None

    today = as_of or date.today()
    if born > today:
        return None

    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


_LATEST_RUN_LIST_FIELDS = {
    "missing_information",
    "contradictions",
    "follow_up_questions",
    "confidence_notes",
}


def _list_item_key(value: Any) -> str:
    """Normalise harmless formatting differences in advisor-facing list items."""
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _list_item_concept(field_name: str, value: Any) -> Optional[str]:
    """Return a narrow semantic key for common duplicate KYC facts."""
    key = _list_item_key(value)

    if field_name == "goals":
        if "retirement" in key:
            return "retirement"
        if re.search(r"\b(?:education|university|college)\b", key):
            if "daughter" in key:
                return "education:daughter"
            if "son" in key:
                return "education:son"
            return "education:general"
        if "home renovation" in key:
            return "home-renovation"

    if field_name == "dependents":
        if re.search(r"\b(?:spouse|wife|husband)\b", key):
            return "partner"
        if "daughter" in key:
            return "daughter"
        if "son" in key:
            return "son"
        if re.search(r"\bparents?\b", key):
            return "parents"

    return None


def merge_list_values(field_name: str, existing: List[Any], incoming: List[Any]) -> List[Any]:
    """Merge list values, keeping the most descriptive semantic duplicate."""
    merged: List[Any] = []
    exact_indexes: Dict[str, int] = {}
    concept_indexes: Dict[str, int] = {}

    for item in list(existing or []) + list(incoming or []):
        exact_key = _list_item_key(item)
        if not exact_key or exact_key in exact_indexes:
            continue

        concept = _list_item_concept(field_name, item)
        if concept is not None and concept in concept_indexes:
            index = concept_indexes[concept]
            current = merged[index]
            current_key = _list_item_key(current)
            if (len(exact_key.split()), len(exact_key)) > (
                len(current_key.split()),
                len(current_key),
            ):
                del exact_indexes[current_key]
                merged[index] = item
                exact_indexes[exact_key] = index
            continue

        index = len(merged)
        merged.append(item)
        exact_indexes[exact_key] = index
        if concept is not None:
            concept_indexes[concept] = index

    return merged


def merge_kyc_profiles(
    existing_profile: Optional[Dict[str, Any]],
    new_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge extracted KYC data without erasing previously reviewed values."""
    merged = copy.deepcopy(existing_profile or {})

    for key, value in new_profile.items():
        if key == "client_id" and merged.get("client_id"):
            continue
        if value in [None, "", [], {}]:
            continue

        if isinstance(value, list):
            if key in _LATEST_RUN_LIST_FIELDS:
                merged[key] = copy.deepcopy(value)
                continue
            current = merged.get(key, [])
            if not isinstance(current, list):
                current = []
            merged[key] = merge_list_values(key, current, value)
            continue

        if isinstance(value, dict):
            current = merged.get(key, {})
            if not isinstance(current, dict):
                current = {}
            merged[key] = {
                **current,
                **{k: v for k, v in value.items() if v not in [None, "", [], {}]},
            }
            continue

        merged[key] = value

    date_of_birth = merged.get("date_of_birth")
    if date_of_birth:
        merged["age"] = calculate_age(date_of_birth)
    return merged


def _extract_date_of_birth(text: str) -> Optional[str]:
    value = (
        _first_match(
            text,
            [
                r"\b(?:date of birth|DOB|born on)\s*[:\-]?\s*([A-Za-z0-9, /\-]+?)(?=\s*(?:\.|\n|$))",
            ],
        )
        or _line_value(text, "Date of birth")
        or _line_value(text, "DOB")
    )
    if not value:
        return None

    cleaned = re.sub(r"\s+", " ", value).strip()
    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    )
    for date_format in formats:
        try:
            parsed = datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
        return parsed.isoformat() if calculate_age(parsed.isoformat()) is not None else None
    return None


def _extract_age(text: str, date_of_birth: Optional[str] = None) -> Optional[int]:
    if date_of_birth:
        return calculate_age(date_of_birth)

    # Retained for compatibility with older notes that contain only an age.
    value = _line_value(text, "Age") or _first_match(
        text,
        [
            r"\bage\s*[:\-]?\s*(\d{1,3})\b",
            r"\b(\d{1,3})\s*years old\b",
            r"\bclient\s+is\s+(\d{1,3})\b",
        ],
    )
    if not value:
        return None
    try:
        age = int(re.search(r"\d{1,3}", value).group(0))  # type: ignore[union-attr]
        return age if 18 <= age <= 100 else None
    except Exception:
        return None


def _extract_occupation(text: str) -> Optional[str]:
    return (
        _line_value(text, "Occupation")
        or _first_match(text, [r"\bworks as\s+(?:a\s+|an\s+)?([^\n.]+)"])
        or _first_match(text, [r"\bis\s+(?:a\s+|an\s+)?(consultant|business owner|lawyer|doctor|engineer|director|manager|teacher|banker)\b"])
    )


def _extract_marital_status(
    text: str,
    dependents: Optional[List[str]] = None,
) -> Optional[str]:
    status_patterns = (
        (
            "Divorced",
            r"\bdivorc(?:e|ed|ee|ing)\b|\bno longer married\b|"
            r"\b(?:ex|former)[ -](?:wife|husband|spouse)\b",
        ),
        (
            "Widowed",
            r"\bwidow(?:ed|er)?\b|\blate (?:wife|husband|spouse)\b|"
            r"\b(?:wife|husband|spouse) (?:is )?(?:deceased|passed away|died)\b",
        ),
        (
            "Separated",
            r"\bseparated\b|\bliving separately\b|"
            r"\bestranged (?:wife|husband|spouse)\b",
        ),
        ("Single", r"\b(?:single|unmarried)\b|\b(?:never|not) married\b"),
        ("Married", r"\bmarried\b"),
    )

    value = _line_value(text, "Marital status")
    if value:
        for status, pattern in status_patterns:
            if re.search(pattern, value, re.I):
                return status
        return value

    for status, pattern in status_patterns:
        if re.search(pattern, text, re.I):
            return status

    if any(
        re.search(r"\b(?:husband|wife|spouse)\b", dependent, re.I)
        for dependent in (dependents or [])
    ):
        return "Married"
    return None


def _extract_income(text: str) -> Optional[str]:
    value = _line_value(text, "Income") or _first_match(
        text,
        [
            r"\bhousehold income\s+is\s+approximately\s+([^\n.]+)",
            r"\bincome\s+is\s+approximately\s+([^\n.]+)",
            r"\bhousehold income\s*[:\-]\s*([^\n.]+)",
            r"\bincome\s*[:\-]\s*([^\n.]+)",
            r"\bsalary\s*[:\-]\s*([^\n.]+)",
        ],
    )
    return value


def _extract_dependents(text: str) -> List[str]:
    value = _line_value(text, "Dependents")
    if value:
        return _split_list(value)

    dependents: List[str] = []
    current_partner_prefix = r"(?<!ex-)(?<!ex )(?<!former )"
    if re.search(current_partner_prefix + r"\bhusband\b", text, re.I):
        dependents.append("Husband")
    if re.search(current_partner_prefix + r"\bwife\b", text, re.I):
        dependents.append("Wife")
    if re.search(current_partner_prefix + r"\bspouse\b", text, re.I):
        dependents.append("Spouse")

    son_match = re.search(r"\b(?:one\s+)?son(?:\s+aged\s+\d{1,2})?\b", text, re.I)
    if son_match:
        dependents.append(son_match.group(0).capitalize())

    daughter_match = re.search(r"\b(?:one\s+)?daughter(?:\s+aged\s+\d{1,2})?\b", text, re.I)
    if daughter_match:
        dependents.append(daughter_match.group(0).capitalize())

    if re.search(r"\bparents?\b", text, re.I):
        dependents.append("Parent(s)")

    return _dedupe(dependents)


def _extract_goals(text: str) -> List[str]:
    lower = text.lower()
    goals: List[str] = []

    if "retirement" in lower:
        goals.append("Retirement planning")
    if any(k in lower for k in ["son's future education", "son’s future education", "education", "university", "college"]):
        if "son" in lower:
            goals.append("Fund son's future education")
        elif "daughter" in lower:
            goals.append("Fund daughter's future education")
        else:
            goals.append("Education funding")
    if "long-term wealth" in lower or "wealth planning" in lower or "wealth creation" in lower:
        goals.append("Long-term wealth planning")
    if re.search(r"\bhome renovation\b", lower):
        goals.append("Maintain liquidity for possible home renovation")
    if "second property" in lower:
        goals.append("Buy a second property")

    return _dedupe(goals)


def _extract_liquidity_needs(text: str) -> List[str]:
    needs: List[str] = []

    if re.search(r"9\s+months?\s+of\s+expenses", text, re.I):
        needs.append("Keep at least 9 months of expenses as emergency savings")
    elif re.search(r"emergency savings|emergency fund", text, re.I):
        needs.append("Maintain emergency savings")

    renovation_amt = re.search(
        r"may\s+need\s+INR\s*([\d]+\s*[–\-]\s*[\d]+L|[\d]+L)[^\n.]*home renovation",
        text,
        re.I,
    )
    if renovation_amt:
        needs.append(f"May need INR {renovation_amt.group(1).replace(' ', '')} for home renovation in the next 12-18 months")
    elif re.search(r"home renovation", text, re.I):
        needs.append("May need liquidity for possible home renovation next year")

    if re.search(r"short-term losses.*?(renovation|emergency)", text, re.I | re.S):
        needs.append("Money needed for renovation or emergency savings should be protected from short-term losses")

    return _dedupe(needs)


def _extract_assets(text: str) -> List[str]:
    match = re.search(r"Existing investments include\s+([^\n.]+)", _normalise(text), re.I)
    if match:
        return _split_list(match.group(1))

    assets: List[str] = []
    asset_terms = [
        "fixed deposits",
        "EPF",
        "equity mutual funds",
        "mutual funds",
        "company stock",
        "portfolio",
        "property",
        "savings",
    ]
    lower = text.lower()
    for term in asset_terms:
        if term.lower() in lower:
            assets.append(term)
    return _dedupe(assets)


def _extract_liabilities(text: str) -> List[str]:
    liabilities: List[str] = []
    if re.search(r"home loan EMI|home loan|mortgage", text, re.I):
        liabilities.append("Home loan EMI")
    if re.search(r"credit card", text, re.I):
        liabilities.append("Credit card debt")
    if re.search(r"business loan", text, re.I):
        liabilities.append("Business loan")
    return _dedupe(liabilities)


def _extract_time_horizon(text: str) -> Dict[str, str]:
    horizons: Dict[str, str] = {}
    lower = text.lower()

    if "retirement" in lower:
        horizons["retirement"] = "Long term - exact retirement date not confirmed"

    if any(k in lower for k in ["education", "university", "college"]):
        if "son" in lower:
            horizons["child_education"] = "Son's future education - exact year not confirmed"
        elif "daughter" in lower:
            horizons["child_education"] = "Daughter's future education - exact year not confirmed"
        else:
            horizons["education"] = "Future education funding - exact year not confirmed"

    if re.search(r"home renovation", text, re.I):
        if re.search(r"12\s*[–\-]\s*18\s+months", text, re.I):
            horizons["home_renovation"] = "12-18 months"
        elif re.search(r"next year", text, re.I):
            horizons["home_renovation"] = "Next year"
        else:
            horizons["home_renovation"] = "Near term - exact date not confirmed"

    growth_match = re.search(r"(?:double|high growth|high returns).*?(\d+\s*[–\-]\s*\d+\s+years?)", text, re.I | re.S)
    if growth_match:
        horizon = re.sub(r"\s*[–-]\s*", "-", growth_match.group(1).strip())
        horizon = re.sub(r"(\d)(years?)", r"\1 \2", horizon, flags=re.I)
        horizons["growth_expectation"] = f"{horizon} - needs advisor clarification"

    if re.search(r"9\s+months?\s+of\s+expenses", text, re.I):
        horizons["emergency_reserve"] = "9 months of expenses to remain liquid"

    return horizons


def _risk_tolerance(text: str) -> Dict[str, Any]:
    lower = text.lower()
    cautious = any(k in lower for k in ["cautious", "does not like taking large risks", "capital protection", "capital preservation", "low risk"])
    moderate = any(k in lower for k in ["moderate risk", "some market volatility"])
    aggressive = any(k in lower for k in ["aggressive", "high growth", "high returns", "double part of her money"])

    evidence_parts = []
    for sentence in _sentences(text):
        s = sentence.lower().strip()
        if s.endswith(":"):
            continue
        if any(k in s for k in ["risk", "cautious", "moderate", "high growth", "double", "loss"]):
            evidence_parts.append(sentence)
    evidence = " | ".join(evidence_parts[:3]) or None

    if aggressive and (cautious or moderate):
        return {
            "value": "Mixed / needs clarification",
            "confidence": "low",
            "evidence": evidence,
        }
    if moderate:
        return {"value": "Moderate", "confidence": "medium", "evidence": evidence}
    if cautious:
        return {"value": "Low / Conservative", "confidence": "medium", "evidence": evidence}
    if aggressive:
        return {"value": "High / Growth-oriented", "confidence": "medium", "evidence": evidence}
    return {"value": None, "confidence": "unknown", "evidence": evidence}


def _extract_declared_missing(text: str) -> List[str]:
    missing: List[str] = []
    mapping = [
        ("investable amount", "Exact investable amount"),
        ("current portfolio value", "Current portfolio value"),
        ("insurance coverage", "Insurance coverage"),
        ("monthly expenses", "Monthly expenses"),
        ("liabilities other than", "Other liabilities beyond home loan"),
        ("exact investment amount", "Exact investment amount"),
        ("income", "Income range"),
    ]
    missing_markers = ["not confirmed", "not shared", "not discussed", "missing", "unclear", "not provided"]

    for sentence in _sentences(text):
        lower_sentence = sentence.lower()
        if not any(marker in lower_sentence for marker in missing_markers):
            continue
        for keyword, label in mapping:
            if keyword in lower_sentence:
                missing.append(label)

    return _dedupe(missing)


_CORE_MISSING_ITEMS = {
    "client full name",
    "date of birth",
    "occupation or employment status",
    "income range",
    "financial goals",
    "risk tolerance",
    "time horizon for each goal",
    "liquidity needs or emergency cash requirement",
    "dependents",
    "existing assets or portfolio",
    "liabilities or debt obligations",
}

_SUPPLEMENTAL_MISSING_PENALTIES = {
    "exact investable amount": 5,
    "exact investment amount": 5,
    "current portfolio value": 5,
    "existing portfolio value": 5,
    "insurance coverage": 3,
    "monthly expenses": 3,
}


def _completion_score(
    profile: Dict[str, Any],
    missing: List[str],
    contradictions: List[str],
) -> int:
    """Score profile coverage by KYC section, then apply review penalties."""
    risk = profile.get("risk_tolerance") or {}
    if not isinstance(risk, dict):
        risk = {}

    section_checks = {
        "personal_details": [
            (5, profile.get("name")),
            (5, profile.get("date_of_birth")),
            (5, profile.get("occupation")),
            (5, profile.get("dependents")),
        ],
        "financial_profile": [
            (10, profile.get("income")),
            (10, profile.get("assets")),
            (5, profile.get("liabilities")),
        ],
        "goals_and_time_horizon": [
            (10, profile.get("goals")),
            (10, profile.get("time_horizon")),
        ],
        "risk_and_liquidity": [
            (10, risk.get("value")),
            (10, profile.get("liquidity_needs")),
        ],
        "review_quality": [
            (5, risk.get("evidence")),
            (5, risk.get("confidence") not in [None, "", "unknown"]),
            (3, isinstance(profile.get("missing_information"), list)),
            (2, isinstance(profile.get("contradictions"), list)),
        ],
    }

    score = sum(
        points
        for checks in section_checks.values()
        for points, is_complete in checks
        if is_complete
    )

    for item in missing:
        normalised_item = str(item).strip().lower()
        # Core gaps have already lost their section points above.
        if normalised_item in _CORE_MISSING_ITEMS:
            continue
        score -= _SUPPLEMENTAL_MISSING_PENALTIES.get(normalised_item, 2)

    score -= len(contradictions) * 8
    return max(0, min(100, score))


# -----------------------------
# Local logic used by tools
# -----------------------------

def local_extract_kyc_profile(raw_text: str, client_id: str = "new_client") -> Dict[str, Any]:
    """Extract a structured KYC profile from raw onboarding text."""
    text = _normalise(raw_text or "")

    date_of_birth = _extract_date_of_birth(text)
    dependents = _extract_dependents(text)
    return {
        "client_id": client_id,
        "name": _extract_name(text),
        "gender": _extract_gender(text),
        "pronouns": _extract_pronouns(text),
        "date_of_birth": date_of_birth,
        "age": _extract_age(text, date_of_birth),
        "occupation": _extract_occupation(text),
        "marital_status": _extract_marital_status(text, dependents),
        "income": _extract_income(text),
        "goals": _extract_goals(text),
        "risk_tolerance": _risk_tolerance(text),
        "time_horizon": _extract_time_horizon(text),
        "liquidity_needs": _extract_liquidity_needs(text),
        "dependents": dependents,
        "assets": _extract_assets(text),
        "liabilities": _extract_liabilities(text),
        "missing_information": _extract_declared_missing(text),
        "contradictions": [],
        "follow_up_questions": [],
        "confidence_notes": [],
        "completion_score": 0,
    }


def local_validate_kyc_completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Check whether the extracted KYC profile is complete enough for advisor review."""
    missing: List[str] = list(profile.get("missing_information") or [])
    contradictions: List[str] = []
    confidence_notes: List[str] = []

    if not profile.get("name"):
        missing.append("Client full name")
    if not profile.get("date_of_birth"):
        missing.append("Date of birth")
    if not profile.get("occupation"):
        missing.append("Occupation or employment status")
    if not profile.get("income"):
        missing.append("Income range")
    if not profile.get("goals"):
        missing.append("Financial goals")
    if not profile.get("risk_tolerance", {}).get("value"):
        missing.append("Risk tolerance")
    if not profile.get("time_horizon"):
        missing.append("Time horizon for each goal")
    if not profile.get("liquidity_needs"):
        missing.append("Liquidity needs or emergency cash requirement")
    if not profile.get("dependents"):
        missing.append("Dependents")
    if not profile.get("assets"):
        missing.append("Existing assets or portfolio")
    if not profile.get("liabilities"):
        missing.append("Liabilities or debt obligations")

    risk = profile.get("risk_tolerance") or {}
    if risk.get("value") == "Mixed / needs clarification":
        contradictions.append(
            "Client describes herself as cautious/moderate risk but also asks for high growth or doubling money in a short period."
        )

    if "home_renovation" in (profile.get("time_horizon") or {}) and "growth_expectation" in (profile.get("time_horizon") or {}):
        confidence_notes.append(
            "Near-term renovation liquidity should be separated from long-term or growth-oriented investment goals."
        )

    if risk.get("confidence") in ["low", "unknown", None]:
        confidence_notes.append("Risk tolerance needs advisor confirmation before downstream planning.")

    missing = _dedupe(missing)
    contradictions = _dedupe(contradictions)
    confidence_notes = _dedupe(confidence_notes)

    return {
        "missing_information": missing,
        "contradictions": contradictions,
        "confidence_notes": confidence_notes,
        "completion_score": _completion_score(profile, missing, contradictions),
    }


def local_generate_follow_up_questions(validation_result: Dict[str, Any]) -> List[str]:
    """Generate targeted questions from missing fields and contradictions."""
    questions: List[str] = []
    missing = validation_result.get("missing_information", [])
    contradictions = validation_result.get("contradictions", [])

    question_map = {
        "Client full name": "Can you confirm the client's full legal name?",
        "Date of birth": "Can you confirm the client's date of birth?",
        "Occupation or employment status": "What is the client's occupation and employment status?",
        "Income range": "What is the client's approximate annual income range?",
        "Financial goals": "What are the client's main financial goals and priorities?",
        "Risk tolerance": "How would the client react to a short-term portfolio fall of 10-15%?",
        "Time horizon for each goal": "What is the expected time horizon for each financial goal?",
        "Liquidity needs or emergency cash requirement": "How much cash does the client need to keep liquid for near-term needs?",
        "Dependents": "Does the client have any financial dependents?",
        "Existing assets or portfolio": "What investments, savings, or assets does the client currently hold?",
        "Liabilities or debt obligations": "Does the client have any loans, mortgages, credit card balances, or other liabilities?",
        "Exact investable amount": "How much capital is available for investment now?",
        "Current portfolio value": "What is the current market value of the existing portfolio?",
        "Insurance coverage": "What life and health insurance coverage does the client currently have?",
        "Monthly expenses": "What are the client's approximate monthly household expenses?",
        "Other liabilities beyond home loan": "Are there any liabilities other than the home loan EMI?",
    }

    for item in missing[:6]:
        questions.append(question_map.get(item, f"Can you clarify this missing item: {item}?"))

    for contradiction in contradictions:
        questions.append(f"Please clarify this potential inconsistency: {contradiction}")

    return _dedupe(questions)[:8]


# -----------------------------
# Agent tools
# -----------------------------

@function_tool
def extract_kyc_profile(raw_text: str, client_id: str = "new_client") -> str:
    """Extract a structured KYC profile from raw client onboarding notes, forms, transcripts, or document text."""
    profile = local_extract_kyc_profile(raw_text=raw_text, client_id=client_id)
    return json.dumps(profile, indent=2)


@function_tool
def validate_kyc_completeness(profile_json: str) -> str:
    """Validate a structured KYC profile and return missing information, contradictions, confidence notes, and completion score."""
    try:
        profile = json.loads(profile_json)
    except Exception:
        profile = {}
    validation = local_validate_kyc_completeness(profile)
    return json.dumps(validation, indent=2)


@function_tool
def generate_follow_up_questions(validation_json: str) -> str:
    """Generate targeted advisor follow-up questions from missing information, contradictions, and low-confidence areas."""
    try:
        validation_result = json.loads(validation_json)
    except Exception:
        validation_result = {
            "missing_information": ["Unable to parse validation result"],
            "contradictions": [],
            "confidence_notes": [],
        }
    questions = local_generate_follow_up_questions(validation_result)
    return json.dumps({"follow_up_questions": questions}, indent=2)
