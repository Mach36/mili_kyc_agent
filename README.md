# Mili Client Onboarding & KYC Agent

A Streamlit prototype for wealth advisors to convert unstructured onboarding inputs into a structured, reviewable KYC profile.

## Why this agent

I chose the Client Onboarding & KYC Agent because onboarding is a high-friction workflow at the start of the advisor-client relationship. Advisors often receive fragmented inputs through intake forms, meeting notes, emails, chat transcripts, and documents. The agent helps extract a structured profile, identify missing or contradictory information, and generate targeted follow-up questions.

## Product flow

1. Advisor selects an existing client from the sidebar or creates a new client.
2. Advisor reviews the current KYC profile.
3. Advisor adds, edits, or removes onboarding documents.
4. Advisor runs the KYC agent.
5. The app updates the profile and shows missing fields, contradictions, confidence notes, and follow-up questions.
6. Advisor can inspect and download the underlying JSON.

Removing a document does not erase already-filled KYC fields. This is intentional because an advisor may have already reviewed or confirmed those fields.

## Agent tools

The app uses three tool boundaries:

- `extract_kyc_profile`: extracts structured KYC details from raw onboarding text.
- `validate_kyc_completeness`: checks missing fields, contradictions, and confidence notes.
- `generate_follow_up_questions`: creates targeted questions for the advisor to ask the client.

The app includes a local deterministic fallback so the UI can be demonstrated even without an API key. With `OPENAI_API_KEY` configured and `USE_LOCAL_DEMO=false`, it runs the OpenAI Agents SDK workflow.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Add your OpenAI API key to `.env`.

## Run

```bash
streamlit run app.py
```

## What is mocked

- Client data is stored in Streamlit session state.
- Documents are stored in session state, not a secure document store.
- Only pasted text and `.txt` upload are supported in this v1.
- KYC/completeness checks are simplified and rule-based inside the tools.

## Known limitations

- No authentication or database persistence.
- No scanned PDF/OCR support.
- Not a production KYC approval system.
- The agent does not approve/reject clients or make suitability decisions.

## Future improvements

- Secure database and document storage.
- PDF parsing and OCR.
- CRM integration.
- Advisor approval workflow and audit trail.
- More robust validation rules by jurisdiction and firm policy.
