# Mili Client Onboarding & KYC Agent

A Streamlit prototype that helps wealth advisors turn unstructured onboarding
notes into a structured, editable, and reviewable KYC profile.

The agent extracts client details, highlights missing or contradictory
information, and suggests targeted follow-up questions. It supports both an
OpenAI Agents SDK workflow and a deterministic local demo mode, so the full UI
can be explored without an API key.

> This is an advisor-assistance prototype, not a production KYC approval or
> investment-suitability system. An advisor must review and confirm all output.

## Features

- Seeded client records plus support for creating new clients
- Editable identity, financial, goal, risk, and time-horizon fields
- Pasted onboarding notes and `.txt` document uploads
- Multiple active or inactive documents per client
- Extraction of a structured KYC profile from unstructured text
- Completeness scoring, contradiction detection, and confidence notes
- Advisor-ready follow-up questions for unresolved information
- Inspectable and downloadable client JSON
- In-memory session state with no external database required

## How it works

With an API key, GPT performs the semantic work: it reads the active documents,
drafts the profile JSON, reviews completeness, assigns the score, and drafts
advisor follow-up questions from the evidence. The tools run in sequence only to
clean and normalise GPT's drafts:

1. `extract_kyc_profile` cleans and normalises GPT's draft JSON into
   the app schema. In API mode it is not used for local rule-based extraction.
2. `validate_kyc_completeness` cleans GPT's drafted gaps, contradictions,
   confidence concerns, and completion score. In API mode it is not used for
   local rule-based validation.
3. `generate_follow_up_questions` cleans GPT's drafted advisor questions. In API
   mode it is not used for local rule-based question generation.

If the API key is missing, local demo mode is enabled, or the SDK call fails,
the app falls back to the deterministic local extraction, validation, and
question-generation functions. The **Documents & agent** tab shows the mode and
an inspectable trace for the latest run.

New results are merged into the existing profile without allowing empty values
to erase previously captured or advisor-reviewed information. Removing a
document therefore does not automatically remove fields already added to the
profile.

## Quick start

### 1. Create an environment

Python 3.9 or later is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Configure the agent

Copy the example environment file:

```bash
cp .env.example .env
```

The app works without an API key and automatically uses its local deterministic
fallback. To use the OpenAI Agents SDK, set `OPENAI_API_KEY` in `.env`:

```dotenv
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4.1-mini
USE_LOCAL_DEMO=false
```

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | No | Enables the OpenAI Agents SDK workflow when present. |
| `OPENAI_MODEL` | No | Model used by the SDK workflow. Defaults to `gpt-4.1-mini`. |
| `USE_LOCAL_DEMO` | No | Set to `true` to force deterministic local processing. |

### 3. Run the app

```bash
streamlit run app.py
```

Streamlit will print the local URL, typically `http://localhost:8501`.

## Using the app

1. Select a seeded client from the sidebar or create a new client.
2. Review or edit the current profile in **Client profile**.
3. Add, edit, activate, or remove source material in **Documents & agent**.
4. Click **Run KYC Agent** to process all active documents.
5. Review the updated fields, flags, confidence notes, and follow-up questions.
6. Inspect or download the full record from **Underlying JSON**.

The document form includes contradictory and incomplete sample inputs for a
quick demonstration.

## Execution modes

| Mode shown in the UI | Meaning |
| --- | --- |
| `openai_agents_sdk` | The OpenAI Agents SDK completed the workflow: GPT drafted the profile, validation, and questions; tools only normalised those drafts. |
| `local_fallback_no_api_key` | No API key was configured, so local rules were used. |
| `local_fallback` | Local mode was explicitly enabled. |
| `local_fallback_after_sdk_error` | The SDK failed and the app recovered locally. |

When an SDK error triggers the fallback, the app displays the reason below the
agent run controls.

## Tests

Run the unit tests with:

```bash
python -m unittest discover -v
```

The tests cover local identity and marital-status extraction, explicit local
mode selection, and profile merging without duplicated semantic facts.

## Project structure

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit UI, client/session state, document management, and profile editing |
| `agent.py` | Agent orchestration, mode selection, response parsing, and fallback handling |
| `tools.py` | Extraction, validation, follow-up generation, and profile merging |
| `schemas.py` | Pydantic models for structured KYC data |
| `sample_data.py` | Seeded clients and demonstration onboarding text |
| `test_agent.py` | Agent mode and merge-behavior tests |
| `test_tools.py` | Deterministic extraction tests |

## Prototype boundaries

- Client records and documents live only in Streamlit session state.
- Only pasted text and UTF-8-compatible `.txt` uploads are supported.
- Local extraction and validation use simplified rules, not firm- or
  jurisdiction-specific KYC policy.
- There is no authentication, encrypted storage, audit trail, OCR, or CRM
  integration.
- The agent does not approve or reject clients, recommend investments, or make
  final suitability decisions.

## Possible next steps

- Add secure persistence and role-based access controls.
- Support PDF parsing, OCR, and document provenance.
- Add jurisdiction- and firm-specific validation policies.
- Integrate with CRM and portfolio systems.
- Add advisor approvals, field-level audit history, and monitoring.
