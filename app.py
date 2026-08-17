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
    authenticate_researcher,
    create_bounty,
    get_report,
    get_researcher,
    initialize,
    list_bounties,
    list_events,
    list_reports,
    metrics,
    register_researcher,
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
    --radius-lg: 18px;
    --radius-md: 13px;
    --radius-sm: 9px;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
.stApp {
    background: radial-gradient(circle at 72% -12%, rgba(45,225,194,.11), transparent 28%), radial-gradient(circle at 4% 44%, rgba(168,140,255,.07), transparent 25%), var(--night);
    color: var(--paper);
    overflow: hidden;
}
.stApp::before {
    content: "";
    position: fixed;
    inset: -20% -10% 0;
    pointer-events: none;
    opacity: .34;
    background-image: linear-gradient(rgba(255,255,255,.032) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.032) 1px, transparent 1px);
    background-size: 38px 38px;
    mask-image: linear-gradient(to bottom, black, transparent 72%);
    transform: perspective(850px) rotateX(57deg) scale(1.48) translateY(-6%);
    transform-origin: center top;
}
.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,.4) 100%);
    z-index: 0;
}
section[data-testid="stMain"] { position: relative; z-index: 1; }
section[data-testid="stSidebar"] {
    background: radial-gradient(circle at 100% 10%, rgba(168,140,255,.25), transparent 29%), radial-gradient(circle at 8% 84%, rgba(92,53,179,.16), transparent 25%), linear-gradient(155deg, #17122b, #0c1018 62%);
    border-right: 1px solid rgba(168,140,255,.3);
    box-shadow: 12px 0 38px rgba(0,0,0,.18);
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.35rem;
    background: transparent;
}
section[data-testid="stSidebar"] h2 { color: var(--paper); letter-spacing: -.055em; }
section[data-testid="stSidebar"] hr { border-color: rgba(168,140,255,.22); }
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    margin: .12rem 0;
    padding: .4rem .48rem;
    transition: background .18s ease, border-color .18s ease, transform .18s ease;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(168,140,255,.1);
    border-color: rgba(168,140,255,.22);
    transform: translateX(2px);
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(90deg, rgba(168,140,255,.22), rgba(45,225,194,.06));
    border-color: rgba(168,140,255,.44);
    box-shadow: inset 3px 0 0 var(--mint), 0 7px 16px rgba(0,0,0,.15);
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p { color: var(--paper) !important; font-weight: 600; }
.block-container {
    max-width: 1280px;
    padding-top: 4.75rem;
    padding-bottom: 3.5rem;
    perspective: 1400px;
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
.brand-kicker { color: var(--violet); font-size: .72rem; }
.eyebrow { color: var(--mint); font-size: .72rem; margin-bottom: .65rem; }
.mono { color: var(--muted); font-size: .72rem; }

.hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(270px, .42fr);
    gap: 1.2rem;
    margin: .1rem 0 1.8rem;
}
.hero-main, .hero-side, .metric-card, .bounty-card, .event-card, .protocol-card {
    border: 1px solid rgba(94, 117, 139, .42);
    background: linear-gradient(135deg, rgba(25, 34, 47, .97), rgba(12, 17, 24, .96));
    box-shadow: 0 16px 34px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.035);
    transform-style: preserve-3d;
    border-radius: var(--radius-lg);
    transition: transform .28s cubic-bezier(.2,.8,.2,1), border-color .28s ease, box-shadow .28s ease;
}
.hero-main { padding: 2.1rem 2.2rem 2rem; min-height: 282px; position: relative; overflow: hidden; background: radial-gradient(circle at 78% 42%, rgba(95,73,224,.6), transparent 19%), radial-gradient(circle at 92% 78%, rgba(45,225,194,.28), transparent 30%), linear-gradient(135deg, #211b3a, #111720 62%); box-shadow: 0 28px 60px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.055); }
.hero-main::after {
    content: "";
    width: 240px; height: 240px;
    position: absolute; right: -90px; bottom: -130px;
    border: 1px solid rgba(45,225,194,.5); border-radius: 50%;
    box-shadow: 0 0 0 42px rgba(45,225,194,.07), 0 0 0 84px rgba(45,225,194,.03);
}
.hero-main h1 { font-size: clamp(2.7rem, 5vw, 5rem); line-height: .9; margin: .1rem 0 1.15rem; max-width: 720px; position: relative; z-index: 1; transform: translateZ(30px); }
.hero-main p { font-size: 1.08rem; max-width: 620px; position: relative; z-index: 1; transform: translateZ(20px); }
.hero-main .eyebrow { position: relative; z-index: 1; transform: translateZ(38px); }
.hero-side { padding: 1.45rem; display: flex; flex-direction: column; justify-content: space-between; min-height: 282px; }
.hero-side > * { transform: translateZ(18px); }
.hero-main:hover { transform: translateY(-5px) rotateX(1.25deg) rotateY(-.6deg); border-color: rgba(45,225,194,.46); box-shadow: 0 36px 72px rgba(0,0,0,.42), 0 0 45px rgba(45,225,194,.08); }
.hero-side:hover { transform: translateY(-5px) rotateX(1deg) rotateY(.7deg); border-color: rgba(168,140,255,.46); box-shadow: 0 30px 58px rgba(0,0,0,.36), 0 0 38px rgba(168,140,255,.08); }
.hero-side h3 { font-size: 1.25rem; margin: .4rem 0; }
.contract-address { font-family: 'DM Mono', monospace; font-size: .78rem; color: var(--paper); padding: .75rem 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); overflow-wrap: anywhere; }

.command-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: .9rem 1.1rem;
    margin-bottom: 1.25rem;
    border: 1px solid rgba(125,104,210,.32);
    background: linear-gradient(100deg, rgba(45,35,83,.92), rgba(17,23,32,.94) 54%, rgba(44,32,74,.84));
    border-radius: var(--radius-lg);
    box-shadow: 0 18px 42px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.07);
}
.command-brand { display: flex; align-items: center; gap: .68rem; min-width: max-content; }
.command-mark { width: 2rem; height: 2rem; display: grid; place-items: center; border-radius: 50%; color: #fff; background: radial-gradient(circle at 35% 25%, #d7a6ff, #6f41d9 58%, #281653); box-shadow: 0 0 22px rgba(168,140,255,.45); font-family: 'DM Mono', monospace; font-weight: 700; }
.command-brand strong { color: var(--paper); font-size: .95rem; letter-spacing: -.02em; }
.command-pills { display: flex; gap: .45rem; flex-wrap: wrap; justify-content: flex-end; }
.command-pill { color: var(--muted); border: 1px solid rgba(255,255,255,.08); background: rgba(5,8,13,.28); padding: .42rem .7rem; border-radius: 999px; font: .64rem 'DM Mono', monospace; letter-spacing: .06em; }
.command-pill.active { color: var(--paper); border-color: rgba(168,140,255,.46); background: rgba(168,140,255,.12); }
.hero-signal { position: absolute; right: 7%; top: 50%; width: 176px; height: 176px; transform: translateY(-50%) translateZ(44px); display: grid; place-items: center; border: 1px solid rgba(230,221,255,.7); border-radius: 42px; background: linear-gradient(145deg, rgba(224,197,255,.25), rgba(79,47,184,.36)); box-shadow: 0 0 0 18px rgba(168,140,255,.07), 0 0 0 38px rgba(45,225,194,.035), 0 26px 45px rgba(0,0,0,.24); rotate: -7deg; }
.hero-signal::before { content: ""; position: absolute; inset: 12%; border: 1px solid rgba(45,225,194,.55); border-radius: 50%; }
.hero-signal span { position: relative; z-index: 1; color: #fff; font-size: 3.5rem; font-weight: 700; letter-spacing: -.12em; text-shadow: 0 7px 22px rgba(0,0,0,.4); }
.hero-main h1, .hero-main p, .hero-main .eyebrow { max-width: 63%; }

.metric-card { padding: 1rem 1.05rem; min-height: 114px; }
.metric-card:hover { transform: translateY(-5px) rotateX(2deg); border-color: rgba(45,225,194,.4); box-shadow: 0 24px 42px rgba(0,0,0,.34), 0 0 26px rgba(45,225,194,.06); }
.metric-value { color: var(--paper); font-size: 2rem; font-weight: 700; letter-spacing: -.06em; margin: .3rem 0; transform: translateZ(18px); }
.metric-label { color: var(--muted); font-size: .82rem; }

.bounty-card { padding: 1.45rem; margin: .75rem 0 1.2rem; position: relative; overflow: hidden; }
.bounty-card::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(115deg, transparent 18%, rgba(255,255,255,.045) 48%, transparent 66%); transform: translateX(-120%); transition: transform .65s ease; }
.bounty-card:hover { transform: translateY(-6px) rotateX(1.4deg) rotateY(-.45deg); border-color: rgba(45,225,194,.52); box-shadow: 0 30px 55px rgba(0,0,0,.38), 0 0 36px rgba(45,225,194,.08); }
.bounty-card:hover::after { transform: translateX(120%); }
.bounty-card h3 { font-size: 1.38rem; margin: .25rem 0 .4rem; position: relative; z-index: 1; transform: translateZ(20px); }
.bounty-card p { max-width: 800px; }
.bounty-meta { display: flex; flex-wrap: wrap; gap: .45rem; margin: 1rem 0 .8rem; }
.chip { border: 1px solid var(--line); border-radius: 999px; color: var(--paper); padding: .3rem .65rem; font-family: 'DM Mono', monospace; font-size: .72rem; }
.chip.mint { border-color: rgba(45,225,194,.48); color: var(--mint); }
.chip.amber { border-color: rgba(244,189,87,.45); color: var(--amber); }
.chip.coral { border-color: rgba(255,118,92,.48); color: var(--coral); }
.chip.violet { border-color: rgba(168,140,255,.48); color: var(--violet); }

.event-card { padding: 1rem 1.1rem; border-left: 3px solid var(--mint); border-radius: var(--radius-md); margin-bottom: .65rem; }
.event-card:hover, .protocol-card:hover { transform: translateY(-4px) rotateX(1deg); border-color: rgba(45,225,194,.38); box-shadow: 0 22px 40px rgba(0,0,0,.28); }
.event-card .event-title { color: var(--paper); font-weight: 600; margin: .22rem 0; }
.event-time { color: var(--muted); font-size: .67rem; }
.event-chain { color: var(--mint); font-family: 'DM Mono', monospace; font-size: .67rem; text-transform: uppercase; }

.protocol-card { padding: 1.25rem; min-height: 100%; }
.protocol-card h3 { margin-top: .15rem; }
.protocol-card strong { color: var(--paper); }

.stButton > button, .stFormSubmitButton > button {
    border-radius: var(--radius-md);
    border: 1px solid var(--mint);
    background: var(--mint);
    color: #08110f;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    padding: .55rem 1rem;
}
.stButton > button, .stFormSubmitButton > button {
    box-shadow: 0 5px 0 #187f70, 0 11px 22px rgba(45,225,194,.16);
    transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    border-color: var(--paper);
    color: #08110f;
    background: #7ef4df;
    transform: translateY(-3px);
    box-shadow: 0 8px 0 #187f70, 0 17px 30px rgba(45,225,194,.22);
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(3px); box-shadow: 0 2px 0 #187f70, 0 5px 12px rgba(45,225,194,.14); }
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {
    background: #0d131b !important;
    border-color: var(--line) !important;
    color: var(--paper) !important;
    border-radius: var(--radius-sm) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label, .stCheckbox label {
    color: var(--paper) !important;
    font-size: .9rem !important;
}
[data-testid="stAlert"] { border-radius: var(--radius-md); }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel); }
hr { border-color: var(--line); }

.command-room-note { color: var(--muted); font: .68rem 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; }

.vault-bento { display: grid; grid-template-columns: 1.05fr 1.22fr .72fr; gap: 1rem; margin-bottom: 1rem; }
.vault-visual, .vault-copy, .vault-feature, .vault-panel, .bounty-overview {
    border: 1px solid rgba(125,104,210,.28);
    background: linear-gradient(135deg, rgba(28,24,46,.98), rgba(14,18,25,.97));
    border-radius: var(--radius-lg);
    box-shadow: 0 22px 50px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.05);
}
.vault-visual { min-height: 284px; position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; padding: 1.4rem; background: radial-gradient(circle at 67% 28%, rgba(158,116,255,.9), transparent 21%), radial-gradient(circle at 64% 65%, rgba(47,205,239,.7), transparent 28%), radial-gradient(circle at 20% 84%, rgba(221,80,231,.75), transparent 25%), linear-gradient(145deg, #26145e, #161342 72%); }
.vault-visual::before { content: ""; position: absolute; width: 210px; height: 210px; border: 1px solid rgba(255,255,255,.3); border-radius: 50%; left: -62px; top: 44px; box-shadow: 0 0 0 28px rgba(255,255,255,.04), 0 0 0 58px rgba(255,255,255,.025); }
.vault-visual::after { content: ""; position: absolute; inset: 0; background: linear-gradient(130deg, transparent 44%, rgba(255,255,255,.12) 49%, transparent 53%); opacity: .65; }
.vault-visual > * { position: relative; z-index: 1; }
.vault-tag { color: rgba(255,255,255,.9); font: .72rem 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; }
.vault-monogram { align-self: center; display: grid; place-items: center; width: 144px; height: 144px; border: 12px solid rgba(255,255,255,.92); border-radius: 42px; color: #fff; font-size: 4rem; font-weight: 700; letter-spacing: -.16em; transform: rotate(-8deg); text-shadow: 0 8px 20px rgba(0,0,0,.24); box-shadow: 0 18px 34px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.5); }
.vault-visual h2 { margin: 0; font-size: 1.6rem; position: relative; z-index: 1; }
.vault-copy { min-height: 284px; padding: 2rem 1.7rem; position: relative; overflow: hidden; }
.vault-copy::before { content: ""; position: absolute; inset: 0; pointer-events: none; background: radial-gradient(circle at 15% 0, rgba(168,140,255,.32), transparent 34%); }
.vault-copy > * { position: relative; z-index: 1; }
.vault-copy h1 { margin: .4rem 0 1.1rem; max-width: 480px; font-size: clamp(2.1rem, 3.5vw, 3.7rem); line-height: .98; }
.vault-copy p { max-width: 520px; font-size: 1rem; }
.vault-feature-stack { display: grid; gap: .72rem; }
.vault-feature { min-height: calc((284px - 1.44rem) / 3); padding: 1rem 1.05rem; display: flex; flex-direction: column; justify-content: center; }
.vault-feature h3 { margin: 0 0 .3rem; font-size: 1rem; }
.vault-feature p { margin: 0; font-size: .82rem; }
.vault-feature:hover, .vault-panel:hover, .bounty-overview:hover, .vault-copy:hover, .vault-visual:hover { transform: translateY(-4px) rotateX(1deg); border-color: rgba(168,140,255,.52); box-shadow: 0 28px 54px rgba(0,0,0,.38), 0 0 30px rgba(168,140,255,.08); }
.vault-lower { display: grid; grid-template-columns: 1.12fr .88fr; gap: 1rem; margin: 1rem 0; }
.vault-panel { padding: 1.35rem; min-height: 205px; }
.vault-panel h2, .bounty-overview h2 { margin: 0 0 .55rem; font-size: 1.35rem; }
.vault-process { display: grid; grid-template-columns: repeat(3, 1fr); gap: .55rem; margin-top: 1rem; }
.vault-step { border: 1px solid rgba(255,255,255,.08); border-radius: var(--radius-sm); background: rgba(5,8,13,.22); padding: .7rem; }
.vault-step strong { color: var(--paper); display: block; font: .68rem 'DM Mono', monospace; letter-spacing: .06em; }
.vault-step span { color: var(--muted); display: block; font-size: .78rem; margin-top: .3rem; }
.bounty-overview { padding: 1.35rem; margin-top: 1rem; overflow: hidden; }
.bounty-table-head, .bounty-table-row { display: grid; grid-template-columns: minmax(180px, 1.6fr) .8fr .65fr .9fr 1fr; gap: .8rem; align-items: center; }
.bounty-table-head { color: var(--muted); padding: .55rem .8rem; font: .64rem 'DM Mono', monospace; letter-spacing: .06em; text-transform: uppercase; }
.bounty-table-row { padding: .85rem .8rem; border-top: 1px solid rgba(255,255,255,.06); border-radius: var(--radius-sm); background: rgba(5,8,13,.14); transition: background .2s ease, transform .2s ease; }
.bounty-table-row:hover { background: rgba(168,140,255,.1); transform: translateX(4px); }
.bounty-name { color: var(--paper); font-weight: 600; }
.bounty-id { color: var(--muted); display: block; margin-top: .2rem; font: .63rem 'DM Mono', monospace; }

.page-vault-header { position: relative; overflow: hidden; display: flex; justify-content: space-between; gap: 1.25rem; align-items: flex-end; padding: 1.65rem 1.7rem; margin-bottom: 1.25rem; border: 1px solid rgba(125,104,210,.32); border-radius: var(--radius-lg); background: radial-gradient(circle at 85% 15%, rgba(168,140,255,.34), transparent 26%), linear-gradient(110deg, rgba(36,26,67,.96), rgba(14,18,25,.98) 64%); box-shadow: 0 23px 50px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.06); }
.page-vault-header::after { content: ""; position: absolute; width: 180px; height: 180px; right: -48px; bottom: -98px; border: 1px solid rgba(45,225,194,.5); border-radius: 50%; box-shadow: 0 0 0 22px rgba(45,225,194,.055), 0 0 0 44px rgba(168,140,255,.035); }
.page-vault-header > * { position: relative; z-index: 1; }
.page-vault-header h1 { margin: .25rem 0 .55rem; font-size: clamp(2.25rem, 4vw, 3.7rem); line-height: 1; }
.page-vault-header p { margin: 0; max-width: 720px; font-size: .98rem; }
.page-vault-tags { display: flex; gap: .45rem; flex-wrap: wrap; justify-content: flex-end; padding-bottom: .25rem; }
.page-vault-tag { border: 1px solid rgba(255,255,255,.1); border-radius: 999px; background: rgba(8,10,16,.26); color: var(--muted); padding: .42rem .68rem; font: .64rem 'DM Mono', monospace; letter-spacing: .06em; text-transform: uppercase; }
.page-vault-tag.primary { border-color: rgba(45,225,194,.42); color: var(--mint); }
div[data-testid="stForm"] { border: 1px solid rgba(125,104,210,.28); border-radius: var(--radius-lg); background: linear-gradient(135deg, rgba(28,24,46,.78), rgba(13,18,26,.86)); box-shadow: 0 18px 38px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.04); padding: 1.1rem 1.15rem; }
button[data-baseweb="tab"] { border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
@media (max-width: 850px) {
    .hero { grid-template-columns: 1fr; }
    .hero-main h1 { font-size: 3rem; }
    .hero-main h1, .hero-main p, .hero-main .eyebrow { max-width: 100%; }
    .hero-signal { opacity: .28; right: -1.8rem; width: 130px; height: 130px; }
    .command-topbar { align-items: flex-start; flex-direction: column; }
    .command-pills { justify-content: flex-start; }
    .vault-bento, .vault-lower { grid-template-columns: 1fr; }
    .vault-visual, .vault-copy { min-height: 230px; }
    .page-vault-header { align-items: flex-start; flex-direction: column; }
    .page-vault-tags { justify-content: flex-start; }
    .vault-copy h1 { font-size: 2.45rem; }
    .vault-feature-stack { grid-template-columns: repeat(3, 1fr); }
    .vault-feature { min-height: 150px; }
    .bounty-table-head, .bounty-table-row { grid-template-columns: minmax(150px, 1fr) .75fr .65fr; }
    .bounty-table-head > :nth-child(4), .bounty-table-head > :nth-child(5), .bounty-table-row > :nth-child(4), .bounty-table-row > :nth-child(5) { display: none; }
    .hero-main:hover, .hero-side:hover, .metric-card:hover, .bounty-card:hover, .event-card:hover, .protocol-card:hover, .vault-feature:hover, .vault-panel:hover, .bounty-overview:hover, .vault-copy:hover, .vault-visual:hover { transform: translateY(-2px); }
}
@media (max-width: 560px) {
    .vault-feature-stack, .vault-process { grid-template-columns: 1fr; }
    .vault-feature { min-height: 0; }
    .vault-monogram { width: 116px; height: 116px; font-size: 3rem; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(value: object) -> str:
    return html.escape(str(value))


def render_page_vault_header(
    eyebrow: str,
    title: str,
    description: str,
    primary_tag: str,
    secondary_tag: str,
) -> None:
    """Render the shared rounded workspace header used outside Command Room."""
    st.markdown(
        f"""
        <section class="page-vault-header">
            <div>
                <div class="eyebrow">{esc(eyebrow)}</div>
                <h1>{esc(title)}</h1>
                <p>{esc(description)}</p>
            </div>
            <div class="page-vault-tags">
                <span class="page-vault-tag primary">{esc(primary_tag)}</span>
                <span class="page-vault-tag">{esc(secondary_tag)}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


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

    st.markdown(
        """
        <div class="command-topbar">
            <div class="command-brand"><div class="command-mark">N</div><strong>NightBounty Command Room</strong></div>
            <div class="command-pills">
                <span class="command-pill active">PRIVATE VAULT</span>
                <span class="command-pill">OWNER VERIFIED</span>
                <span class="command-pill">MIDNIGHT READY</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    deployment_label = "PREPROD VERIFIED" if deployment["is_deployed"] else "PREPROD PENDING"
    deployment_tone = "mint" if deployment["is_deployed"] else "amber"
    key_label = owner_encryption["key_id"] if owner_encryption else "ENCRYPTION SETUP REQUIRED"
    bounty_rows = "".join(
        f"""
        <div class="bounty-table-row">
            <div><span class="bounty-name">{esc(bounty['title'])}</span><span class="bounty-id">{esc(bounty['id'])} · {esc(bounty['target_name'])}</span></div>
            <div>{status_chip(str(bounty['status']))}</div>
            <div class="mono">{esc(bounty['severity'])}</div>
            <div class="mono">{esc(bounty['reward'])}</div>
            <div class="mono">{esc(key_label)}</div>
        </div>
        """
        for bounty in bounties
    )
    if not bounty_rows:
        bounty_rows = "<div class='bounty-table-row'><div class='bounty-name'>No bounties published</div><div>—</div><div>—</div><div>—</div><div>—</div></div>"

    st.markdown(
        f"""
        <div class="vault-bento">
            <section class="vault-visual">
                <div class="vault-tag">MIDNIGHT · PRIVATE VAULT</div>
                <div class="vault-monogram">NB</div>
                <h2>Night<br>Bounty</h2>
            </section>
            <section class="vault-copy">
                <div class="eyebrow">PRIVATE RESPONSIBLE DISCLOSURE</div>
                <h1>Proof before<br>public exposure.</h1>
                <p>Researchers commit encrypted reports first. Owners privately verify, decide, and reward without turning vulnerabilities into public attack guides.</p>
                <div class="bounty-meta"><span class="chip {deployment_tone}">{deployment_label}</span><span class="chip violet">{esc(key_label)}</span></div>
            </section>
            <section class="vault-feature-stack">
                <div class="vault-feature"><h3>Encrypted intake</h3><p>Fresh X25519 envelopes protect every report before it is persisted.</p></div>
                <div class="vault-feature"><h3>First disclosure</h3><p>Commitment receipts establish who reported before the issue is exposed.</p></div>
                <div class="vault-feature"><h3>Shielded reward</h3><p>tNIGHT payout evidence avoids placing recipient identity on the public board.</p></div>
            </section>
        </div>
        <div class="vault-lower">
            <section class="vault-panel">
                <div class="eyebrow">SECURE REPORTING FLOW</div>
                <h2>Built for the moment before disclosure.</h2>
                <p>Public bounty context, private exploit evidence, and an auditable resolution path in one focused workflow.</p>
                <div class="vault-process">
                    <div class="vault-step"><strong>01 · ENCRYPT</strong><span>Researcher locks report to owner key.</span></div>
                    <div class="vault-step"><strong>02 · COMMIT</strong><span>Safe commitment proves first disclosure.</span></div>
                    <div class="vault-step"><strong>03 · RESOLVE</strong><span>Owner accepts, rejects, or records payout.</span></div>
                </div>
            </section>
            <section class="vault-panel">
                <div class="eyebrow">WORKSPACE SIGNALS</div>
                <h2>Live case position</h2>
                <div class="vault-process">
                    <div class="vault-step"><strong>{summary['open_bounties']}</strong><span>Active bounties</span></div>
                    <div class="vault-step"><strong>{summary['private_reports']}</strong><span>Private reports</span></div>
                    <div class="vault-step"><strong>{summary['resolved']}</strong><span>Owner decisions</span></div>
                </div>
                <p class="command-room-note" style="margin-top:1rem">{summary['paid']} shielded payout receipts recorded</p>
            </section>
        </div>
        <section class="bounty-overview">
            <div class="eyebrow">OPEN BOUNTIES OVERVIEW</div>
            <h2>Responsible-disclosure board</h2>
            <div class="bounty-table-head"><span>Bounty</span><span>Status</span><span>Severity</span><span>Reward</span><span>Encryption</span></div>
            {bounty_rows}
        </section>
        """,
        unsafe_allow_html=True,
    )

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
                <p><strong>Public:</strong> bounty status, safe resolution signals, and deployment evidence.</p>
                <p><strong>Private:</strong> exploit content, pseudonymous account details, report preimages, and shielded recipients.</p>
                <p><strong>Verifiable:</strong> a commitment exists before the owner decision and payout receipt.</p>
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
        st.info("The visual workspace is ready, but deployment evidence is still pending. Use Protocol & Deploy and the local NightBounty deployer before claiming PreProd verified.")


def current_researcher() -> dict[str, object] | None:
    researcher_id = st.session_state.get("researcher_id")
    if not isinstance(researcher_id, str):
        return None
    researcher = get_researcher(researcher_id)
    if researcher is None:
        st.session_state.pop("researcher_id", None)
    return researcher


def render_researcher_access() -> dict[str, object] | None:
    """Render pseudonymous research-account sign-up/sign-in before report access."""
    researcher = current_researcher()
    if researcher is not None:
        identity_column, logout_column = st.columns([0.75, 0.25])
        with identity_column:
            st.caption(f"Signed in as researcher `{researcher['alias']}`. Your pseudonym is attached to new private reports.")
        with logout_column:
            if st.button("Log out", use_container_width=True, key="researcher_logout"):
                st.session_state.pop("researcher_id", None)
                st.rerun()
        return researcher

    st.markdown("<div class='eyebrow'>RESEARCHER IDENTITY</div>", unsafe_allow_html=True)
    st.caption("Create a pseudonymous account to submit a report. NightBounty collects no email or real-name data in this MVP.")
    signup_tab, login_tab = st.tabs(["Sign up", "Log in"])
    with signup_tab:
        with st.form("researcher_signup"):
            signup_alias = st.text_input("Researcher alias", placeholder="e.g. nocturne_17")
            signup_password = st.text_input("Password", type="password", help="At least 12 characters. Store it safely; this MVP has no password recovery.")
            confirm_password = st.text_input("Confirm password", type="password")
            registered = st.form_submit_button("Create researcher account", type="primary", use_container_width=True)
        if registered:
            if signup_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    created = register_researcher(signup_alias, signup_password)
                    st.session_state["researcher_id"] = created["id"]
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with login_tab:
        with st.form("researcher_login"):
            login_alias = st.text_input("Researcher alias", key="researcher_login_alias")
            login_password = st.text_input("Password", type="password", key="researcher_login_password")
            logged_in = st.form_submit_button("Log in to Researcher Vault", use_container_width=True)
        if logged_in:
            authenticated = authenticate_researcher(login_alias, login_password)
            if authenticated is None:
                st.error("Invalid alias or password.")
            else:
                st.session_state["researcher_id"] = authenticated["id"]
                st.rerun()
    return None


def render_submit_report() -> None:
    open_bounties = [bounty for bounty in list_bounties() if bounty["status"] == "OPEN"]

    render_page_vault_header(
        "RESEARCHER VAULT",
        "Submit a private report",
        "Choose one open bounty. Every report uses a fresh encryption envelope for the owner’s published X25519 public key before it is persisted.",
        "PSEUDONYMOUS ACCESS",
        "X25519 ENCRYPTED",
    )
    researcher = render_researcher_access()
    if researcher is None:
        return
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
            st.caption(f"Submitting as `{researcher['alias']}`")
            report_title = st.text_input("Report title", placeholder="Stored XSS through the editor preview field")
            severity = st.selectbox("Suggested severity", ["Critical", "High", "Medium", "Low"]) or "Low"
            impact = st.text_area("Impact", placeholder="Explain what an attacker could do if this issue were exploited.", height=110)
            reproduction = st.text_area("Safe reproduction steps", placeholder="Use the isolated target and test account. Keep the proof of concept minimal.", height=150)
            remediation = st.text_area("Suggested remediation", placeholder="Example: apply context-aware output encoding and a restrictive CSP.", height=100)
            st.info(f"This report will be encrypted automatically for owner key `{owner_encryption['key_id']}`. Researchers never enter a shared decryption password.")
            accepted_rules = st.checkbox("I tested only the stated demo scope and did not access real user data.")
            submitted = st.form_submit_button("Encrypt & commit private report", use_container_width=True)

        if submitted:
            if not all([report_title.strip(), impact.strip(), reproduction.strip()]):
                st.error("Add a title, impact, and reproduction steps.")
            elif not accepted_rules:
                st.error("Confirm the safe-testing rule before submitting.")
            else:
                payload = {
                    "schema": "nightbounty.report.v1",
                    "bounty_id": bounty["id"],
                    "researcher_alias": researcher["alias"],
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
                        researcher_id=str(researcher["id"]),
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
    render_page_vault_header(
        "OWNER CONSOLE",
        "Private owner review",
        "Unlock the gated workspace to inspect encrypted disclosure evidence, decide reports, and record shielded payout receipts.",
        "OWNER GATED",
        "PRIVATE REVIEW",
    )
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
    render_page_vault_header(
        "PROTOCOL & DEPLOY",
        "What judges should verify",
        "Review NightBounty’s private disclosure lifecycle, PreProd deployment evidence, and the exact path from local build to verified contract.",
        "MIDNIGHT PREPROD",
        "DEPLOYMENT EVIDENCE",
    )


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
        "From `midnight/deployer`, run `npm ci`, then `npm run proof-server:up`.",
        "Run `npm run deploy` to create/recover a local PreProd wallet, request tNIGHT, generate tDUST, and deploy NightBounty.",
        "Save the local recovery seed and encrypted private-state password; they are needed for owner-only contract calls.",
        "Copy the runner’s verified contract address and deployment transaction hash into `midnight/deployment.json`.",
        "Add the same verified values to Streamlit Cloud secrets before claiming PreProd verified.",
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
        if st.session_state.get("is_owner"):
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
