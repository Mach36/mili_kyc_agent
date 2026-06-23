from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

from agent import run_kyc_agent
from sample_data import (
    INCOMPLETE_SAMPLE,
    NEW_CLIENT_SAMPLE,
    PRIYA_DISCOVERY_CALL_SAMPLE,
    PRIYA_FOLLOW_UP_SAMPLE,
    seed_clients,
)
from text_upload import decode_text_upload
from tools import (
    calculate_age,
    calculate_profile_completion,
    merge_kyc_profiles,
    normalise_profile_list,
    normalise_time_horizon,
)

APP_TITLE = "Mili KYC Agent"
PROFILE_TAB = "Client profile"
DOCUMENTS_TAB = "Documents & agent"
JSON_TAB = "Underlying JSON"

st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="wide")


def apply_global_styles() -> None:
    """Apply the app's visual system without changing Streamlit interactions."""
    st.markdown(
        f"""
        <style>
        :root {{
            --mili-navy: #142b4a;
            --mili-blue: #246b83;
            --mili-teal: #20a39e;
            --mili-mint: #e8f7f5;
            --mili-selected: light-dark(#eaf1f8, #1d3048);
            --mili-surface: light-dark(#ffffff, #172033);
            --mili-surface-soft: light-dark(#f5f8fb, #111827);
            --mili-border: light-dark(#dce5ed, #334155);
            --mili-text: light-dark(#172033, #f1f5f9);
            --mili-muted: light-dark(#607086, #a8b4c5);
            --mili-shadow: 0 10px 28px rgba(20, 43, 74, 0.08);
            --mili-radius: 0.75rem;
        }}

        .stApp {{
            color: var(--mili-text);
            background:
                radial-gradient(circle at 88% 0%, rgba(32, 163, 158, 0.08), transparent 24rem),
                var(--mili-surface-soft);
        }}

        [data-testid="stHeader"] {{
            background: color-mix(in srgb, var(--mili-surface) 90%, transparent);
            border-bottom: 1px solid var(--mili-border);
            backdrop-filter: blur(12px);
        }}
        [data-testid="stHeader"] [data-testid="stToolbar"] > div > div:first-child::after {{
            content: "{APP_TITLE}";
            margin-left: 1rem;
            color: var(--mili-navy);
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            white-space: nowrap;
        }}

        .block-container {{
            max-width: 86rem;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }}
        .block-container h1 {{
            margin-bottom: 0.2rem;
            color: var(--mili-navy);
            font-size: clamp(2rem, 3vw, 2.8rem);
            font-weight: 750;
            letter-spacing: -0.035em;
        }}
        .block-container h2,
        .block-container h3 {{
            color: var(--mili-navy);
            letter-spacing: -0.015em;
        }}
        .mili-eyebrow {{
            display: block;
            margin: 0 0 0.3rem;
            padding-top: 0.7rem;
            color: var(--mili-blue);
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            line-height: 1.4;
            overflow: visible;
            text-transform: uppercase;
        }}
        [data-testid="stMarkdownContainer"]:has(> .mili-eyebrow) {{
            overflow: visible;
        }}

        [data-testid="stSidebar"] {{
            background: light-dark(#f8fbfd, #111827);
            border-right: 1px solid var(--mili-border);
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding-top: 1rem;
        }}
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button {{
            visibility: visible !important;
            opacity: 1 !important;
        }}
        [data-testid="stSidebar"] h1 {{
            color: var(--mili-navy);
            font-size: 1.35rem;
            letter-spacing: -0.02em;
        }}
        [data-testid="stSidebar"] h3 {{
            margin-top: 1rem;
            color: var(--mili-muted);
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            justify-content: flex-start;
            border-color: transparent;
            background: transparent;
            box-shadow: none;
            font-weight: 600;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            border-color: rgba(32, 163, 158, 0.35);
            background: var(--mili-mint);
            color: var(--mili-navy);
        }}
        .st-key-new_client_panel {{
            margin-top: 0.35rem;
            padding: 0 0.15rem;
        }}
        .st-key-new_client_panel h3 {{
            margin: 0 0 0.15rem;
            color: var(--mili-muted);
            font-size: 0.72rem;
            letter-spacing: 0.09em;
        }}
        .st-key-new_client_panel label,
        .st-key-new_client_panel label p {{
            color: var(--mili-muted) !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
        }}
        .st-key-new_client_panel [data-testid="stVerticalBlock"] {{
            gap: 0.55rem;
        }}
        .st-key-new_client_panel .stTextInput,
        .st-key-new_client_panel .stButton {{
            margin: 0;
        }}
        [class*="st-key-new_client_name_"] [data-baseweb="input"] {{
            min-height: 2.35rem;
            height: 2.35rem;
            border: 1px solid var(--mili-border) !important;
            border-radius: 0.55rem !important;
            background: var(--mili-surface) !important;
            box-shadow: none !important;
        }}
        [class*="st-key-new_client_name_"] input {{
            min-height: 2.25rem;
            height: 2.25rem;
            padding-inline: 0.7rem;
            border: 0 !important;
            background: transparent !important;
            color: var(--mili-text) !important;
        }}
        [class*="st-key-new_client_name_"] [data-baseweb="input"]:focus-within {{
            border-color: var(--mili-blue) !important;
            box-shadow: 0 0 0 1px var(--mili-blue) !important;
        }}
        .st-key-create_client button {{
            min-height: 2.35rem !important;
            justify-content: center !important;
            margin: 0 !important;
            border-color: #246b83 !important;
            border-radius: 0.55rem !important;
            background: #246b83 !important;
            color: #ffffff !important;
            box-shadow: none !important;
            font-size: 0.82rem;
        }}
        .st-key-create_client button:hover {{
            border-color: #1d596d !important;
            background: #1d596d !important;
            color: #ffffff !important;
            transform: none;
            box-shadow: none !important;
        }}
        .st-key-remove_selected_client button {{
            min-height: 2rem !important;
            justify-content: center !important;
            color: #b42318 !important;
            font-size: 0.78rem;
        }}
        .st-key-remove_selected_client button:hover {{
            border-color: color-mix(in srgb, #b42318 35%, transparent) !important;
            background: color-mix(in srgb, #b42318 8%, transparent) !important;
            color: #b42318 !important;
            box-shadow: none !important;
            transform: none;
        }}

        .stTextInput input,
        .stTextArea textarea,
        .stDateInput input,
        [data-baseweb="select"] > div {{
            border-color: var(--mili-border) !important;
            border-radius: 0.625rem !important;
            background-color: var(--mili-surface) !important;
        }}
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stDateInput input:focus {{
            border-color: var(--mili-teal) !important;
            box-shadow: 0 0 0 1px var(--mili-teal) !important;
        }}
        .stTextArea textarea {{
            line-height: 1.55;
        }}
        .stButton > button,
        .stDownloadButton > button {{
            min-height: 2.5rem;
            border-radius: 0.625rem;
            font-weight: 650;
            transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
        }}
        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            border-color: var(--mili-teal);
            transform: translateY(-1px);
            box-shadow: 0 5px 14px rgba(20, 43, 74, 0.1);
        }}
        .stButton > button[kind="primary"] {{
            border-color: var(--mili-blue);
            background: linear-gradient(135deg, var(--mili-navy), var(--mili-blue));
            box-shadow: 0 7px 18px rgba(20, 43, 74, 0.18);
        }}
        .st-key-download_client_json button {{
            position: relative;
            top: 0.3rem;
            min-height: 2rem;
            padding: 0.3rem 0.6rem;
            border-color: transparent;
            background: transparent;
            color: var(--mili-muted);
            box-shadow: none;
            font-size: 0.82rem;
        }}
        .st-key-download_client_json button:hover {{
            border-color: transparent;
            background: var(--mili-selected);
            color: var(--mili-navy);
            box-shadow: none;
            transform: none;
        }}

        [data-testid="stExpander"] {{
            overflow: hidden;
            border: 1px solid var(--mili-border);
            border-radius: var(--mili-radius);
            background: var(--mili-surface);
            box-shadow: 0 4px 15px rgba(20, 43, 74, 0.04);
        }}
        [data-testid="stExpander"] summary {{
            font-weight: 700;
        }}
        [class*="st-key-document_card_"] [class*="st-key-title_doc_"] [data-baseweb="input"] {{
            border-color: transparent;
            background: transparent;
            box-shadow: none;
        }}
        [class*="st-key-document_card_"] [class*="st-key-title_doc_"] [data-baseweb="input"]:hover,
        [class*="st-key-document_card_"] [class*="st-key-title_doc_"] [data-baseweb="input"]:focus-within {{
            border-color: var(--mili-border);
            background: var(--mili-surface);
        }}
        [class*="st-key-document_card_"] [class*="st-key-title_doc_"] input {{
            padding-left: 0.65rem;
            font-size: 1.05rem;
            font-weight: 700;
        }}
        [class*="st-key-toggle_contents_"] button {{
            padding: 0.2rem 0;
            color: var(--mili-muted);
            font-weight: 650;
        }}
        [class*="st-key-toggle_contents_"] button:hover {{
            box-shadow: none;
            transform: none;
        }}
        [data-testid="stAlert"] {{
            border-radius: var(--mili-radius);
        }}
        [data-testid="stProgress"] > div > div {{
            height: 0.55rem;
            border-radius: 999px;
        }}
        [data-testid="stProgress"] [data-baseweb="progress-bar"] > div > div > div {{
            background: linear-gradient(90deg, var(--mili-blue), var(--mili-teal));
        }}

        [data-testid="stTabs"] {{
            margin-top: -2rem;
        }}
        [data-testid="stTabs"] div:has(> [data-baseweb="tab-list"]) {{
            position: sticky;
            top: 3.75rem;
            z-index: 1000;
            isolation: isolate;
            margin: 0 0 1.25rem;
            padding: 0.35rem;
            border: 1px solid var(--mili-border);
            border-radius: var(--mili-radius);
            background: color-mix(in srgb, var(--mili-surface) 94%, transparent);
            box-shadow: var(--mili-shadow);
            backdrop-filter: blur(12px);
        }}
        [data-baseweb="tab-list"] {{
            gap: 0.3rem;
        }}
        [data-baseweb="tab"] {{
            height: 2.65rem;
            padding: 0 1rem;
            border-radius: 0.5rem;
            color: var(--mili-muted);
            font-weight: 650;
        }}
        [data-baseweb="tab"][aria-selected="true"] {{
            background: var(--mili-mint);
            color: var(--mili-navy);
        }}

        hr {{
            border-color: var(--mili-border) !important;
        }}
        [data-testid="stCaptionContainer"] {{
            color: var(--mili-muted);
        }}

        @media (max-width: 760px) {{
            .block-container {{
                padding-top: 1.5rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }}
            [data-testid="stTabs"] div:has(> [data-baseweb="tab-list"]) {{
                top: 3.25rem;
                margin-top: 0;
            }}
            [data-baseweb="tab"] {{
                padding: 0 0.75rem;
                font-size: 0.82rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_global_styles()


PROFILE_FIELDS = [
    "name",
    "gender",
    "pronouns",
    "date_of_birth",
    "age",
    "occupation",
    "income",
]

LIST_FIELDS = [
    "goals",
    "liquidity_needs",
    "dependents",
    "assets",
    "liabilities",
    "missing_information",
    "contradictions",
    "follow_up_questions",
    "confidence_notes",
]

PROFILE_TEXT_AREA_HEIGHT = 120

MARITAL_STATUS_OPTIONS = [
    "Single",
    "Married",
    "Divorced",
    "Widowed",
    "Separated",
]

GENDER_OPTIONS = [
    "Female",
    "Male",
    "Non-binary",
    "Other",
    "Prefer not to say",
]


def init_state() -> None:
    if "clients" not in st.session_state:
        st.session_state.clients = seed_clients()
    for client in st.session_state.clients.values():
        client.setdefault("kyc_reviewed", False)
    selected_client_id = st.session_state.get("selected_client_id")
    if selected_client_id not in st.session_state.clients:
        st.session_state.selected_client_id = next(
            iter(st.session_state.clients), None
        )
    if "last_agent_run" not in st.session_state:
        st.session_state.last_agent_run = None
    # These counters are used to reset Streamlit input widgets after submit.
    if "new_client_input_version" not in st.session_state:
        st.session_state.new_client_input_version = 0
    last_unnamed_client_id = st.session_state.get("last_unnamed_client_id")
    if last_unnamed_client_id not in st.session_state.clients:
        st.session_state.last_unnamed_client_id = None
    if "document_input_version" not in st.session_state:
        st.session_state.document_input_version = 0
    if "document_upload_version" not in st.session_state:
        st.session_state.document_upload_version = 0
    if "profile_editor_version" not in st.session_state:
        st.session_state.profile_editor_version = 0
    if st.session_state.get("pending_client_removal") not in st.session_state.clients:
        st.session_state.pending_client_removal = None


def new_empty_profile(client_id: str, name: str) -> Dict[str, Any]:
    return {
        "client_id": client_id,
        "name": name or None,
        "gender": None,
        "pronouns": None,
        "date_of_birth": None,
        "age": None,
        "occupation": None,
        "marital_status": None,
        "goals": [],
        "risk_tolerance": {"value": None, "confidence": "unknown", "evidence": None},
        "time_horizon": {},
        "liquidity_needs": [],
        "dependents": [],
        "income": None,
        "assets": [],
        "liabilities": [],
        "missing_information": [],
        "contradictions": [],
        "follow_up_questions": [],
        "confidence_notes": [],
        "completion_score": 0,
    }


def is_untouched_unnamed_client(client_id: str) -> bool:
    """Return whether a generated unnamed client still has no advisor input."""
    client = st.session_state.clients.get(client_id)
    if not client or client.get("documents") or client.get("kyc_reviewed"):
        return False

    profile = client.get("profile", {})
    baseline = new_empty_profile(client_id, "")
    profile_without_score = {
        key: value for key, value in profile.items() if key != "completion_score"
    }
    baseline_without_score = {
        key: value for key, value in baseline.items() if key != "completion_score"
    }
    return profile_without_score == baseline_without_score


def remove_client(client_id: str) -> None:
    """Remove a client and keep the active selection valid."""
    client_ids = list(st.session_state.clients)
    if client_id not in st.session_state.clients:
        return

    removed_index = client_ids.index(client_id)
    del st.session_state.clients[client_id]
    remaining_ids = list(st.session_state.clients)
    st.session_state.selected_client_id = (
        remaining_ids[min(removed_index, len(remaining_ids) - 1)]
        if remaining_ids
        else None
    )
    st.session_state.last_agent_run = None
    st.session_state.profile_editor_version += 1
    st.session_state.pending_client_removal = None


@st.dialog("Remove client?")
def render_remove_client_dialog(client_id: str, client_name: str) -> None:
    st.write(
        f"Remove **{client_name}** and all of their documents and profile data? "
        "This cannot be undone."
    )
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button(
            "Remove client",
            key=f"confirm_remove_client_{client_id}",
            type="primary",
            use_container_width=True,
        ):
            remove_client(client_id)
            st.toast(f"{client_name} removed")
            st.rerun()
    with cancel_col:
        if st.button(
            "Cancel",
            key=f"cancel_remove_client_{client_id}",
            use_container_width=True,
        ):
            st.session_state.pending_client_removal = None
            st.rerun()


def merge_profile(existing: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Merge agent output without deleting advisor-confirmed fields when new data is incomplete."""
    return merge_kyc_profiles(existing, extracted)


def list_to_text(items: Any, field_name: Optional[str] = None) -> str:
    return "\n".join(normalise_profile_list(items, field_name))


def text_to_list(value: str) -> List[str]:
    return [line.strip(" -•\t") for line in value.splitlines() if line.strip(" -•\t")]


def clear_document_upload_for_sample(sample_key: str) -> None:
    """Reset the uploader when a sample becomes the active input source."""
    if st.session_state.get(sample_key) != "None":
        st.session_state.document_upload_version += 1


def normalise_time_horizon_key(value: str) -> str:
    """Convert an advisor-facing label into a stable JSON key."""
    cleaned = (value or "").strip().lower()
    cleaned = cleaned.replace("&", "and")
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in cleaned)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or f"timeline_{uuid.uuid4().hex[:6]}"


