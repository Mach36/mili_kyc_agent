from __future__ import annotations

from typing import Dict, Any


def seed_clients() -> Dict[str, Dict[str, Any]]:
    return {
        "client_001": {
            "client_id": "client_001",
            "kyc_reviewed": False,
            "profile": {
                "client_id": "client_001",
                "name": "Anika Sharma",
                "gender": "Female",
                "pronouns": "she/her",
                "date_of_birth": "1984-04-15",
                "age": 42,
                "occupation": "Product Director",
                "marital_status": "Married",
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
                    "title": "Consolidated KYC Fact Find",
                    "text": (
                        "Client name: Anika Sharma\n"
                        "Gender: Female\n"
                        "Pronouns: she/her\n"
                        "Date of birth: 15 April 1984\n"
                        "Occupation: Product Director\n"
                        "Marital status: Married\n"
                        "Dependents: Spouse, one daughter aged 12\n"
                        "Household income: Approximately INR 55L annually\n"
                        "Goals: Retirement planning in 18-20 years; daughter's "
                        "university education in around 6 years.\n"
                        "Risk tolerance: Moderate. Anika is comfortable with moderate "
                        "risk but does not want large short-term losses.\n"
                        "Liquidity needs: She may need liquidity for a home renovation "
                        "in the next 18 months. The amount of emergency cash that must "
                        "remain untouched has not been confirmed.\n"
                        "Existing investments include equity mutual funds, fixed deposits, and "
                        "emergency savings.\n"
                        "Liabilities: Home loan EMI.\n"
                        "Information not provided: Existing portfolio value and "
                        "insurance coverage.\n"
                        "Advisor review note: Confirm risk tolerance with a short "
                        "questionnaire."
                    ),
                    "active": True,
                }
            ],
        },
        "client_002": {
            "client_id": "client_002",
            "kyc_reviewed": False,
            "profile": {
                "client_id": "client_002",
                "name": "Rohan Mehta",
                "gender": "Male",
                "pronouns": "he/him",
                "date_of_birth": "1990-02-10",
                "age": 36,
                "occupation": "Business owner",
                "marital_status": "Married",
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
            "documents": [
                {
                    "doc_id": "doc_002",
                    "title": "Discovery Call Notes",
                    "text": (
                        "Discovery call for Rohan Mehta, DOB 10 February 1990. He is a "
                        "man and uses he/him pronouns. He is a "
                        "business owner and is married; wife and one son depend on him. "
                        "Kept coming back to aggressive growth and growing wealth over "
                        "roughly the next 5 years, with buying a second property also "
                        "somewhere on the list. Said he wants the portfolio positioned "
                        "for growth, but later said he really dislikes losses and cannot "
                        "tolerate seeing his investments decline - need to pin down what "
                        "that actually means. Existing investments include business cash "
                        "flows and equity investments. We ran out of time before getting "
                        "an income range, and neither debt obligations nor near-term cash "
                        "needs were properly discussed. Follow up on the maximum "
                        "short-term fall he could accept and whether any liabilities are "
                        "attached to the business."
                    ),
                    "active": True,
                }
            ],
        },
    }


NEW_CLIENT_SAMPLE = """Client: Priya Kapoor. Date of birth: 12 May 1987. Works as a senior consultant. She wants to invest for retirement and for her son's education. She says she is low risk and wants capital protection, but later says she wants aggressive growth and high returns within 2 years. She may need cash for a home renovation next year. Her husband and son are dependents. Existing assets include fixed deposits and some equity mutual funds. No income, liabilities, or exact investment amount provided."""

INCOMPLETE_SAMPLE = """Client: Kabir Arora. Met during discovery call. He wants help with long-term wealth creation and may invest later this year. He mentioned that his parents may depend on him financially. No date of birth, income, existing assets, liabilities, risk tolerance, or time horizon were confirmed."""

