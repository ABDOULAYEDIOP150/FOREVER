"""Éléments d'interface partagés (style, cartes, badges)."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

PRIMARY = "#123456"

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1150px;}
.ent-hero {background: linear-gradient(120deg, #123456 0%, #1f5a8a 100%); color: #fff;
           padding: 1.3rem 1.6rem; border-radius: 14px; margin-bottom: 1.2rem;}
.ent-hero h2 {color: #fff; margin: 0 0 .2rem 0; font-size: 1.55rem;}
.ent-hero p {margin: 0; opacity: .85;}
.ent-card {border: 1px solid rgba(128,128,128,.25); border-radius: 12px; padding: 1rem 1.1rem; margin-bottom: .8rem;}
.ent-card h4 {margin: 0 0 .3rem 0;}
.ent-muted {opacity: .7; font-size: .88rem;}
.badge {display: inline-block; padding: .12rem .55rem; border-radius: 999px; font-size: .78rem; font-weight: 600;}
.b-ok {background: #dcf3e4; color: #146c2e;}
.b-ko {background: #fde2e1; color: #a1251b;}
.b-wait {background: #fff1d6; color: #8a5a00;}
.b-info {background: #e1ebf7; color: #123456;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = "") -> None:
    st.markdown(f"<div class='ent-hero'><h2>{title}</h2><p>{subtitle}</p></div>", unsafe_allow_html=True)


def badge(text: str) -> str:
    cls = {
        "Validée": "b-ok", "Validé": "b-ok", "Admis(e)": "b-ok", "Rendu": "b-ok", "Corrigé": "b-ok",
        "Non validée": "b-ko", "Non validé": "b-ko", "Ajourné(e)": "b-ko", "Clos": "b-ko",
        "En attente": "b-wait", "En cours": "b-wait", "À faire": "b-wait",
    }.get(text, "b-info")
    return f"<span class='badge {cls}'>{text}</span>"


def fmt_note(n) -> str:
    return "—" if n is None else f"{n:.2f}".replace(".", ",")


def is_past(date_limite: str | None) -> bool:
    if not date_limite:
        return False
    try:
        return datetime.now() > datetime.strptime(date_limite, "%Y-%m-%d %H:%M")
    except ValueError:
        return False
