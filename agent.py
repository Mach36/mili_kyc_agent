import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from tools import (
    calculate_age,
    extract_kyc_profile,
    validate_kyc_completeness,
    generate_follow_up_questions,
    local_extract_kyc_profile,
    local_validate_kyc_completeness,
    local_generate_follow_up_questions,
)

load_dotenv()


AGENT_INSTRUCTIONS = """
You are a Client Onboarding & KYC assistant for a wealth advisor.

Your job is to help the advisor turn messy onboarding notes, transcripts, forms,
and document text into a structured reviewable client profile.

You must use the available tools in this order:
1. extract_kyc_profile
2. validate_kyc_completeness
3. generate_follow_up_questions

Important boundaries:
- Do not approve or reject KYC.
- Do not make investment recommendations.
- Do not assign a final suitability decision.
- Do not treat inferred information as confirmed.
- Always keep the advisor in the loop.
- Extract date_of_birth as YYYY-MM-DD and always derive age from it. Never infer
  a date of birth from an age.

Final output must be valid JSON only.
Do not wrap the JSON in markdown.
Do not add commentary before or after the JSON.

The final JSON should follow this shape:

{
  "client_id": "...",
  "name": "...",
  "date_of_birth": "YYYY-MM-DD",
  "age": 0,
  "occupation": "...",
  "income": "...",
  "goals": [],
  "risk_tolerance": {
    "value": "...",
    "confidence": "...",
    "evidence": "..."
  },
  "time_horizon": {},
  "liquidity_needs": [],
  "dependents": [],
  "assets": [],
  "liabilities": [],
  "missing_information": [],
  "contradictions": [],
  "follow_up_questions": [],
  "confidence_notes": [],
  "completion_score": 0
}
"""


def _safe_json_loads(value: Any) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON from an agent response.

    The model is instructed to return JSON only, but this helper makes the app
    more robust if the response contains extra text.
    """
    if isinstance(value, dict):
        return value

    if value is None:
        return None

    text = str(value).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # Fallback: try extracting the outer JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None

    return None


def _merge_profile(existing_profile: Optional[Dict[str, Any]], new_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge new extracted KYC data into the existing profile.

    Product rule:
    Removing a document should not automatically delete fields that were already
    filled or reviewed. Therefore, empty values from the new run should not wipe
    existing values.
    """
    if not existing_profile:
        merged = dict(new_profile)
        date_of_birth = merged.get("date_of_birth")
        if date_of_birth:
            merged["age"] = calculate_age(date_of_birth)
        return merged

    merged = dict(existing_profile)

    for key, value in new_profile.items():
        if value in [None, "", [], {}]:
            continue

        # These should always reflect the latest run.
        if key in [
            "missing_information",
            "contradictions",
            "follow_up_questions",
            "confidence_notes",
            "completion_score",
        ]:
            merged[key] = value
            continue

        # For list fields, combine and deduplicate.
        if isinstance(value, list):
            existing_list = merged.get(key, [])
            if not isinstance(existing_list, list):
                existing_list = []

            combined = existing_list + value
            deduped = []
            for item in combined:
                if item not in deduped:
                    deduped.append(item)

            merged[key] = deduped
            continue

        # For dict fields, shallow merge.
        if isinstance(value, dict):
            existing_dict = merged.get(key, {})
            if not isinstance(existing_dict, dict):
                existing_dict = {}

            merged[key] = {
                **existing_dict,
                **{k: v for k, v in value.items() if v not in [None, "", [], {}]},
            }
            continue

        # For scalar fields, update only when new value is useful.
        merged[key] = value

    date_of_birth = merged.get("date_of_birth")
    if date_of_birth:
        merged["age"] = calculate_age(date_of_birth)
    return merged


