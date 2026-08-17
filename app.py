from __future__ import annotations

import html
import json
import os
from textwrap import dedent

import streamlit as st

from nightbounty.access import matches_owner_access_code, normalize_owner_access_code
from nightbounty.crypto import (
    decrypt_legacy_report,
    decrypt_report,
    encrypt_report,
    is_public_key_envelope,
    owner_key_id,
    owner_public_key_from_private_key,
    short_commitment,
)
from nightbounty.midnight import contract_label, get_deployment, lifecycle_chain_note
from nightbounty.store import (
    create_bounty,
    get_report,
    initialize,
    list_bounties,
    list_events,
    list_reports,
    metrics,
    reset_demo_data,
    submit_report,
    transition_report,
)

st.set_page_config(
    page_title="NightBounty — private responsible disclosure",
    page_icon="◒",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize()


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --night: #0a0d12;
    --panel: #111720;
    --panel-hi: #171f2b;
    --line: #293544;
    --paper: #f4f1e8;
    --muted: #9cacb9;
    --mint: #2de1c2;
    --amber: #f4bd57;
    --coral: #ff765c;
    --violet: #a88cff;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
.stApp {
    background: var(--night);
    color: var(--paper);
}
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    opacity: .28;
    background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
    background-size: 38px 38px;
    mask-image: linear-gradient(to bottom, black, transparent 72%);
}
section[data-testid="stSidebar"] {
    background: #0d1219;
    border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.35rem;
}
.block-container {
    max-width: 1280px;
    padding-top: 2.0rem;
    padding-bottom: 3.5rem;
}
h1, h2, h3, p { color: var(--paper); }
h1 { letter-spacing: -0.05em; }
h2 { letter-spacing: -0.035em; margin-top: .45rem; }
h3 { letter-spacing: -0.02em; }
[data-testid="stMarkdownContainer"] p { color: var(--muted); line-height: 1.55; }

.brand-kicker, .eyebrow, .mono, .status-line, .event-time {
    font-family: 'DM Mono', monospace;
    letter-spacing: .08em;
    text-transform: uppercase;
}
.brand-kicker { color: var(--mint); font-size: .72rem; }
.eyebrow { color: var(--mint); font-size: .72rem; margin-bottom: .65rem; }
.mono { color: var(--muted); font-size: .72rem; }

.hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(270px, .42fr);
    gap: 1.2rem;
    margin: .1rem 0 1.8rem;
}
.hero-main, .hero-side, .metric-card, .bounty-card, .event-card, .protocol-card {
    border: 1px solid var(--line);
    background: rgba(17, 23, 32, .94);
}
.hero-main { padding: 2.1rem 2.2rem 2rem; min-height: 282px; position: relative; overflow: hidden; }
.hero-main::after {
    content: "";
    width: 240px; height: 240px;
    position: absolute; right: -90px; bottom: -130px;
    border: 1px solid rgba(45,225,194,.5); border-radius: 50%;
    box-shadow: 0 0 0 42px rgba(45,225,194,.07), 0 0 0 84px rgba(45,225,194,.03);
}
.hero-main h1 { font-size: clamp(2.7rem, 5vw, 5rem); line-height: .9; margin: .1rem 0 1.15rem; max-width: 720px; position: relative; z-index: 1; }
.hero-main p { font-size: 1.08rem; max-width: 620px; position: relative; z-index: 1; }
.hero-side { padding: 1.45rem; display: flex; flex-direction: column; justify-content: space-between; min-height: 282px; }
.hero-side h3 { font-size: 1.25rem; margin: .4rem 0; }
.contract-address { font-family: 'DM Mono', monospace; font-size: .78rem; color: var(--paper); padding: .75rem 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); overflow-wrap: anywhere; }

.metric-card { padding: 1rem 1.05rem; min-height: 114px; }
.metric-value { color: var(--paper); font-size: 2rem; font-weight: 700; letter-spacing: -.06em; margin: .3rem 0; }
.metric-label { color: var(--muted); font-size: .82rem; }