def format_time_horizon_label(key: str) -> str:
    """Convert JSON keys like child_education into advisor-facing labels."""
    return (key or "").replace("_", " ").strip().title() or "Goal / Need"


def disable_risk_confidence_typing() -> None:
    """Keep Streamlit's select UI while disabling its built-in search input."""
    components.html(
        """
        <script>
        const hostDocument = window.parent.document;
        const riskSelector = '[class*="st-key-risk_tolerance_control_"] .stSelectbox input';
        const genderSelector = '[class*="st-key-identity_details_"] .stSelectbox input';
        const lockedSelectSelector = [
            riskSelector,
            genderSelector,
        ].join(', ');

        function markSelectMenu() {
            const riskInput = hostDocument.querySelector(riskSelector);
            const genderInput = hostDocument.querySelector(genderSelector);
            const riskMenuIsOpen = riskInput?.getAttribute('aria-expanded') === 'true';
            const genderMenuIsOpen = genderInput?.getAttribute('aria-expanded') === 'true';
            hostDocument.querySelectorAll('[data-testid="stSelectboxVirtualDropdown"]').forEach((menu) => {
                if (riskMenuIsOpen) {
                    menu.dataset.riskConfidenceMenu = 'true';
                } else {
                    delete menu.dataset.riskConfidenceMenu;
                }
                if (genderMenuIsOpen) {
                    menu.dataset.genderMenu = 'true';
                } else {
                    delete menu.dataset.genderMenu;
                }
            });
        }

        function lockConfidenceInput() {
            hostDocument.querySelectorAll(lockedSelectSelector).forEach((input) => {
                input.readOnly = true;
                input.setAttribute('inputmode', 'none');
                if (input.dataset.selectTypingLocked === 'true') return;

                input.dataset.selectTypingLocked = 'true';
                input.addEventListener('beforeinput', (event) => event.preventDefault());
                input.addEventListener('keydown', (event) => {
                    if (event.key.length === 1 || event.key === 'Backspace' || event.key === 'Delete') {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                });
            });
            markSelectMenu();
        }

        lockConfidenceInput();
        const observer = new MutationObserver(lockConfidenceInput);
        observer.observe(hostDocument.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['aria-expanded'],
        });
        window.addEventListener('beforeunload', () => observer.disconnect());
        </script>
        """,
        height=0,
        width=0,
    )


