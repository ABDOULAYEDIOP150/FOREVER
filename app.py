"""FOREVER — Espace Numérique de Travail (ENT) universitaire.

Lancer en local :  streamlit run app.py
"""
import streamlit as st

from ent import db, views_etudiant, views_prof
from ent.seed import MDP_ETUDIANT, MDP_PROFESSEUR
from ent.ui import hero, inject_css

st.set_page_config(page_title="FOREVER · ENT", page_icon="🎓", layout="wide")
inject_css()


@st.cache_resource
def _init() -> bool:
    db.init_db(seed=True)
    return True


_init()


def login_page() -> None:
    hero("🎓 FOREVER · Espace Numérique de Travail", "Université FOREVER — portail étudiants et enseignants")
    col, info = st.columns([1, 1])
    with col:
        with st.form("login"):
            st.subheader("Connexion")
            username = st.text_input("Identifiant", placeholder="ex. m.sarr")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter", type="primary", width="stretch"):
                user = db.authenticate(username, password)
                if user:
                    st.session_state["user_id"] = user["id"]
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")
    with info:
        st.markdown("#### Comptes de démonstration")
        st.markdown(f"""
| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Étudiant (année validée) | `m.sarr` | `{MDP_ETUDIANT}` |
| Étudiant (année en cours) | `c.dupont` | `{MDP_ETUDIANT}` |
| Étudiant (ajourné) | `l.leroy` | `{MDP_ETUDIANT}` |
| Professeur | `m.martin` | `{MDP_PROFESSEUR}` |
| Professeur | `j.durand` | `{MDP_PROFESSEUR}` |
""")
        st.caption("Autres étudiants : a.fall, t.bernard · Autre professeur : f.ndiaye")


def main() -> None:
    user_id = st.session_state.get("user_id")
    user = db.get_user(user_id) if user_id else None
    if not user:
        login_page()
        return

    module = views_etudiant if user["role"] == "etudiant" else views_prof
    with st.sidebar:
        st.markdown("## 🎓 FOREVER")
        st.markdown(f"**{user['prenom']} {user['nom']}**  \n"
                    f"{'Étudiant(e) · ' + user['programme_code'] if user['role'] == 'etudiant' else 'Enseignant(e)'}")
        st.divider()
        page = st.radio("Navigation", module.PAGES, label_visibility="collapsed", key=f"nav_{user['role']}")
        st.divider()
        if st.button("🚪 Se déconnecter", width="stretch"):
            st.session_state.clear()
            st.rerun()

    flash = st.session_state.pop("flash", None)
    if flash:
        st.toast(flash, icon="✅")
        st.success(flash)
    module.render(page, user)


main()
