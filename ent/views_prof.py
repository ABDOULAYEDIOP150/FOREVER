"""Espace professeur."""
from __future__ import annotations

from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st

from ent import db
from ent.ui import badge, fmt_note, hero
from ent.views_etudiant import changer_mdp

PAGES = ["🏠 Accueil", "📚 Publier un cours", "🧠 Créer un QCM / examen", "✏️ Saisie des notes",
         "📥 Résultats & copies", "👤 Mon profil"]


def render(page: str, user: dict) -> None:
    {
        PAGES[0]: accueil, PAGES[1]: publier_cours, PAGES[2]: creer_evaluation,
        PAGES[3]: saisie_notes, PAGES[4]: resultats, PAGES[5]: profil,
    }[page](user)


def _choix_matiere(user: dict, key: str) -> dict | None:
    mats = db.teacher_subjects(user["id"])
    if not mats:
        st.warning("Aucune matière ne vous est attribuée.")
        return None
    labels = {f"{m['code']} · {m['nom']} (S{m['semestre']})": m for m in mats}
    return labels[st.selectbox("Matière", list(labels), key=key)]


# --------------------------------------------------------------------------- #
def accueil(user: dict) -> None:
    hero(f"Bonjour Pr. {user['nom']} 👋", "Gérez vos cours, vos évaluations et vos notes")
    mats = db.teacher_subjects(user["id"])
    evals = db.teacher_evaluations(user["id"])
    a_corriger = db.query(
        """SELECT COUNT(*) AS n FROM soumissions s JOIN evaluations e ON e.id = s.evaluation_id
           JOIN matieres m ON m.id = e.matiere_id WHERE m.professeur_id = ? AND s.note_sur_20 IS NULL""",
        (user["id"],),
    )[0]["n"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matières", len(mats))
    c2.metric("Cours publiés", len(db.teacher_courses(user["id"])))
    c3.metric("Évaluations", len(evals))
    c4.metric("Copies à corriger", a_corriger)

    st.subheader("Mes matières")
    rows = []
    for m in mats:
        g = db.subject_students_with_grades(m["id"])
        notes = [x["note"] for x in g if x["note"] is not None]
        rows.append({
            "Code": m["code"], "Matière": m["nom"], "Semestre": m["semestre"], "Étudiants": m["nb_etudiants"],
            "Notes saisies": f"{len(notes)}/{len(g)}",
            "Moyenne": round(sum(notes) / len(notes), 2) if notes else None,
            "Taux de réussite": f"{round(100 * sum(n >= 10 for n in notes) / len(notes))} %" if notes else "—",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


# --------------------------------------------------------------------------- #
def publier_cours(user: dict) -> None:
    hero("Publier un cours", "Mettez en ligne vos supports au format PDF")
    with st.form("cours", clear_on_submit=True):
        mat = _choix_matiere(user, "cours_mat")
        titre = st.text_input("Titre du cours *")
        desc = st.text_area("Description", height=80)
        fichier = st.file_uploader("Support (PDF) *", type=["pdf"])
        ok = st.form_submit_button("📤 Publier", type="primary")
    if ok:
        if not (mat and titre.strip() and fichier):
            st.error("Le titre et le fichier PDF sont obligatoires.")
        else:
            db.add_course(mat["id"], titre.strip(), desc.strip(), fichier.name, fichier.getvalue())
            st.success(f"Cours « {titre} » publié pour {mat['code']}.")

    st.subheader("Mes cours publiés")
    courses = db.teacher_courses(user["id"])
    if not courses:
        st.info("Aucun cours publié.")
    for c in courses:
        col1, col2 = st.columns([5, 1])
        col1.markdown(f"**{c['titre']}** <span class='ent-muted'>· {c['code']} · {c['fichier_nom']} · {c['date_publication']}</span>",
                      unsafe_allow_html=True)
        if col2.button("🗑️ Supprimer", key=f"del_c_{c['id']}"):
            db.delete_course(c["id"])
            st.rerun()


# --------------------------------------------------------------------------- #
def creer_evaluation(user: dict) -> None:
    hero("Créer un QCM ou un examen", "QCM corrigés automatiquement ou sujet PDF avec dépôt de copies")
    mat = _choix_matiere(user, "eval_mat")
    if not mat:
        return
    c1, c2 = st.columns(2)
    type_label = c1.radio("Type", ["QCM d'entraînement", "Examen"], horizontal=True)
    type_ = "qcm" if type_label.startswith("QCM") else "examen"
    if type_ == "examen":
        format_label = c2.radio("Format de l'examen", ["QCM en ligne", "Sujet PDF + dépôt de copie"], horizontal=True)
        format_ = "qcm" if format_label.startswith("QCM") else "pdf"
    else:
        format_ = "qcm"

    titre = st.text_input("Titre *", key="ev_titre")
    consignes = st.text_area("Consignes", key="ev_consignes", height=70)
    c1, c2, c3 = st.columns(3)
    duree = c1.number_input("Durée (minutes)", min_value=0, max_value=600, value=30 if type_ == "examen" else 10, step=5)
    date_limite = None
    compte = False
    if type_ == "examen":
        d = c2.date_input("Date limite", value=datetime.now().date() + timedelta(days=14), format="DD/MM/YYYY")
        h = c3.time_input("Heure limite", value=time(23, 59))
        date_limite = datetime.combine(d, h).strftime("%Y-%m-%d %H:%M")
        compte = st.checkbox("Reporter automatiquement la note dans la matière", value=True)

    questions = None
    sujet = None
    if format_ == "qcm":
        st.markdown("#### Questions")
        n = st.number_input("Nombre de questions", min_value=1, max_value=40, value=3)
        questions = []
        for i in range(int(n)):
            with st.container(border=True):
                q = st.text_input(f"Question {i + 1}", key=f"q_txt_{i}")
                choix_txt = st.text_area("Choix (un par ligne)", key=f"q_ch_{i}", height=90,
                                         placeholder="Réponse A\nRéponse B\nRéponse C")
                choix = [c.strip() for c in choix_txt.splitlines() if c.strip()]
                bonnes = st.multiselect("Bonne(s) réponse(s)", choix, key=f"q_ok_{i}")
                questions.append({"question": q.strip(), "choix": choix, "correctes": [choix.index(b) for b in bonnes]})
    else:
        sujet = st.file_uploader("Sujet de l'examen (PDF) *", type=["pdf"])

    if st.button("🚀 Publier l'évaluation", type="primary"):
        erreurs = []
        if not titre.strip():
            erreurs.append("Le titre est obligatoire.")
        if format_ == "qcm":
            for i, q in enumerate(questions):
                if not q["question"] or len(q["choix"]) < 2 or not q["correctes"]:
                    erreurs.append(f"Question {i + 1} : énoncé, au moins 2 choix et au moins une bonne réponse requis.")
        elif sujet is None:
            erreurs.append("Le sujet PDF est obligatoire.")
        if erreurs:
            for e in erreurs:
                st.error(e)
            return
        db.add_evaluation(
            mat["id"], titre.strip(), consignes.strip(), type_, format_, questions=questions,
            sujet_nom=sujet.name if sujet else None, sujet=sujet.getvalue() if sujet else None,
            duree_minutes=int(duree) or None, date_limite=date_limite, compte_dans_moyenne=compte,
        )
        for k in list(st.session_state):
            if k.startswith(("q_txt_", "q_ch_", "q_ok_", "ev_")):
                del st.session_state[k]
        st.session_state["flash"] = f"« {titre} » publié pour les étudiants de {mat['code']}."
        st.rerun()


# --------------------------------------------------------------------------- #
def saisie_notes(user: dict) -> None:
    hero("Saisie des notes", "Saisissez ou modifiez les notes de vos étudiants (sur 20)")
    mat = _choix_matiere(user, "notes_mat")
    if not mat:
        return
    rows = db.subject_students_with_grades(mat["id"])
    df = pd.DataFrame([{"id": r["id"], "N° étudiant": r["numero_etudiant"], "Nom": r["nom"].upper(),
                        "Prénom": r["prenom"], "Note /20": r["note"]} for r in rows])
    edited = st.data_editor(
        df, hide_index=True, width="stretch", key=f"editor_{mat['id']}",
        column_config={
            "id": None,
            "Note /20": st.column_config.NumberColumn(min_value=0.0, max_value=20.0, step=0.25, format="%.2f"),
        },
        disabled=["N° étudiant", "Nom", "Prénom"],
    )
    session = st.selectbox("Session", ["Session 1", "Session 2 (rattrapage)"])
    if st.button("💾 Enregistrer les notes", type="primary"):
        grades = {int(r["id"]): (None if pd.isna(r["Note /20"]) else float(r["Note /20"])) for _, r in edited.iterrows()}
        n = db.save_grades(mat["id"], grades, session.split(" (")[0])
        st.success(f"{n} note(s) enregistrée(s) pour {mat['code']}.")

    notes = [n for n in edited["Note /20"].tolist() if not pd.isna(n)]
    if notes:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Moyenne", fmt_note(sum(notes) / len(notes)))
        c2.metric("Min", fmt_note(min(notes)))
        c3.metric("Max", fmt_note(max(notes)))
        c4.metric("Réussite", f"{round(100 * sum(n >= 10 for n in notes) / len(notes))} %")


# --------------------------------------------------------------------------- #
def resultats(user: dict) -> None:
    hero("Résultats & copies", "Suivez les QCM et corrigez les copies d'examens")
    evals = db.teacher_evaluations(user["id"])
    if not evals:
        st.info("Aucune évaluation publiée.")
        return
    overview = pd.DataFrame([{
        "Titre": e["titre"], "Matière": e["code"], "Type": "Examen" if e["type"] == "examen" else "QCM",
        "Format": e["format"].upper(), "Rendus": e["nb_soumissions"], "Moyenne": e["moyenne"],
        "Date limite": e["date_limite"] or "—",
    } for e in evals])
    st.dataframe(overview, hide_index=True, width="stretch")

    labels = {f"{e['code']} · {e['titre']}": e for e in evals}
    e = labels[st.selectbox("Détail de l'évaluation", list(labels))]
    subs = db.evaluation_submissions(e["id"])
    st.markdown(f"**{len(subs)}** rendu(s) {badge('Compte dans la moyenne') if e['compte_dans_moyenne'] else ''}",
                unsafe_allow_html=True)

    if e["format"] == "qcm":
        if subs:
            st.dataframe(pd.DataFrame([{"N° étudiant": s["numero_etudiant"], "Nom": f"{s['nom'].upper()} {s['prenom']}",
                                        "Bonnes réponses": s["score"], "Note /20": s["note_sur_20"],
                                        "Rendu le": s["date_soumission"]} for s in subs]),
                         hide_index=True, width="stretch")
    else:
        for s in subs:
            with st.container(border=True):
                c1, c2 = st.columns([2, 3])
                c1.markdown(f"**{s['nom'].upper()} {s['prenom']}** ({s['numero_etudiant']})  \nDéposée le {s['date_soumission']}")
                copie = db.get_submission_copy(s["id"])
                c1.download_button("📥 Copie", copie["copie"], file_name=copie["copie_nom"], mime="application/pdf",
                                   key=f"cp_{s['id']}")
                with c2.form(f"corr_{s['id']}"):
                    note = st.number_input("Note /20", 0.0, 20.0, value=float(s["note_sur_20"] or 0), step=0.25)
                    com = st.text_input("Commentaire", value=s["commentaire"] or "")
                    if st.form_submit_button("Enregistrer la correction"):
                        db.grade_submission(s["id"], note, com)
                        st.session_state["flash"] = f"Correction enregistrée pour {s['prenom']} {s['nom']}."
                        st.rerun()

    with st.expander("⚠️ Supprimer cette évaluation"):
        if st.button("Supprimer définitivement", key=f"del_e_{e['id']}"):
            db.delete_evaluation(e["id"])
            st.rerun()


# --------------------------------------------------------------------------- #
def profil(user: dict) -> None:
    hero("Mon profil", user.get("email") or "")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{user['prenom']} {user['nom']}**  \nEnseignant(e)")
        for m in db.teacher_subjects(user["id"]):
            st.markdown(f"- {m['code']} · {m['nom']} (S{m['semestre']}, {m['programme_code']})")
    with c2:
        changer_mdp(user)