PRIYA_DISCOVERY_CALL_SAMPLE = """Call Transcript 1 - Priya Kapoor Initial Discovery Call

Advisor: Good morning, Priya. Thanks for joining. To begin with, could you confirm a few basic details for your client profile?

Priya: Sure. My full name is Priya Kapoor. I am 39 years old and I work as a Senior Strategy Consultant.

Advisor: Thank you. Could you confirm your marital status and dependents?

Priya: I am divorced. My son is financially dependent on me. He is 8 years old.

Advisor: Understood. What are the main reasons you are seeking financial advice at this stage?

Priya: I want to start planning more seriously for the long term. Retirement is one goal, but I also want to plan for my son's education. He is still young, but I know education costs can become significant later.

Advisor: Are there any shorter-term financial needs we should keep in mind?

Priya: Yes. I may renovate my home next year. I may need around INR 12 to 15 lakh for that in the next 12 to 18 months. I do not want that money exposed to too much market risk.

Advisor: What is your approximate household income?

Priya: Around INR 65 lakh per year.

Advisor: Could you briefly describe your existing investments or assets?

Priya: I have fixed deposits, EPF, some equity mutual funds, and company stock from my employer.

Advisor: Do you currently have any loans or liabilities?

Priya: I have an ongoing home loan EMI. Other than that, I do not think there is anything major, but I would need to check.

Advisor: How would you describe your risk appetite?

Priya: Generally, I am cautious. I do not like taking very large risks, especially with money that I may need soon.

Advisor: For longer-term goals like retirement or education, would you be comfortable with some market volatility?

Priya: Yes, for long-term goals I am comfortable with moderate risk. But I would not want short-term losses to affect the money needed for renovation or emergency savings.

Advisor: Thank you. I will capture that. We may need to separate your short-term liquidity needs from your longer-term investment goals.

Priya: Yes, that makes sense. I prefer something simple and easy to understand."""

PRIYA_FOLLOW_UP_SAMPLE = """Call Transcript 2 - Priya Kapoor Follow-up Clarification Call

Advisor: Hi Priya, thanks for joining again. I wanted to clarify a few points from our previous discussion.

Priya: Sure.

Advisor: Last time, you mentioned being cautious with money. But you also mentioned wanting strong growth. Could you explain that a little more?

Priya: Yes. I would like part of my money to grow faster. Ideally, if a portion could double in 2 to 3 years, that would be great. But I do not want to gamble or lose a lot of money.

Advisor: That is useful to clarify. So we should treat the renovation fund and emergency savings separately from any long-term growth allocation.

Priya: Yes, exactly. I do not want money needed soon to be exposed to short-term market losses.

Advisor: How much emergency cash would you like to keep available?

Priya: I would like to keep at least 9 months of expenses as emergency savings.

Advisor: What are your monthly household expenses approximately?

Priya: I am not sure of the exact number. I can check and share it later.

Advisor: How much capital are you planning to invest initially?

Priya: I have not decided the exact amount yet. I need to review my current portfolio and cash position.

Advisor: Do you know the current value of your overall investment portfolio?

Priya: Not exactly. I can pull together the details of my mutual funds, fixed deposits, EPF, and company stock.

Advisor: Do you have life insurance or health insurance coverage?

Priya: I have some employer-provided health insurance, but I am not sure whether it is enough. I have not reviewed life insurance recently.

Advisor: Since you are divorced and your son is dependent on you, we should also review protection planning and nominee details later.

Priya: Yes, that would be helpful.

Advisor: To summarise, your key goals are retirement planning, your son's education, and maintaining liquidity for possible home renovation. Your risk profile needs clarification because you described yourself as cautious but also mentioned high growth expectations over a short period.

Priya: Yes, that summary is accurate.

Advisor: For the next step, please share your current portfolio value, monthly expenses, investable amount, insurance details, nominee information, and any other liabilities apart from the home loan.

Priya: Sure, I will send those after checking."""