def _local_fallback_run(
    raw_text: str,
    client_id: str,
    existing_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Local fallback path.

    This keeps the Streamlit demo working even if:
    - OPENAI_API_KEY is missing
    - the Agents SDK is not installed correctly
    - the model call fails
    """
    extracted = local_extract_kyc_profile(raw_text=raw_text, client_id=client_id)
    validation = local_validate_kyc_completeness(extracted)
    questions = local_generate_follow_up_questions(validation)

    extracted["missing_information"] = validation.get("missing_information", [])
    extracted["contradictions"] = validation.get("contradictions", [])
    extracted["confidence_notes"] = validation.get("confidence_notes", [])
    extracted["completion_score"] = validation.get("completion_score", 0)
    extracted["follow_up_questions"] = questions

    return _merge_profile(existing_profile, extracted)


def _tool_trace() -> list[str]:
    return [
        "extract_kyc_profile",
        "validate_kyc_completeness",
        "generate_follow_up_questions",
    ]


def _wrap_result(profile: Dict[str, Any], mode: str, error: Optional[str] = None) -> Dict[str, Any]:
    """
    Return agent results in a wrapper so developer/debug information does not get
    mixed into advisor-facing KYC fields such as confidence_notes.
    """
    result: Dict[str, Any] = {
        "mode": mode,
        "tool_trace": _tool_trace(),
        "profile": profile,
    }
    if error:
        result["error"] = error
    return result


def run_kyc_agent(
    raw_text: str,
    client_id: str = "new_client",
    existing_profile: Optional[Dict[str, Any]] = None,
    force_local: bool = False,
) -> Dict[str, Any]:
    """
    Main function called by Streamlit.

    It tries to run the OpenAI Agents SDK flow. If that fails, it falls back to
    local deterministic extraction so the demo remains usable. Debug/error
    details are returned outside the client profile.
    """
    if not raw_text or not raw_text.strip():
        profile = _merge_profile(
            existing_profile,
            {
                "client_id": client_id,
                "missing_information": ["No onboarding text or document content provided"],
                "contradictions": [],
                "follow_up_questions": [
                    "Please upload or paste onboarding notes, an intake form, or a transcript."
                ],
                "confidence_notes": [
                    "Agent did not run because no input text was provided."
                ],
                "completion_score": 0,
            },
        )
        return _wrap_result(profile, mode="no_input")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if force_local or not api_key:
        profile = _local_fallback_run(
            raw_text=raw_text,
            client_id=client_id,
            existing_profile=existing_profile,
        )
        return _wrap_result(
            profile,
            mode="local_fallback" if force_local else "local_fallback_no_api_key",
        )

    try:
        from agents import Agent, Runner

        model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        kyc_agent = Agent(
            name="Client Onboarding & KYC Agent",
            instructions=AGENT_INSTRUCTIONS,
            model=model_name,
            tools=[
                extract_kyc_profile,
                validate_kyc_completeness,
                generate_follow_up_questions,
            ],
        )

        prompt = f"""
Client ID: {client_id}

Existing profile, if available:
{json.dumps(existing_profile or {}, indent=2)}

Raw onboarding input:
{raw_text}

Return the final merged KYC profile as valid JSON only.
"""

        result = Runner.run_sync(
            kyc_agent,
            prompt,
            max_turns=8,
        )

        parsed = _safe_json_loads(result.final_output)

        if not parsed:
            raise ValueError("Agent did not return valid JSON.")

        parsed["client_id"] = parsed.get("client_id") or client_id
        profile = _merge_profile(existing_profile, parsed)
        return _wrap_result(profile, mode="openai_agents_sdk")

    except Exception as exc:
        profile = _local_fallback_run(
            raw_text=raw_text,
            client_id=client_id,
            existing_profile=existing_profile,
        )
        return _wrap_result(
            profile,
            mode="local_fallback_after_sdk_error",
            error=str(exc),
        )

def build_advisor_summary(profile: Dict[str, Any]) -> str:
    """
    Convert the structured profile into an advisor-readable text summary.

    Streamlit can use this for the top-level advisor view.
    """
    name = profile.get("name") or "Unknown client"
    age = profile.get("age") or "Not confirmed"
    occupation = profile.get("occupation") or "Not confirmed"
    score = profile.get("completion_score", 0)

    risk = profile.get("risk_tolerance", {}) or {}
    risk_value = risk.get("value") or "Not confirmed"
    risk_confidence = risk.get("confidence") or "unknown"

    goals = profile.get("goals") or []
    missing = profile.get("missing_information") or []
    contradictions = profile.get("contradictions") or []
    followups = profile.get("follow_up_questions") or []

    summary = f"""
Client: {name}
Age: {age}
Occupation: {occupation}
Profile completion score: {score}/100

Risk tolerance:
- Value: {risk_value}
- Confidence: {risk_confidence}

Key goals:
{chr(10).join([f"- {goal}" for goal in goals]) if goals else "- Not confirmed"}

Missing information:
{chr(10).join([f"- {item}" for item in missing]) if missing else "- No major missing fields identified"}

Contradictions / review flags:
{chr(10).join([f"- {item}" for item in contradictions]) if contradictions else "- No major contradictions identified"}

Recommended follow-up questions:
{chr(10).join([f"- {item}" for item in followups]) if followups else "- No follow-up questions generated"}
""".strip()

    return summary
