from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from typing import Any, Dict, List

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
from tools import calculate_age, merge_kyc_profiles

# st.set_page_config(page_title="Mili KYC Agent", page_icon="🧾", layout="wide")
APP_TITLE = "Mili KYC Agent"

st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="wide")

st.markdown(
    f"""
    <style>
    [data-testid="stHeader"] [data-testid="stToolbar"] > div > div:first-child::after {{
        content: "{APP_TITLE}";
        margin-left: 60%;
        font-size: 1.125rem;
        font-weight: 600;
        white-space: nowrap;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


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
    if "selected_client_id" not in st.session_state:
        st.session_state.selected_client_id = next(iter(st.session_state.clients.keys()))
    if "last_agent_run" not in st.session_state:
        st.session_state.last_agent_run = None
    # These counters are used to reset Streamlit input widgets after submit.
    if "new_client_input_version" not in st.session_state:
        st.session_state.new_client_input_version = 0
    if "document_input_version" not in st.session_state:
        st.session_state.document_input_version = 0
    if "profile_editor_version" not in st.session_state:
        st.session_state.profile_editor_version = 0


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


def merge_profile(existing: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Merge agent output without deleting advisor-confirmed fields when new data is incomplete."""
    return merge_kyc_profiles(existing, extracted)


def list_to_text(items: List[str]) -> str:
    return "\n".join(items or [])


def text_to_list(value: str) -> List[str]:
    return [line.strip(" -•\t") for line in value.splitlines() if line.strip(" -•\t")]


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


def render_time_horizon_editor(profile: Dict[str, Any], client_id: str, version: int) -> None:
    """
    Render time_horizon as clean editable rows instead of raw JSON.

    The underlying profile still stores time_horizon as a dictionary so the JSON
    output remains structured, but advisors do not need to edit raw JSON.
    """
    st.markdown("**Goal timelines**")
    # st.caption("Each row links a goal or liquidity need to the relevant time horizon.")

    raw_time_horizon = profile.get("time_horizon", {}) or {}
    if not isinstance(raw_time_horizon, dict):
        raw_time_horizon = {}

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
    reviewed_client_ids = [
        client_id
        for client_id, record in st.session_state.clients.items()
        if record.get("kyc_reviewed", False)
    ]
    if reviewed_client_ids:
        reviewed_selectors = ",\n".join(
            f".st-key-select_{client_id} button, .st-key-select_{client_id} button p"
            for client_id in reviewed_client_ids
        )
        st.sidebar.html(
            f"""
            <style>
            {reviewed_selectors} {{
                color: #16a34a !important;
                border-color: rgba(34, 197, 94, 0.55) !important;
            }}
            </style>
            """,
        )

    for client_id, record in st.session_state.clients.items():
        name = record["profile"].get("name") or "Unnamed client"
        label = f"{'▸ ' if client_id == st.session_state.selected_client_id else ''}{name}"
        if st.sidebar.button(label, key=f"select_{client_id}", use_container_width=True):
            if st.session_state.selected_client_id != client_id:
                st.session_state.selected_client_id = client_id
                st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Add new client")

    # Dynamic key ensures this input is cleared after client creation.
    new_client_key = f"new_client_name_{st.session_state.new_client_input_version}"
    new_name = st.sidebar.text_input("Client name", key=new_client_key)

    if st.sidebar.button("+ Create client", use_container_width=True):
        clean_name = (new_name or "").strip()
        client_id = f"client_{uuid.uuid4().hex[:8]}"
        st.session_state.clients[client_id] = {
            "client_id": client_id,
            "profile": new_empty_profile(client_id, clean_name),
            "documents": [],
            "kyc_reviewed": False,
        }
        st.session_state.selected_client_id = client_id
        st.session_state.new_client_input_version += 1
        st.toast("New client created")
        st.rerun()


def update_kyc_review_status(client_id: str, widget_key: str) -> None:
    """Persist review status before Streamlit redraws the sidebar."""
    st.session_state.clients[client_id]["kyc_reviewed"] = bool(st.session_state[widget_key])


def render_profile_editor(client_id: str, client: Dict[str, Any]) -> None:
    profile = client["profile"]
    score = profile.get("completion_score", 0)
    version = st.session_state.profile_editor_version

    title_col, review_col = st.columns([4, 1])
    with title_col:
        st.subheader("KYC Profile")
    with review_col:
        review_key = f"kyc_reviewed_{client_id}"
        st.checkbox(
            "KYC review",
            value=bool(client.get("kyc_reviewed", False)),
            key=review_key,
            on_change=update_kyc_review_status,
            args=(client_id, review_key),
            help="Mark this client's KYC profile as reviewed by the advisor.",
        )
    st.progress(min(100, int(score)) / 100, text=f"Profile completion: {score}%")

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
                value=list_to_text(profile.get("dependents", [])),
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


def render_documents(client: Dict[str, Any]) -> None:
    st.subheader("Documents")
    st.caption("Removing a document does not delete fields that were already extracted or advisor-reviewed.")

    docs = client["documents"]
    if not docs:
        st.info("No documents added yet. Paste or upload onboarding information below.")

    remove_doc_id = None
    for doc in docs:
        with st.expander(f"{doc['title']} {'(inactive)' if not doc.get('active', True) else ''}", expanded=False):
            doc["title"] = st.text_input("Document title", value=doc["title"], key=f"title_{doc['doc_id']}")
            doc["text"] = st.text_area("Document text", value=doc["text"], height=180, key=f"text_{doc['doc_id']}")
            cols = st.columns([1, 1, 4])
            with cols[0]:
                doc["active"] = st.checkbox("Active", value=doc.get("active", True), key=f"active_{doc['doc_id']}")
            with cols[1]:
                if st.button("Remove", key=f"remove_{doc['doc_id']}"):
                    remove_doc_id = doc["doc_id"]

    if remove_doc_id:
        client["documents"] = [d for d in docs if d["doc_id"] != remove_doc_id]
        st.toast("Document removed. Existing KYC fields were retained.")
        st.rerun()

    with st.expander("+ Add document", expanded=True):
        input_version = st.session_state.document_input_version
        sample_choice = st.selectbox(
            "Use sample input",
            [
                "None",
                "Contradictory sample - Priya",
                "Incomplete sample - Kabir",
                "Discovery call - Priya",
                "Follow up - Priya",
            ],
            key=f"sample_choice_{input_version}",
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
            key=f"upload_file_{input_version}",
        )
        uploaded_text = ""
        upload_token = "no_upload"
        if uploaded_file is not None:
            uploaded_bytes = uploaded_file.getvalue()
            uploaded_text = decode_text_upload(uploaded_bytes)
            upload_token = hashlib.sha256(uploaded_bytes).hexdigest()[:12]
            st.caption(f"Loaded {uploaded_file.name}: {len(uploaded_text):,} characters")

        doc_title = st.text_input(
            "New document title",
            value="Onboarding notes",
            key=f"new_doc_title_{input_version}",
        )
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


def render_agent_actions(client_id: str, client: Dict[str, Any]) -> None:
    active_docs = [d for d in client["documents"] if d.get("active", True)]
    combined_text = "\n\n".join([f"## {d['title']}\n{d['text']}" for d in active_docs])

    st.subheader("Agent run")
    st.caption("The agent extracts KYC fields, validates completeness, and generates advisor follow-up questions.")

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

                st.success("KYC profile updated")
                st.rerun()

            except Exception as exc:
                st.error(f"Agent failed: {exc}")

    if st.session_state.last_agent_run:
        result = st.session_state.last_agent_run
        mode = result.get("mode", "profile_direct")
        tools = result.get("tool_trace", [])
        st.caption(f"Mode: {mode} | Tools: {', '.join(tools) if tools else 'N/A'}")
        if result.get("error"):
            st.warning(f"SDK fallback used because: {result['error']}")

def main() -> None:
    init_state()
    render_sidebar()

    client_id = st.session_state.selected_client_id
    client = st.session_state.clients[client_id]
    profile = client["profile"]

    st.title("Client Onboarding & KYC Agent")
    st.caption("A prototype workspace for wealth advisors to manage onboarding documents and convert them into a structured, reviewable KYC profile.")

    st.markdown(
        """
        <style>
        /* The tab list scrolls horizontally, so its row wrapper must be sticky. */
        [data-testid="stTabs"] div:has(> [data-baseweb="tab-list"]) {
            position: sticky;
            top: 3.75rem;
            z-index: 1000;
            isolation: isolate;
            background-color: Canvas;
            background-color: light-dark(#ffffff, #0e1117);
            box-shadow: 0 1px 0 color-mix(in srgb, CanvasText 18%, transparent),
                        0 4px 8px color-mix(in srgb, CanvasText 6%, transparent);
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
    tab1, tab2, tab3 = st.tabs(["Client profile", "Documents & agent", "Underlying JSON"])

    with tab1:
        render_profile_editor(client_id, client)

    with tab2:
        render_documents(client)
        st.divider()
        render_agent_actions(client_id, client)

    with tab3:
        st.subheader("Structured client record")
        st.json(client)
        st.download_button(
            "Download client JSON",
            data=json.dumps(client, indent=2),
            file_name=f"{profile.get('name') or client_id}_kyc_profile.json".replace(" ", "_"),
            mime="application/json",
        )

    st.divider()
    st.caption("Advisor remains responsible for reviewing extracted fields, confirming uncertain information, and making any KYC or suitability decision.")


if __name__ == "__main__":
    main()