def select_main_tab_in_browser(tab_label: str) -> None:
    """Select a main tab after Streamlit reconciles the rerun in the browser."""
    encoded_label = json.dumps(tab_label)
    components.html(
        f"""
        <script>
        const hostDocument = window.parent.document;
        const targetLabel = {encoded_label};
        let attempts = 0;

        function selectTargetTab() {{
            attempts += 1;
            const tabs = hostDocument.querySelectorAll(
                '[data-testid="stTabs"] [data-baseweb="tab"]'
            );
            const target = Array.from(tabs).find(
                (tab) => tab.textContent.trim() === targetLabel
            );

            if (!target) {{
                if (attempts < 40) window.setTimeout(selectTargetTab, 50);
                return;
            }}

            if (target.getAttribute('aria-selected') !== 'true') {{
                target.click();
            }}

            function scrollPageToTop() {{
                const main = hostDocument.querySelector('[data-testid="stMain"]');
                main?.scrollTo({{ top: 0, behavior: 'auto' }});
                hostDocument.scrollingElement?.scrollTo({{ top: 0, behavior: 'auto' }});
                window.parent.scrollTo({{ top: 0, behavior: 'auto' }});
            }}

            window.requestAnimationFrame(() => {{
                window.requestAnimationFrame(scrollPageToTop);
            }});
            window.setTimeout(scrollPageToTop, 100);
        }}

        window.requestAnimationFrame(selectTargetTab);
        </script>
        """,
        height=0,
        width=0,
    )