.bounty-card { padding: 1.45rem; margin: .75rem 0 1.2rem; position: relative; }
.bounty-card h3 { font-size: 1.38rem; margin: .25rem 0 .4rem; }
.bounty-card p { max-width: 800px; }
.bounty-meta { display: flex; flex-wrap: wrap; gap: .45rem; margin: 1rem 0 .8rem; }
.chip { border: 1px solid var(--line); color: var(--paper); padding: .26rem .52rem; font-family: 'DM Mono', monospace; font-size: .72rem; }
.chip.mint { border-color: rgba(45,225,194,.48); color: var(--mint); }
.chip.amber { border-color: rgba(244,189,87,.45); color: var(--amber); }
.chip.coral { border-color: rgba(255,118,92,.48); color: var(--coral); }
.chip.violet { border-color: rgba(168,140,255,.48); color: var(--violet); }

.event-card { padding: 1rem 1.1rem; border-left: 3px solid var(--mint); margin-bottom: .65rem; }
.event-card .event-title { color: var(--paper); font-weight: 600; margin: .22rem 0; }
.event-time { color: var(--muted); font-size: .67rem; }
.event-chain { color: var(--mint); font-family: 'DM Mono', monospace; font-size: .67rem; text-transform: uppercase; }

.protocol-card { padding: 1.25rem; min-height: 100%; }
.protocol-card h3 { margin-top: .15rem; }
.protocol-card strong { color: var(--paper); }

.stButton > button, .stFormSubmitButton > button {
    border-radius: 4px;
    border: 1px solid var(--mint);
    background: var(--mint);
    color: #08110f;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    padding: .55rem 1rem;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    border-color: var(--paper);
    color: #08110f;
    background: #7ef4df;
}
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {
    background: #0d131b !important;
    border-color: var(--line) !important;
    color: var(--paper) !important;
    border-radius: 4px !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label, .stCheckbox label {
    color: var(--paper) !important;
    font-size: .9rem !important;
}
[data-testid="stAlert"] { border-radius: 4px; }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 4px; background: var(--panel); }
hr { border-color: var(--line); }

