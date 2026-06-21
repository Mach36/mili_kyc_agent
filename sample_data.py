from __future__ import annotations

from typing import Dict, Any


def seed_clients() -> Dict[str, Dict[str, Any]]:
    return {
        "client_001": {
            "client_id": "client_001",
            "profile": {
                "client_id": "client_001",
                "name": "Anika Sharma",
                "date_of_birth": "1984-04-15",
                "age": 42,
                "occupation": "Product Director",
                "goals": [
                    "Retirement planning in 18-20 years",
                    "Daughter's university education in around 6 years",
                ],
                "risk_tolerance": {
                    "value": "Moderate",
                    "confidence": "medium",
                    "evidence": "Comfortable with moderate risk but does not want large short-term losses.",
                },
                "time_horizon": {
                    "retirement": "18-20 years",
                    "education": "6 years",
                },
                "liquidity_needs": ["May need liquidity for home renovation in the next 18 months."],
                "dependents": ["Spouse", "One daughter aged 12"],
                "income": "Approx. INR 55L annual household income",
                "assets": ["Existing equity mutual funds", "Fixed deposits", "Emergency savings"],
                "liabilities": ["Home loan EMI"],
                "missing_information": ["Existing portfolio value", "Insurance coverage"],
                "contradictions": [],
                "follow_up_questions": [
                    "What is the current market value of the existing portfolio?",
                    "How much emergency cash should remain untouched?",
                ],
                "confidence_notes": ["Risk tolerance should be confirmed with a short questionnaire."],
                "completion_score": 84,
            },
            "documents": [
                {
                    "doc_id": "doc_001",
                    "title": "Initial Meeting Notes",
                    "text": "Client: Anika Sharma. Date of birth: 15 April 1984. Works as a Product Director. Wants retirement planning and daughter's university education. Comfortable with moderate risk but does not want large short-term losses. May need liquidity for home renovation in the next 18 months. Spouse and daughter are dependents. Income approx INR 55L. Has equity mutual funds, fixed deposits and emergency savings. Has home loan EMI.",
                    "active": True,
                }
            ],
        },
        "client_002": {
            "client_id": "client_002",
            "profile": {
                "client_id": "client_002",
                "name": "Rohan Mehta",
                "date_of_birth": "1990-02-10",
                "age": 36,
                "occupation": "Business owner",
                "goals": ["Grow wealth over the next 5 years", "Buy a second property"],
                "risk_tolerance": {
                    "value": "High / Growth-oriented",
                    "confidence": "low",
                    "evidence": "Client says he wants aggressive growth but also dislikes losses.",
                },
                "time_horizon": {"wealth_growth": "5 years"},
                "liquidity_needs": [],
                "dependents": ["Wife", "One son"],
                "income": None,
                "assets": ["Business cash flows", "Equity investments"],
                "liabilities": [],
                "missing_information": ["Income range", "Liabilities / debt obligations", "Liquidity needs"],
                "contradictions": ["Client wants aggressive growth but also says he cannot tolerate losses."],
                "follow_up_questions": [
                    "What level of short-term decline would be unacceptable?",
                    "Does the client have business loans or other debt obligations?",
                ],
                "confidence_notes": ["Risk tolerance is internally inconsistent and needs advisor review."],
                "completion_score": 68,
            },
            "documents": [],
        },
    }


NEW_CLIENT_SAMPLE = """Client: Priya Kapoor. Date of birth: 12 May 1987. Works as a senior consultant. She wants to invest for retirement and for her son's education. She says she is low risk and wants capital protection, but later says she wants aggressive growth and high returns within 2 years. She may need cash for a home renovation next year. Her husband and son are dependents. Existing assets include fixed deposits and some equity mutual funds. No income, liabilities, or exact investment amount provided."""

INCOMPLETE_SAMPLE = """Client: Kabir Arora. Met during discovery call. He wants help with long-term wealth creation and may invest later this year. He mentioned that his parents may depend on him financially. No date of birth, income, existing assets, liabilities, risk tolerance, or time horizon were confirmed."""