def render_time_horizon_editor(profile: Dict[str, Any], client_id: str, version: int) -> None:
    """
    Render time_horizon as clean editable rows instead of raw JSON.

    The underlying profile still stores time_horizon as a dictionary so the JSON
    output remains structured, but advisors do not need to edit raw JSON.
    """
    st.markdown("**Goal timelines**")
    # st.caption("Each row links a goal or liquidity need to the relevant time horizon.")

    raw_time_horizon = normalise_time_horizon(profile.get("time_horizon", {}))
    profile["time_horizon"] = raw_time_horizon

    updated_time_horizon: Dict[str, str] = {}
    remove_key = None

    header = st.columns([1.4, 2.3, 0.7])
    header[0].caption("Goal / need")
    header[1].caption("Time horizon")
    header[2].caption("Action")

    if not raw_time_horizon:
        st.info("No time horizons captured yet. Add one below or run the agent on onboarding notes.")

    for idx, (key, value) in enumerate(raw_time_horizon.items()):
        cols = st.columns([1.4, 2.3, 0.7])
        label = cols[0].text_input(
            "Goal / need",
            value=format_time_horizon_label(key),
            key=f"timeline_label_{client_id}_{version}_{idx}",
            label_visibility="collapsed",
        )
        horizon = cols[1].text_input(
            "Time horizon",
            value=str(value or ""),
            key=f"timeline_value_{client_id}_{version}_{idx}",
            label_visibility="collapsed",
        )
        with cols[2]:
            if st.button("Remove", key=f"timeline_remove_{client_id}_{version}_{idx}"):
                remove_key = key

        if remove_key != key and label.strip() and horizon.strip():
            updated_time_horizon[normalise_time_horizon_key(label)] = horizon.strip()

    if remove_key:
        profile["time_horizon"] = updated_time_horizon
        st.session_state.profile_editor_version += 1
        st.rerun()

    st.markdown("Add another timeline")
    add_cols = st.columns([1.4, 2.3, 0.7])
    new_label = add_cols[0].text_input(
        "New goal / need",
        value="",
        placeholder="e.g. Retirement",
        key=f"timeline_new_label_{client_id}_{version}",
        label_visibility="collapsed",
    )
    new_horizon = add_cols[1].text_input(
        "New time horizon",
        value="",
        placeholder="e.g. 15 years",
        key=f"timeline_new_value_{client_id}_{version}",
        label_visibility="collapsed",
    )
    with add_cols[2]:
        add_clicked = st.button("Add", key=f"timeline_add_{client_id}_{version}")

    if add_clicked:
        if not new_label.strip() or not new_horizon.strip():
            st.warning("Add both goal/need and time horizon.")
        else:
            updated_time_horizon[normalise_time_horizon_key(new_label)] = new_horizon.strip()
            profile["time_horizon"] = updated_time_horizon
            st.session_state.profile_editor_version += 1
            st.rerun()
    else:
        profile["time_horizon"] = updated_time_horizon


def render_sidebar() -> None:
    st.sidebar.title("Advisor Workspace")

    st.sidebar.subheader("Clients")
    selected_client_id = st.session_state.selected_client_id
    reviewed_client_ids = [
        client_id
        for client_id, record in st.session_state.clients.items()
        if record.get("kyc_reviewed", False)
    ]
    reviewed_selectors = ",\n".join(
        f".st-key-select_{client_id} button::after"
        for client_id in reviewed_client_ids
    )
    reviewed_rule = (
        f"""
        {reviewed_selectors} {{
            content: "\\2713";
            display: inline-grid;
            flex: 0 0 1.2rem;
            width: 1.2rem;
            height: 1.2rem;
            margin-left: auto;
            place-items: center;
            border-radius: 999px;
            background: #dcf7ef;
            color: #137d69;
            font-size: 0.75rem;
            font-weight: 800;
            line-height: 1;
        }}
        """
        if reviewed_selectors
        else ""
    )
    selected_rule = (
        f"""
        .st-key-select_{selected_client_id} button {{
            border-color: rgba(36, 107, 131, 0.3) !important;
            background: var(--mili-selected) !important;
            color: var(--mili-navy) !important;
            box-shadow: inset 3px 0 0 var(--mili-blue) !important;
        }}
        .st-key-select_{selected_client_id} button p {{
            color: var(--mili-navy) !important;
            font-weight: 750 !important;
        }}
        """
        if selected_client_id
        else ""
    )
    st.sidebar.html(
        f"""
        <style>
        {reviewed_rule}
        {selected_rule}
        </style>
        """,
    )

    for client_id, record in st.session_state.clients.items():
        name = record["profile"].get("name") or "Unnamed client"
        label = f"{'▸ ' if client_id == st.session_state.selected_client_id else ''}{name}"
        if st.sidebar.button(label, key=f"select_{client_id}", use_container_width=True):
            if st.session_state.selected_client_id != client_id:
                st.session_state.selected_client_id = client_id
                st.session_state.last_unnamed_client_id = None
                st.rerun()

    if selected_client_id:
        selected_profile = st.session_state.clients[selected_client_id]["profile"]
        selected_name = selected_profile.get("name") or "Unnamed client"
        if st.sidebar.button(
            "Remove selected client",
            key="remove_selected_client",
            use_container_width=True,
        ):
            st.session_state.pending_client_removal = selected_client_id
            st.rerun()
    else:
        st.sidebar.caption("No clients yet.")

    pending_client_id = st.session_state.pending_client_removal
    if pending_client_id:
        pending_profile = st.session_state.clients[pending_client_id]["profile"]
        pending_name = pending_profile.get("name") or "Unnamed client"
        render_remove_client_dialog(pending_client_id, pending_name)

    st.sidebar.divider()
    with st.sidebar.container(key="new_client_panel"):
        st.subheader("Add new client")

        # Dynamic key ensures this input is cleared after client creation.
        new_client_key = f"new_client_name_{st.session_state.new_client_input_version}"
        new_name = st.text_input(
            "Client name",
            key=new_client_key,
            placeholder="Enter client name",
        )

        if st.button(
            "+ Create client",
            key="create_client",
            type="primary",
            use_container_width=True,
        ):
            clean_name = (new_name or "").strip()
            is_repeated_unnamed_creation = (
                not clean_name
                and st.session_state.last_unnamed_client_id
                == st.session_state.selected_client_id
                and is_untouched_unnamed_client(
                    st.session_state.selected_client_id
                )
            )
            if is_repeated_unnamed_creation:
                return

            client_id = f"client_{uuid.uuid4().hex[:8]}"
            st.session_state.clients[client_id] = {
                "client_id": client_id,
                "profile": new_empty_profile(client_id, clean_name),
                "documents": [],
                "kyc_reviewed": False,
            }
            st.session_state.selected_client_id = client_id
            st.session_state.last_unnamed_client_id = (
                client_id if not clean_name else None
            )
            st.session_state.new_client_input_version += 1
            st.toast("New client created")
            st.rerun()