@media (max-width: 850px) {
    .hero { grid-template-columns: 1fr; }
    .hero-main h1 { font-size: 3rem; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(value: object) -> str:
    return html.escape(str(value))


def status_chip(status: str) -> str:
    classes = {
        "OPEN": "mint",
        "REPORT_SUBMITTED": "amber",
        "ACCEPTED": "violet",
        "REJECTED": "coral",
        "PAID": "mint",
        "PREPROD_REQUIRED": "amber",
    }
    return f'<span class="chip {classes.get(status, "")}">{esc(status.replace("_", " "))}</span>'


def contract_panel() -> None:
    deployment = get_deployment()
    if deployment["is_deployed"]:
        status = "PREPROD VERIFIED"
        address = str(deployment["contract_address"])
        tx = str(deployment["deployment_transaction"])
        body = f"""
        <div class="hero-side">
            <div>
                <div class="eyebrow">MIDNIGHT NETWORK</div>
                {status_chip(status)}
                <h3>Private lifecycle active</h3>
                <p>Contract deployment evidence is configured locally. Private report content stays out of the public chain.</p>
            </div>
            <div>
                <div class="contract-address">{esc(address)}</div>
                <div class="mono" style="margin-top:.7rem">DEPLOY TX · {esc(tx)}</div>
            </div>
        </div>
        """
    else:
        body = """
        <div class="hero-side">
            <div>
                <div class="eyebrow">MIDNIGHT NETWORK</div>
                <span class="chip amber">PREPROD PACK READY</span>
                <h3>Deploy before judging</h3>
                <p>The Compact contract and PreProd configuration pack are included. This UI will not pretend local actions are public-chain transactions.</p>
            </div>
            <div>
                <div class="contract-address">midnight/contract/src/nightbounty.compact</div>
                <div class="mono" style="margin-top:.7rem">NEXT · COMPILE + DEPLOY TO PREPROD</div>
            </div>
        </div>
        """
    st.markdown(body, unsafe_allow_html=True)


def render_event(event: dict[str, str]) -> None:
    st.markdown(
        f"""
        <div class="event-card">
            <div class="event-time">{esc(event['created_at'])} · {esc(event['event_type'].replace('_', ' '))}</div>
            <div class="event-title">{esc(event['public_summary'])}</div>
            <div class="event-chain">{esc(event['chain_status'].replace('_', ' '))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bounty_label(bounty: dict[str, object]) -> str:
    return f"{bounty['id']} · {bounty['status']} · {bounty['title']}"


def render_bounty_card(bounty: dict[str, object], owner_encryption_key_id: str | None = None) -> None:
    encryption_chip = (
        f'<span class="chip violet">OWNER KEY · {esc(owner_encryption_key_id)}</span>'
        if owner_encryption_key_id
        else '<span class="chip amber">ENCRYPTION SETUP REQUIRED</span>'
    )
    st.markdown(
        f"""
        <div class="bounty-card">
            <div class="mono">{esc(bounty['id'])} · {esc(bounty['target_name'])}</div>
            <h3>{esc(bounty['title'])}</h3>
            <p>{esc(bounty['description'])}</p>
            <div class="bounty-meta">
                {status_chip(str(bounty['status']))}
                <span class="chip coral">{esc(bounty['severity'])}</span>
                <span class="chip mint">{esc(bounty['reward'])}</span>
                {encryption_chip}
            </div>
            <div class="mono">SCOPE · {esc(bounty['scope'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_command_room() -> None:
    bounties = list_bounties()
    owner_encryption = get_owner_encryption_profile()
    deployment = get_deployment()
    summary = metrics()

    main, side = st.columns([1.6, 0.7], gap="large")
    with main:
        st.markdown(
            """
            <div class="hero-main">
                <div class="eyebrow">PRIVATE RESPONSIBLE DISCLOSURE</div>
                <h1>Find bugs.<br>Keep the exploit dark.</h1>
                <p>NightBounty gives ethical researchers proof of first disclosure while project owners keep vulnerability details, identities, and shielded rewards out of public view.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with side:
        contract_panel()

    st.markdown("<div class='eyebrow'>LIVE WORKSPACE METRICS</div>", unsafe_allow_html=True)
    metric_columns = st.columns(4)
    metric_items = [
        (summary["open_bounties"], "active bounties"),
        (summary["private_reports"], "private reports"),
        (summary["resolved"], "owner decisions"),
        (summary["paid"], "shielded payouts"),
    ]
    for column, (value, label) in zip(metric_columns, metric_items):
        with column:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br><div class='eyebrow'>BOUNTY BOARD</div>", unsafe_allow_html=True)
    if not bounties:
        st.info("No bounties have been published yet. The authorized owner can create one in Owner Console.")
    for bounty in bounties:
        render_bounty_card(bounty, owner_encryption["key_id"] if owner_encryption else None)

    if owner_encryption:
        with st.expander("AstraCMS public report-encryption key", expanded=False):
            st.caption("This key is public and can encrypt reports only. The matching private key remains in the owner’s server-side configuration.")
            st.code(owner_encryption["public_key_b64"], language=None)
            st.caption(f"Key ID · {owner_encryption['key_id']}")

    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        st.markdown("<div class='eyebrow'>WHY MIDNIGHT</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="protocol-card">
                <h3>Privacy is the product.</h3>
                <p><strong>Public:</strong> bounty status, safe resolution signals, and a deployment reference.</p>
                <p><strong>Private:</strong> exploit content, reporter pseudonym, report commitment preimage, and shielded recipient address.</p>
                <p><strong>Verifiable:</strong> a report was committed first, the owner made a decision, and a payout receipt was recorded.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("<div class='eyebrow'>PUBLIC TIMELINE</div>", unsafe_allow_html=True)
        if bounties:
            timeline_options = {bounty_label(bounty): bounty for bounty in bounties}
            selected_label = st.selectbox("Bounty timeline", list(timeline_options), key="public_bounty_timeline")
            if selected_label is not None:
                selected_bounty = timeline_options[selected_label]
                st.caption(f"Safe public events for {selected_bounty['id']} only.")
                events = list_events(str(selected_bounty["id"]))
                if events:
                    for event in events:
                        render_event(event)
                else:
                    st.info("No public-safe events have been recorded for this bounty yet.")

    if not deployment["is_deployed"]:
        st.info(
            "The app is intentionally in deployment-pending mode. Complete the PreProd flow in the Protocol & Deploy page and add the verified address/transaction before submitting to judges."
        )


def render_submit_report() -> None:
    open_bounties = [bounty for bounty in list_bounties() if bounty["status"] == "OPEN"]

    st.markdown("<div class='eyebrow'>RESEARCHER VAULT</div>", unsafe_allow_html=True)
    st.header("Submit a private report")
    st.caption("Choose one open bounty. Every report uses a fresh encryption envelope for the owner’s published X25519 public key before it is persisted.")
    owner_encryption = get_owner_encryption_profile()

    if not owner_encryption:
        st.error("Secure submissions are unavailable until the owner configures a valid X25519 report-encryption private key.")
        st.code('owner_x25519_private_key_b64 = "<generated-private-key>"', language="toml")
        st.caption("The owner generates this once and stores it only in Streamlit secrets. Researchers never receive or enter it.")
        return

    if not open_bounties:
        st.warning("There are no open bounties right now. The owner can publish another scoped demo bounty in Owner Console.")
        return

    bounty_options = {bounty_label(bounty): bounty for bounty in open_bounties}
    selected_label = st.selectbox("Bounty to research", list(bounty_options), key="research_bounty")
    if selected_label is None:
        return
    bounty = bounty_options[selected_label]

    left, right = st.columns([1.35, 0.65], gap="large")
    with right:
        st.markdown(
            f"""
            <div class="protocol-card">
                <div class="eyebrow">SAFE TESTING RULES</div>
                <h3>{esc(bounty['target_name'])}</h3>
                <p>{esc(bounty['description'])}</p>
                <p class="mono">SCOPE · {esc(bounty['scope'])}</p>
                <hr>
                <p>Use only the stated demo scope. Do not test production systems, extract data, or use denial-of-service techniques.</p>
                <p class="mono">RECIPIENT KEY · {esc(owner_encryption['key_id'])}</p>
                <p class="mono">PAYLOAD → X25519 + HKDF + AES-256-GCM</p>
                <p class="mono">COMMITMENT → SHA-256(PAYLOAD + RANDOM SALT)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with left:
        with st.form("private_report_form", clear_on_submit=True):
            reporter_alias = st.text_input("Researcher alias", placeholder="e.g. nocturne_17")
            report_title = st.text_input("Report title", placeholder="Stored XSS through the editor preview field")
            severity = st.selectbox("Suggested severity", ["Critical", "High", "Medium", "Low"]) or "Low"
            impact = st.text_area("Impact", placeholder="Explain what an attacker could do if this issue were exploited.", height=110)
            reproduction = st.text_area("Safe reproduction steps", placeholder="Use the isolated target and test account. Keep the proof of concept minimal.", height=150)
            remediation = st.text_area("Suggested remediation", placeholder="Example: apply context-aware output encoding and a restrictive CSP.", height=100)
            st.info(f"This report will be encrypted automatically for owner key `{owner_encryption['key_id']}`. Researchers never enter a shared decryption password.")
            accepted_rules = st.checkbox("I tested only the stated demo scope and did not access real user data.")
            submitted = st.form_submit_button("Encrypt & commit private report", use_container_width=True)

        if submitted:
            if not all([reporter_alias.strip(), report_title.strip(), impact.strip(), reproduction.strip()]):
                st.error("Add your alias, title, impact, and reproduction steps.")
            elif not accepted_rules:
                st.error("Confirm the safe-testing rule before submitting.")
            else:
                payload = {
                    "schema": "nightbounty.report.v1",
                    "bounty_id": bounty["id"],
                    "reporter_alias": reporter_alias.strip(),
                    "report_title": report_title.strip(),
                    "severity": severity,
                    "impact": impact.strip(),
                    "reproduction": reproduction.strip(),
                    "remediation": remediation.strip(),
                }
                try:
                    encrypted = encrypt_report(
                        payload,
                        owner_encryption["public_key_b64"],
                        bounty_id=str(bounty["id"]),
                    )
                    report = submit_report(
                        bounty_id=str(bounty["id"]),
                        reporter_alias=reporter_alias,
                        report_title=report_title,
                        severity=severity,
                        ciphertext=encrypted["ciphertext"],
                        encryption_salt=encrypted["encryption_salt"],
                        commitment=encrypted["commitment"],
                        payload_digest=encrypted["payload_digest"],
                        chain_status="LOCAL_DEMO_COMMITMENT",
                    )
                    st.success("Private report encrypted and committed to this bounty's local demo lifecycle.")
                    st.markdown(
                        f"""
                        <div class="protocol-card">
                            <div class="eyebrow">YOUR SAFE RECEIPT</div>
                            <h3>{esc(report['id'])}</h3>
                            <p class="mono">BOUNTY · {esc(bounty['id'])}</p>
                            <p class="mono">RECIPIENT KEY · {esc(owner_encryption['key_id'])}</p>
                            <p class="mono">COMMITMENT · {esc(short_commitment(report['commitment']))}</p>
                            <p class="mono">PAYLOAD DIGEST · {esc(short_commitment(report['payload_digest']))}</p>
                            <p>{esc(lifecycle_chain_note('submitReport'))}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except ValueError as exc:
                    st.error(str(exc))


def read_server_secret(environment_name: str, streamlit_name: str) -> str | None:
    """Read a secret without exposing it to the UI or browser session state."""
    configured = os.getenv(environment_name)
    if not configured:
        try:
            configured = st.secrets.get(streamlit_name)
        except FileNotFoundError:
            configured = None
    value = str(configured or "").strip()
    return value or None


def get_owner_access_code() -> str | None:
    """Read the owner gate from a server-side environment variable or secret."""
    return normalize_owner_access_code(
        read_server_secret("NIGHTBOUNTY_OWNER_ACCESS_CODE", "owner_access_code")
    )


def get_owner_encryption_profile() -> dict[str, str] | None:
    """Derive the public owner profile from a server-only X25519 private key."""
    private_key_b64 = read_server_secret(
        "NIGHTBOUNTY_OWNER_X25519_PRIVATE_KEY_B64",
        "owner_x25519_private_key_b64",
    )
    if not private_key_b64:
        return None
    try:
        public_key_b64 = owner_public_key_from_private_key(private_key_b64)
    except ValueError:
        return None
    return {
        "private_key_b64": private_key_b64,
        "public_key_b64": public_key_b64,
        "key_id": owner_key_id(public_key_b64),
    }


def lock_owner_console() -> None:
    """Remove authorization and any decrypted report content from this session."""
    st.session_state.pop("is_owner", None)
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith("payload_"):
            del st.session_state[key]


def render_owner_console() -> None:
    st.markdown("<div class='eyebrow'>OWNER CONSOLE</div>", unsafe_allow_html=True)
    st.header("Private owner review")
    access_code = get_owner_access_code()

    if not st.session_state.get("is_owner"):
        st.caption("AstraCMS Security Desk only. Report metadata and ciphertext remain unavailable until the owner gate is unlocked.")
        if not access_code:
            st.warning("Owner access is not configured. Add a private code before this console can display reports.")
            st.code('owner_access_code = "use-a-long-random-private-code"', language="toml")
            st.caption("For local use, set `NIGHTBOUNTY_OWNER_ACCESS_CODE`. On Streamlit Community Cloud, add `owner_access_code` in App settings → Secrets.")
            return

        with st.form("owner_access_gate"):
            submitted_code = st.text_input("Owner access code", type="password")
            unlocked = st.form_submit_button("Unlock owner console", type="primary", use_container_width=True)
        if unlocked:
            if matches_owner_access_code(submitted_code, access_code):
                st.session_state["is_owner"] = True
                st.rerun()
            st.error("That owner access code is not valid.")
        return

    owner_encryption = get_owner_encryption_profile()
    action_column, lock_column = st.columns([0.76, 0.24])
    with action_column:
        if owner_encryption:
            st.caption(f"AstraCMS Security Desk is the authorized demo owner. New reports are encrypted for `{owner_encryption['key_id']}` and can be decrypted only with this configured private key.")
        else:
            st.caption("AstraCMS Security Desk is the authorized demo owner. Configure the owner X25519 private key before accepting secure reports.")
    with lock_column:
        if st.button("Lock console", use_container_width=True):
            lock_owner_console()
            st.rerun()

    if not owner_encryption:
        st.warning("Report encryption is not configured. Create a key with `python3 tools/generate_owner_keypair.py`, then add the private value to Streamlit secrets. Do not publish that private value.")

    st.markdown("<br><div class='eyebrow'>PUBLISH DEMO BOUNTY</div>", unsafe_allow_html=True)
    with st.expander("Create a new scoped bounty", expanded=False):
        st.caption("This creates a local workspace bounty for the demo. It does not claim a new Midnight contract deployment.")
        with st.form("create_bounty_form", clear_on_submit=True):
            title_column, target_column = st.columns(2)
            with title_column:
                bounty_title = st.text_input("Bounty title", placeholder="Unsafe file attachment preview")
            with target_column:
                target_name = st.text_input("Isolated target", placeholder="AstraCMS · isolated staging target")
            reward_column, severity_column = st.columns(2)
            with reward_column:
                reward = st.text_input("Reward", placeholder="150 tNIGHT")
            with severity_column:
                bounty_severity = st.selectbox("Maximum severity", ["Critical", "High", "Medium", "Low"]) or "Medium"
            description = st.text_area("Public-safe description", placeholder="Describe the permitted test scenario without publishing exploit details.", height=90)
            scope = st.text_area("Testing scope", placeholder="Only the isolated demo URL and supplied test accounts. No production systems or data extraction.", height=90)
            owner_alias = st.text_input("Owner display name", value="AstraCMS Security Desk")
            published = st.form_submit_button("Publish demo bounty", type="primary", use_container_width=True)

        if published:
            try:
                created_bounty = create_bounty(
                    title=bounty_title,
                    target_name=target_name,
                    reward=reward,
                    severity=bounty_severity,
                    description=description,
                    scope=scope,
                    owner_alias=owner_alias,
                )
                st.session_state["owner_selected_bounty"] = created_bounty["id"]
                st.session_state["owner_bounty_notice"] = f"Published {created_bounty['id']} for the local demo workspace."
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    bounties = list_bounties()
    if not bounties:
        st.info("No bounties have been published yet.")
        return

    notice = st.session_state.pop("owner_bounty_notice", None)
    if isinstance(notice, str):
        st.success(notice)

    bounty_options = {bounty_label(bounty): bounty for bounty in bounties}
    selected_bounty_id = st.session_state.get("owner_selected_bounty")
    selected_index = next(
        (index for index, bounty in enumerate(bounties) if bounty["id"] == selected_bounty_id),
        0,
    )
    selected_label = st.selectbox(
        "Bounty context",
        list(bounty_options),
        index=selected_index,
        key="owner_bounty_context",
    )
    if selected_label is None:
        return
    bounty = bounty_options[selected_label]
    st.session_state["owner_selected_bounty"] = bounty["id"]
    render_bounty_card(bounty, owner_encryption["key_id"] if owner_encryption else None)

    reports = list_reports(str(bounty["id"]))
    if not reports:
        st.markdown(
            """
            <div class="protocol-card">
                <h3>No private report waiting for this bounty.</h3>
                <p>Use Researcher Vault with a safe test report, or select another bounty context.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    report_options = {f"{report['id']} · {report['status']} · {report['report_title']}": report["id"] for report in reports}
    selected_label = st.selectbox("Private report", list(report_options))
    if selected_label is None:
        return
    report = get_report(report_options[selected_label])
    assert report is not None

    st.markdown(
        f"""
        <div class="bounty-card">
            <div class="mono">{esc(report['id'])} · {esc(report['created_at'])}</div>
            <h3>{esc(report['report_title'])}</h3>
            <div class="bounty-meta">
                {status_chip(report['status'])}
                <span class="chip coral">{esc(report['severity'])}</span>
                <span class="chip">RESEARCHER · {esc(report['reporter_alias'])}</span>
            </div>
            <div class="mono">COMMITMENT · {esc(short_commitment(report['commitment']))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_public_key_envelope(report["encryption_salt"]):
        if not owner_encryption:
            st.error("This report is encrypted for an owner key that is not configured on this server.")
        elif st.button("Decrypt with configured owner key", type="primary", key=f"decrypt_{report['id']}"):
            try:
                st.session_state[f"payload_{report['id']}"] = decrypt_report(
                    report["ciphertext"],
                    report["encryption_salt"],
                    owner_encryption["private_key_b64"],
                    bounty_id=report["bounty_id"],
                )
                st.success("Report authenticated and decrypted for this owner session.")
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.warning("This is a legacy shared-key demo report created before the public-key upgrade.")
        with st.form(f"legacy_unlock_{report['id']}"):
            collaboration_key = st.text_input("Legacy collaboration key", type="password")
            unlocked = st.form_submit_button("Decrypt legacy report")
        if unlocked:
            try:
                st.session_state[f"payload_{report['id']}"] = decrypt_legacy_report(
                    report["ciphertext"], report["encryption_salt"], collaboration_key
                )
                st.success("Legacy report decrypted for this owner session.")
            except ValueError as exc:
                st.error(str(exc))

    payload = st.session_state.get(f"payload_{report['id']}")
    if payload:
        with st.expander("Private report content", expanded=True):
            st.markdown(f"**Impact**  \n{esc(payload['impact'])}")
            st.markdown(f"**Safe reproduction**  \n{esc(payload['reproduction'])}")
            if payload.get("remediation"):
                st.markdown(f"**Suggested remediation**  \n{esc(payload['remediation'])}")

    chain_status = "LOCAL_DEMO_OWNER_ACTION"
    if report["status"] == "SUBMITTED" and payload:
        accept_column, reject_column = st.columns(2)
        with accept_column:
            if st.button("Accept report", type="primary", use_container_width=True):
                transition_report(report["id"], "ACCEPTED", chain_status=chain_status)
                st.success("Report accepted. Authorize the shielded reward next.")
                st.rerun()
        with reject_column:
            if st.button("Reject report", use_container_width=True):
                transition_report(report["id"], "REJECTED", chain_status=chain_status)
                st.info("Report closed without publishing its contents.")
                st.rerun()
    elif report["status"] == "SUBMITTED":
        st.info("Decrypt the report before making an owner decision.")

    if report["status"] == "ACCEPTED":
        st.markdown("<div class='eyebrow'>PAYOUT RECEIPT</div>", unsafe_allow_html=True)
        st.info("Send the reward using Lace as a shielded tNIGHT transfer, then paste the transaction or receipt commitment below. The recipient address stays out of this public dashboard.")
        with st.form(f"payout_{report['id']}"):
            payout_reference = st.text_input("Shielded transfer transaction / receipt commitment", placeholder="Paste a verified reference")
            paid = st.form_submit_button("Record shielded payout", use_container_width=True)
        if paid:
            if not payout_reference.strip():
                st.error("Paste the verified payout transaction or receipt commitment.")
            else:
                transition_report(
                    report["id"],
                    "PAID",
                    chain_status="LOCAL_DEMO_PAYOUT_RECEIPT",
                    payout_reference=payout_reference,
                )
                st.success("Payout receipt recorded. The public timeline contains no recipient identity.")
                st.rerun()

    if report["status"] == "PAID":
        st.success("This report is resolved and paid. Publish only a redacted advisory after the project has patched the issue.")
        if report.get("payout_reference"):
            st.code(report["payout_reference"], language=None)


def render_protocol_deploy() -> None:
    deployment = get_deployment()
    st.markdown("<div class='eyebrow'>PROTOCOL & DEPLOY</div>", unsafe_allow_html=True)
    st.header("What judges should verify")

    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        st.markdown(
            """
            <div class="protocol-card">
                <h3>Public chain facts</h3>
                <p>• Contract deployment on Midnight PreProd</p>
                <p>• One deployed bounty lifecycle</p>
                <p>• Salted report and payout commitments</p>
                <hr>
                <h3>Private by design</h3>
                <p>• Raw exploit content</p>
                <p>• Researcher identity and payout address</p>
                <p>• Report salt and ciphertext decryption key</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        status_text = "VERIFIED ON PREPROD" if deployment["is_deployed"] else "DEPLOYMENT PENDING"
        st.markdown(
            f"""
            <div class="protocol-card">
                <div class="eyebrow">NETWORK STATUS</div>
                <h3>{status_text}</h3>
                <p>{esc(contract_label())}</p>
                <p class="mono">CONTRACT · {esc(deployment.get('contract_address') or 'not configured')}</p>
                <p class="mono">DEPLOY TX · {esc(deployment.get('deployment_transaction') or 'not configured')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.info("The Owner Console can create multiple local demo bounties for one organization. The current Compact source models one bounty per deployment, so the app does not label those new local records as chain transactions.")

    st.markdown("<br><div class='eyebrow'>SOLO DEPLOYMENT CHECKLIST</div>", unsafe_allow_html=True)
    checklist = [
        "Open the current official Midnight `example-bboard` template and use its PreProd-compatible CLI/API workflow.",
        "Install the supported Compact compiler, then compile `midnight/contract/src/nightbounty.compact`.",
        "Run the official local Docker proof server and configure Lace for Midnight PreProd.",
        "Get tNIGHT from the PreProd faucet and generate tDUST for fees in Lace.",
        "Deploy the contract, then copy its verified address and deployment transaction into `midnight/deployment.json`.",
        "Run the submit → accept → shielded payout demo and retain transaction screenshots for Devpost.",
    ]
    for index, item in enumerate(checklist, start=1):
        st.markdown(
            f"<div class='event-card'><div class='event-time'>STEP {index:02d}</div><div class='event-title'>{esc(item)}</div></div>",
            unsafe_allow_html=True,
        )

    with st.expander("Compact contract lifecycle", expanded=False):
        st.code(
            dedent(
                """
                OPEN
                  └── submitReport(commitment)
                        └── REPORT_SUBMITTED
                              ├── acceptReport() → ACCEPTED
                              │                       └── confirmPayout(receiptCommitment) → PAID
                              └── rejectReport() → REJECTED
                """
            ).strip(),
            language="text",
        )

    with st.expander("Deployment metadata file", expanded=False):
        st.code(json.dumps({
            "network": "PreProd",
            "contract_address": "<verified contract address>",
            "deployment_transaction": "<verified transaction id>",
        }, indent=2), language="json")
        st.caption("Copy `midnight/deployment.json.example` to `midnight/deployment.json`. The real file is intentionally ignored by Git.")


def render_sidebar() -> str:
    deployment = get_deployment()
    with st.sidebar:
        st.markdown("<div class='brand-kicker'>MIDNIGHT TRACK · 2026</div>", unsafe_allow_html=True)
        st.markdown("## NIGHT<br>BOUNTY", unsafe_allow_html=True)
        st.markdown("<p class='mono'>PRIVATE RESPONSIBLE DISCLOSURE</p>", unsafe_allow_html=True)
        st.markdown("---")
        page = st.radio(
            "Navigate",
            ["Command Room", "Researcher Vault", "Owner Console", "Protocol & Deploy"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if deployment["is_deployed"]:
            st.markdown("<span class='chip mint'>PREPROD VERIFIED</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='chip amber'>DEPLOYMENT PENDING</span>", unsafe_allow_html=True)
        st.caption(contract_label())
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Reset local demo data", use_container_width=True):
            reset_demo_data()
            lock_owner_console()
            st.rerun()
        st.markdown("<p class='mono' style='margin-top:1.5rem'>BUILD FOR JUDGES</p>", unsafe_allow_html=True)
        st.caption("Show the Compact contract, PreProd address, private report flow, and shielded payout receipt—not a fake dashboard.")
    return page or "Command Room"


page = render_sidebar()

if page == "Command Room":
    render_command_room()
elif page == "Researcher Vault":
    render_submit_report()
elif page == "Owner Console":
    render_owner_console()
else:
    render_protocol_deploy()

st.markdown("<br><hr><p class='mono'>NIGHTBOUNTY · PRIVATE RESPONSIBLE DISCLOSURE · HACKATHON MVP</p>", unsafe_allow_html=True)