def render_profile_editor(client_id: str, client: Dict[str, Any]) -> None:
    profile = client["profile"]
    version = st.session_state.profile_editor_version
    is_reviewed = bool(client.get("kyc_reviewed", False))

    title_col, review_col = st.columns([4, 1], vertical_alignment="center")
    with title_col:
        st.subheader("KYC Profile", anchor=False)
    with review_col:
        status_label = "Review complete" if is_reviewed else "Review incomplete"
        status_class = "complete" if is_reviewed else "incomplete"
        st.markdown(
            f'<div class="kyc-review-status {status_class}">{status_label}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        """
        <style>
        .kyc-review-status {
            width: fit-content;
            margin-left: auto;
            padding: 0.22rem 0.65rem;
            border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            line-height: 1.25rem;
            white-space: nowrap;
        }
        .kyc-review-status.complete {
            border-color: color-mix(in srgb, #16a34a 35%, transparent);
            background: color-mix(in srgb, #16a34a 12%, transparent);
            color: #15803d;
        }
        .kyc-review-status.incomplete {
            opacity: 0.68;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key=f"profile_completion_{client_id}"):
        score_placeholder = st.empty()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        profile["name"] = st.text_input(
            "Name",
            value=profile.get("name") or "",
            key=f"name_{client_id}_{version}",
        ) or None
    with c2:
        stored_date_of_birth = profile.get("date_of_birth")
        try:
            date_of_birth_value = date.fromisoformat(stored_date_of_birth) if stored_date_of_birth else None
        except (TypeError, ValueError):
            date_of_birth_value = None

        selected_date_of_birth = st.date_input(
            "Date of birth",
            value=date_of_birth_value,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            key=f"date_of_birth_{client_id}_{version}",
            format="DD/MM/YYYY",
        )
        profile["date_of_birth"] = selected_date_of_birth.isoformat() if selected_date_of_birth else None
        profile["age"] = calculate_age(profile["date_of_birth"]) if profile["date_of_birth"] else None
        clear_date_of_birth = st.button(
            "Clear",
            key=f"clear_date_of_birth_{client_id}_{version}",
            disabled=selected_date_of_birth is None,
            help="Clear date of birth",
        )
        if clear_date_of_birth:
            profile["date_of_birth"] = None
            profile["age"] = None
            st.session_state.profile_editor_version += 1
            st.rerun()

        date_input_key = f"date_of_birth_{client_id}_{version}"
        age_label = f"Age: {profile['age']}" if profile["age"] is not None else ""
        st.markdown(
            f"""
            <style>
            [data-testid="stColumn"]:has(.st-key-clear_date_of_birth_{client_id}_{version}) {{
                position: relative;
            }}
            .st-key-clear_date_of_birth_{client_id}_{version} {{
                position: absolute;
                right: 0;
                top: 0;
                z-index: 3;
            }}
            .st-key-clear_date_of_birth_{client_id}_{version} button {{
                min-height: 1.25rem;
                height: 1.25rem;
                padding: 0 0.3rem;
                border: 0;
                background: transparent;
                color: inherit;
                opacity: 0.6;
                font-size: 0.7rem;
                line-height: 1rem;
            }}
            .st-key-clear_date_of_birth_{client_id}_{version} button:disabled {{
                visibility: hidden;
            }}
            .st-key-{date_input_key} [data-baseweb="input"] {{
                position: relative;
            }}
            .st-key-{date_input_key} [data-baseweb="input"] svg {{
                display: none;
            }}
            .st-key-{date_input_key} [data-baseweb="input"] input {{
                padding-right: 6.5rem;
            }}
            .st-key-{date_input_key} [data-baseweb="input"]::after {{
                content: "{age_label}";
                position: absolute;
                right: 5%;
                top: 50%;
                transform: translateY(-50%);
                color: inherit;
                opacity: 0.6;
                font-family: inherit;
                font-size: 0.875rem;
                line-height: 1.25rem;
                white-space: nowrap;
                pointer-events: none;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        profile["occupation"] = st.text_input(
            "Occupation",
            value=profile.get("occupation") or "",
            key=f"occupation_{client_id}_{version}",
        ) or None
    with c4:
        current_marital_status = (profile.get("marital_status") or "").strip()
        marital_status_options = [""] + MARITAL_STATUS_OPTIONS
        if current_marital_status and current_marital_status not in marital_status_options:
            marital_status_options.append(current_marital_status)

        profile["marital_status"] = st.selectbox(
            "Marital status",
            marital_status_options,
            index=marital_status_options.index(current_marital_status),
            key=f"marital_status_{client_id}_{version}",
            format_func=lambda option: option or "Select marital status",
        ) or None

    with st.container(key=f"identity_details_{client_id}_{version}"):
        gender_col, pronouns_col = st.columns(2)
        current_gender = (profile.get("gender") or "").strip()
        gender_options = [""] + GENDER_OPTIONS
        if current_gender and current_gender not in gender_options:
            gender_options.append(current_gender)

        profile["gender"] = gender_col.selectbox(
            "Gender",
            gender_options,
            index=gender_options.index(current_gender),
            key=f"gender_{client_id}_{version}",
            format_func=lambda option: option or "Gender",
            label_visibility="collapsed",
        ) or None
        profile["pronouns"] = pronouns_col.text_input(
            "Pronouns",
            value=profile.get("pronouns") or "",
            key=f"pronouns_{client_id}_{version}",
            placeholder="Pronouns",
            label_visibility="collapsed",
        ) or None
        gender_label = str(profile["gender"] or "Gender")
        gender_label = (
            gender_label.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("<", "\\3c ")
            .replace("\r", " ")
            .replace("\n", " ")
        )
        st.markdown(
            f"""
            <style>
            .st-key-gender_{client_id}_{version} [data-baseweb="select"] > div {{
                position: relative;
            }}
            .st-key-gender_{client_id}_{version}
            [data-baseweb="select"] > div > div:first-child {{
                opacity: 0;
            }}
            .st-key-gender_{client_id}_{version} [data-baseweb="select"] > div::before {{
                content: "{gender_label}";
                position: absolute;
                left: 0.5rem;
                right: 1.5rem;
                top: 50%;
                transform: translateY(-50%);
                z-index: 2;
                overflow: hidden;
                color: var(--text-color, CanvasText);
                font-size: 0.7rem;
                line-height: 1.25rem;
                text-overflow: ellipsis;
                white-space: nowrap;
                pointer-events: none;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    c4, c5 = st.columns(2)
    with c4:
        profile["income"] = st.text_input(
            "Income",
            value=profile.get("income") or "",
            key=f"income_{client_id}_{version}",
        ) or None
    with c5:
        rt = profile.get("risk_tolerance", {}) or {}
        confidence_options = ["unknown", "low", "medium", "high"]
        current_confidence = rt.get("confidence", "unknown")
        with st.container(key=f"risk_tolerance_control_{client_id}_{version}"):
            rt_value = st.text_input(
                "Risk tolerance",
                value=rt.get("value") or "",
                key=f"risk_value_{client_id}_{version}",
            ) or None
            rt_conf = st.selectbox(
                "Risk confidence",
                confidence_options,
                index=confidence_options.index(current_confidence) if current_confidence in confidence_options else 0,
                key=f"risk_confidence_{client_id}_{version}",
                format_func=lambda option: option.title(),
                label_visibility="collapsed",
                help="Confidence in the recorded risk tolerance",
                accept_new_options=False,
            )
        profile["risk_tolerance"] = {
            "value": rt_value,
            "confidence": rt_conf,
            "evidence": rt.get("evidence"),
        }

    with st.expander("Goals and planning details", expanded=True):
        left, right = st.columns(2)
        with left:
            profile["goals"] = text_to_list(st.text_area(
                "Goals",
                value=list_to_text(profile.get("goals", [])),
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"goals_{client_id}_{version}",
            ))
            profile["liquidity_needs"] = text_to_list(st.text_area(
                "Liquidity needs",
                value=list_to_text(profile.get("liquidity_needs", [])),
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"liquidity_{client_id}_{version}",
            ))
            profile["dependents"] = text_to_list(st.text_area(
                "Dependents",
                value=list_to_text(profile.get("dependents", []), "dependents"),
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"dependents_{client_id}_{version}",
            ))
        with right:
            profile["assets"] = text_to_list(st.text_area(
                "Assets",
                value=list_to_text(profile.get("assets", [])),
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"assets_{client_id}_{version}",
            ))
            profile["liabilities"] = text_to_list(st.text_area(
                "Liabilities",
                value=list_to_text(profile.get("liabilities", [])),
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"liabilities_{client_id}_{version}",
            ))
        render_time_horizon_editor(profile, client_id, version)

    with st.expander("Review flags", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Missing information**")
            profile["missing_information"] = text_to_list(st.text_area(
                "Missing info",
                value=list_to_text(profile.get("missing_information", [])),
                label_visibility="collapsed",
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"missing_{client_id}_{version}",
            ))
            st.markdown("**Contradictions**")
            profile["contradictions"] = text_to_list(st.text_area(
                "Contradictions",
                value=list_to_text(profile.get("contradictions", [])),
                label_visibility="collapsed",
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"contradictions_{client_id}_{version}",
            ))
        with col2:
            st.markdown("**Follow-up questions**")
            profile["follow_up_questions"] = text_to_list(st.text_area(
                "Follow-up questions",
                value=list_to_text(profile.get("follow_up_questions", [])),
                label_visibility="collapsed",
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"followups_{client_id}_{version}",
            ))
            st.markdown("**Confidence notes**")
            profile["confidence_notes"] = text_to_list(st.text_area(
                "Confidence notes",
                value=list_to_text(profile.get("confidence_notes", [])),
                label_visibility="collapsed",
                height=PROFILE_TEXT_AREA_HEIGHT,
                key=f"confidence_notes_{client_id}_{version}",
            ))

    st.divider()
    review_note_col, review_action_col = st.columns([3, 1], vertical_alignment="center")
    with review_note_col:
        st.caption(
            "KYC review is complete." if is_reviewed
            else "Confirm once all profile details and review flags have been checked."
        )
    with review_action_col:
        action_label = "Reopen review" if is_reviewed else "Mark review complete"
        action_key = (
            f"reopen_kyc_review_{client_id}"
            if is_reviewed
            else f"complete_kyc_review_{client_id}"
        )
        if st.button(
            action_label,
            key=action_key,
            type="secondary" if is_reviewed else "primary",
            use_container_width=True,
        ):
            st.session_state.clients[client_id]["kyc_reviewed"] = not is_reviewed
            toast_message = (
                "KYC review reopened"
                if is_reviewed
                else "KYC review marked complete"
            )
            st.toast(toast_message)
            st.rerun()

    score = calculate_profile_completion(profile)
    profile["completion_score"] = score
    score_placeholder.progress(
        score / 100,
        text=f"Profile completion: {score}%",
    )
    if score == 100:
        st.markdown(
            f"""
            <style>
            .st-key-profile_completion_{client_id}
            [data-baseweb="progress-bar"] > div > div > div {{
                background-color: #16a34a !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )


@st.dialog("Add document")
def render_add_document_dialog(client: Dict[str, Any]) -> None:
    input_version = st.session_state.document_input_version
    sample_key = f"sample_choice_{input_version}"
    with st.container(key="document_dialog_header"):
        title_col, sample_col = st.columns(2, vertical_alignment="bottom")
        with title_col:
            doc_title = st.text_input(
                "Document title",
                value="Onboarding notes",
                key=f"new_doc_title_{input_version}",
            )
        with sample_col:
            sample_choice = st.selectbox(
                "Sample data",
                [
                    "None",
                    "Contradictory sample - Priya",
                    "Incomplete sample - Kabir",
                    "Discovery call - Priya",
                    "Follow up - Priya",
                ],
                key=sample_key,
                on_change=clear_document_upload_for_sample,
                args=(sample_key,),
            )

    default_text = ""
    if sample_choice == "Contradictory sample - Priya":
        default_text = NEW_CLIENT_SAMPLE
    elif sample_choice == "Incomplete sample - Kabir":
        default_text = INCOMPLETE_SAMPLE
    elif sample_choice == "Discovery call - Priya":
        default_text = PRIYA_DISCOVERY_CALL_SAMPLE
    elif sample_choice == "Follow up - Priya":
        default_text = PRIYA_FOLLOW_UP_SAMPLE

    uploaded_file = st.file_uploader(
        "Upload .txt file",
        type=["txt"],
        key=f"upload_file_{input_version}_{st.session_state.document_upload_version}",
    )
    uploaded_text = ""
    upload_token = "no_upload"
    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        uploaded_text = decode_text_upload(uploaded_bytes)
        upload_token = hashlib.sha256(uploaded_bytes).hexdigest()[:12]
        st.caption(f"Loaded {uploaded_file.name}: {len(uploaded_text):,} characters")

    doc_text = st.text_area(
        "Paste or edit document text",
        value=uploaded_text or default_text,
        height=180,
        key=f"new_doc_text_{input_version}_{sample_choice}_{upload_token}",
    )

    if st.button("Add document to client", type="primary", key=f"add_doc_{input_version}"):
        if not doc_text.strip():
            st.warning("Add some document text first.")
        else:
            client["documents"].append({
                "doc_id": f"doc_{uuid.uuid4().hex[:8]}",
                "title": (doc_title or "Untitled document").strip(),
                "text": doc_text.strip(),
                "active": True,
            })
            st.session_state.document_input_version += 1
            st.toast("Document added")
            st.rerun()


def render_documents(client: Dict[str, Any]) -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.subheader("Documents", anchor=False, width="content")
        if st.button(r"\+", key="open_add_document", help="Add document", type="primary"):
            render_add_document_dialog(client)

    st.caption("Removing a document does not delete fields that were already extracted or advisor-reviewed.")

    docs = client["documents"]
    if not docs:
        st.info("No documents added yet. Click + to add onboarding information.")

    remove_doc_id = None
    for doc in docs:
        expanded_key = f"document_expanded_{doc['doc_id']}"
        if expanded_key not in st.session_state:
            st.session_state[expanded_key] = False

        with st.container(border=True, key=f"document_card_{doc['doc_id']}"):
            with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                doc["title"] = st.text_input(
                    "Document title",
                    value=doc["title"],
                    key=f"title_{doc['doc_id']}",
                    label_visibility="collapsed",
                )
                doc["active"] = st.checkbox(
                    "Active",
                    value=doc.get("active", True),
                    key=f"active_{doc['doc_id']}",
                )
                if st.button("Remove", key=f"remove_{doc['doc_id']}"):
                    remove_doc_id = doc["doc_id"]

            is_expanded = st.session_state[expanded_key]
            if st.button(
                "Document contents",
                key=f"toggle_contents_{doc['doc_id']}",
                icon=":material/keyboard_arrow_up:" if is_expanded else ":material/keyboard_arrow_down:",
                type="tertiary",
            ):
                is_expanded = not is_expanded
                st.session_state[expanded_key] = is_expanded

            if is_expanded:
                doc["text"] = st.text_area(
                    "Document text",
                    value=doc["text"],
                    height=180,
                    key=f"text_{doc['doc_id']}",
                    label_visibility="collapsed",
                )

    if remove_doc_id:
        client["documents"] = [d for d in docs if d["doc_id"] != remove_doc_id]
        st.toast("Document removed. Existing KYC fields were retained.")
        st.rerun()


def render_agent_actions(client_id: str, client: Dict[str, Any]) -> None:
    active_docs = [d for d in client["documents"] if d.get("active", True)]
    combined_text = "\n\n".join([f"## {d['title']}\n{d['text']}" for d in active_docs])

    st.subheader("Agent run", anchor=False)
    st.caption(
        "With an API key, GPT drafts the profile, validation, and follow-up questions; the tools only clean and normalise those drafts. Local rules are fallback only."
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        run_clicked = st.button("Run KYC Agent", type="primary", use_container_width=True)
    with col2:
        st.write(f"Active documents included: **{len(active_docs)}**")
        st.caption(f"Text sent to agent: {len(combined_text)} characters")

    if run_clicked:
        if not combined_text.strip():
            st.warning("Add or activate at least one document before running the agent.")
            return

        with st.spinner("Running KYC agent..."):
            try:
                result = run_kyc_agent(
                    raw_text=combined_text,
                    client_id=client_id,
                    existing_profile=client["profile"],
                )

                if isinstance(result, dict) and "profile" in result:
                    extracted_profile = result.get("profile", {})
                    last_run = result
                else:
                    extracted_profile = result if isinstance(result, dict) else {}
                    last_run = {
                        "mode": "profile_direct",
                        "tool_trace": [
                            "extract_kyc_profile",
                            "validate_kyc_completeness",
                            "generate_follow_up_questions",
                        ],
                        "profile": extracted_profile,
                    }

                if not extracted_profile:
                    st.error("Agent returned no profile data. Check agent.py output.")
                    return

                updated_profile = merge_profile(client["profile"], extracted_profile)
                client["profile"] = updated_profile
                st.session_state.clients[client_id] = client
                st.session_state.last_agent_run = last_run
                st.session_state.profile_editor_version += 1
                st.session_state.next_main_tab = PROFILE_TAB

                st.success("KYC profile updated")
                st.rerun()

            except TypeError:
                result = run_kyc_agent(combined_text, client_id)

                if isinstance(result, dict) and "profile" in result:
                    extracted_profile = result.get("profile", {})
                    last_run = result
                else:
                    extracted_profile = result if isinstance(result, dict) else {}
                    last_run = {
                        "mode": "profile_direct",
                        "tool_trace": [
                            "extract_kyc_profile",
                            "validate_kyc_completeness",
                            "generate_follow_up_questions",
                        ],
                        "profile": extracted_profile,
                    }

                updated_profile = merge_profile(client["profile"], extracted_profile)
                client["profile"] = updated_profile
                st.session_state.clients[client_id] = client
                st.session_state.last_agent_run = last_run
                st.session_state.profile_editor_version += 1
                st.session_state.next_main_tab = PROFILE_TAB

                st.success("KYC profile updated")
                st.rerun()

            except Exception as exc:
                st.error(f"Agent failed: {exc}")

    if st.session_state.last_agent_run:
        result = st.session_state.last_agent_run
        mode = result.get("mode", "profile_direct")
        trace = result.get("tool_trace", [])
        trace_names = [
            step.get("name", "Unnamed step") if isinstance(step, dict) else str(step)
            for step in trace
        ]
        st.caption(f"Mode: {mode} | Trace: {' -> '.join(trace_names) if trace_names else 'N/A'}")
        if trace:
            with st.expander("Tool-call trace", expanded=False):
                for index, step in enumerate(trace, start=1):
                    if isinstance(step, dict):
                        name = step.get("name", "Unnamed step")
                        detail = step.get("detail", "")
                    else:
                        name = str(step)
                        detail = ""
                    st.markdown(f"{index}. `{name}`" + (f" - {detail}" if detail else ""))
        if result.get("error"):
            st.warning(f"SDK fallback used because: {result['error']}")

def main() -> None:
    init_state()
    render_sidebar()

    client_id = st.session_state.selected_client_id
    if client_id is None:
        st.markdown('<p class="mili-eyebrow">Advisor operations</p>', unsafe_allow_html=True)
        st.title("Client Onboarding & KYC Agent")
        st.info("No clients in the workspace. Add a new client from the sidebar to begin.")
        return

    client = st.session_state.clients[client_id]
    profile = client["profile"]

    st.markdown('<p class="mili-eyebrow">Advisor operations</p>', unsafe_allow_html=True)
    st.title("Client Onboarding & KYC Agent")
    st.caption("A prototype workspace for wealth advisors to manage onboarding documents and convert them into a structured, reviewable KYC profile.")

    st.markdown(
        """
        <style>
        /* Match the document add control to the primary action while keeping it square. */
        .st-key-open_add_document button {
            width: 2rem;
            min-width: 2rem;
            height: 2rem;
            min-height: 2rem;
            padding: 0;
        }

        /* Keep risk confidence compact and inset into the risk tolerance field. */
        [class*="st-key-risk_tolerance_control_"] {
            position: relative;
        }
        [class*="st-key-risk_tolerance_control_"] .stTextInput input {
            padding-right: 7.25rem;
        }
        [class*="st-key-risk_tolerance_control_"] [data-testid="stElementContainer"]:has(> .stSelectbox) {
            position: absolute;
            right: 0.25rem;
            bottom: 0.25rem;
            width: 6.75rem;
            z-index: 1;
        }
        [class*="st-key-risk_tolerance_control_"] .stSelectbox [data-baseweb="select"] > div {
            min-height: 2rem;
            height: 2rem;
        }
        [class*="st-key-risk_tolerance_control_"] .stSelectbox [data-baseweb="select"] * {
            font-size: 0.72rem;
        }
        [class*="st-key-risk_tolerance_control_"]
        .stSelectbox [data-baseweb="select"] > div > div:first-child > div:first-child {
            transform: translateX(0.25rem);
        }
        [class*="st-key-risk_tolerance_control_"] .stSelectbox input {
            caret-color: transparent;
        }
        [data-testid="stSelectboxVirtualDropdown"][data-risk-confidence-menu="true"]::before {
            content: "Confidence";
            display: block;
            padding: 0.4rem 0.75rem 0.2rem;
            color: var(--text-color);
            opacity: 0.65;
            font-size: 0.68rem;
            font-style: italic;
            line-height: 1rem;
        }
        [data-testid="stSelectboxVirtualDropdown"][data-risk-confidence-menu="true"] [role="option"],
        [data-testid="stSelectboxVirtualDropdown"][data-risk-confidence-menu="true"] [role="option"] * {
            font-size: 0.72rem;
        }
        [data-testid="stSelectboxVirtualDropdown"][data-gender-menu="true"] [role="option"],
        [data-testid="stSelectboxVirtualDropdown"][data-gender-menu="true"] [role="option"] * {
            font-size: 0.7rem;
        }

        /* Fit gender and pronouns into the existing gap below Name. */
        [class*="st-key-identity_details_"] {
            width: calc((100% - 3rem) / 4);
            margin-top: -1.35rem;
            margin-bottom: -0.9rem;
            position: relative;
            z-index: 2;
        }
        [class*="st-key-identity_details_"] [data-testid="stHorizontalBlock"] {
            gap: 0.35rem;
        }
        [class*="st-key-identity_details_"] [data-testid="stColumn"] {
            width: calc((100% - 0.35rem) / 2);
            min-width: 0;
            flex: 0 0 calc((100% - 0.35rem) / 2);
        }
        [class*="st-key-identity_details_"] [data-baseweb="select"],
        [class*="st-key-identity_details_"] [data-baseweb="input"] {
            width: 100%;
            min-height: 1.75rem;
            height: 1.75rem;
            box-sizing: border-box;
            background-color: transparent !important;
        }
        [class*="st-key-identity_details_"] .stSelectbox [data-baseweb="select"] > div,
        [class*="st-key-identity_details_"] .stTextInput [data-baseweb="input"],
        [class*="st-key-identity_details_"] .stTextInput [data-baseweb="input"] > div,
        [class*="st-key-identity_details_"] .stTextInput input {
            background-color: transparent !important;
        }
        [class*="st-key-identity_details_"] [data-baseweb="select"] > div,
        [class*="st-key-identity_details_"] input {
            min-height: 1.75rem;
            height: 1.75rem;
            box-sizing: border-box;
            background-color: transparent !important;
            font-size: 0.7rem;
            line-height: 1.25rem;
        }
        [class*="st-key-identity_details_"] [data-baseweb="select"] * {
            font-size: 0.7rem;
            line-height: 1.25rem;
        }
        [class*="st-key-identity_details_"]
        [data-baseweb="select"] > div > div:first-child {
            height: 100%;
            display: flex;
            align-items: center;
            color: var(--text-color, CanvasText) !important;
            overflow: visible;
        }
        [class*="st-key-identity_details_"]
        [data-baseweb="select"] > div > div:first-child > div:first-child {
            display: block !important;
            color: var(--text-color, CanvasText) !important;
            opacity: 1 !important;
            visibility: visible !important;
            white-space: nowrap;
        }
        [class*="st-key-identity_details_"] .stSelectbox input {
            color: var(--text-color, CanvasText) !important;
            -webkit-text-fill-color: var(--text-color, CanvasText) !important;
            opacity: 1 !important;
        }
        [class*="st-key-identity_details_"] .stSelectbox,
        [class*="st-key-identity_details_"] .stTextInput {
            margin: 0;
        }
        @media (max-width: 640px) {
            [class*="st-key-identity_details_"] {
                width: 100%;
                margin-top: 0;
                margin-bottom: 0;
            }
            [class*="st-key-identity_details_"] [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap;
                width: 100%;
            }
            [class*="st-key-identity_details_"] [data-testid="stColumn"] {
                width: calc((100% - 0.35rem) / 2);
                min-width: 0;
                flex: 1 1 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    disable_risk_confidence_typing()
    default_tab = st.session_state.pop("next_main_tab", None)
    tab1, tab2, tab3 = st.tabs(
        [PROFILE_TAB, DOCUMENTS_TAB, JSON_TAB],
        default=default_tab,
    )
    if default_tab:
        select_main_tab_in_browser(default_tab)

    with tab1:
        render_profile_editor(client_id, client)

    with tab2:
        render_documents(client)
        st.divider()
        render_agent_actions(client_id, client)

    with tab3:
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.subheader("Structured client record", anchor=False, width="content")
            st.download_button(
                "Download JSON",
                data=json.dumps(client, indent=2),
                file_name=f"{profile.get('name') or client_id}_kyc_profile.json".replace(" ", "_"),
                mime="application/json",
                key="download_client_json",
                type="tertiary",
                icon=":material/download:",
                on_click="ignore",
            )
        st.json(client)

    st.divider()
    st.caption("Advisor remains responsible for reviewing extracted fields, confirming uncertain information, and making any KYC or suitability decision.")


if __name__ == "__main__":
    main()
