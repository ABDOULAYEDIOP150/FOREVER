"""Espace étudiant."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ent import db, documents
from ent.scolarite import bilan, statut_matiere
from ent.ui import badge, fmt_note, hero, is_past

PAGES = ["🏠 Accueil", "📊 Mes notes", "📄 Mes documents", "📚 Mes cours", "📝 QCM & examens", "👤 Mon profil"]


def render(page: str, user: dict) -> None:
    {
        PAGES[0]: accueil, PAGES[1]: notes, PAGES[2]: mes_documents,
        PAGES[3]: cours, PAGES[4]: evaluations, PAGES[5]: profil,
    }[page](user)


# --------------------------------------------------------------------------- #
def accueil(user: dict) -> None:
    hero(f"Bonjour {user['prenom']} 👋", f"{user['niveau']} {user['programme_nom']} · Année {user['annee_universitaire']}")
    b = bilan(db.student_grades(user["id"]))
    evals = db.student_evaluations(user["id"])
    a_faire = [e for e in evals if e["soumission_id"] is None and not is_past(e["date_limite"])]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Moyenne générale", f"{fmt_note(b.moyenne_annuelle)} /20")
    c2.metric("Crédits ECTS", f"{b.ects_acquis} / {b.ects_total}")
    c3.metric("Résultat", "Admis(e)" if b.annee_validee else ("En cours" if not b.complet else "Ajourné(e)"))
    c4.metric("Évaluations à faire", len(a_faire))

    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        st.subheader("Dernières notes publiées")
        grades = [g for g in db.student_grades(user["id"]) if g["note"] is not None]
        grades.sort(key=lambda g: g["date_saisie"] or "", reverse=True)
        for g in grades[:5]:
            st.markdown(
                f"<div class='ent-card'><b>{g['code']} · {g['matiere']}</b><br>"
                f"Note : <b>{fmt_note(g['note'])}/20</b> &nbsp; {badge(statut_matiere(g['note']))}</div>",
                unsafe_allow_html=True,
            )
    with col_b:
        st.subheader("À faire")
        if not a_faire:
            st.success("Rien à rendre pour le moment.")
        for e in a_faire[:5]:
            kind = "Examen" if e["type"] == "examen" else "QCM"
            limite = f" · avant le {e['date_limite']}" if e["date_limite"] else ""
            st.markdown(
                f"<div class='ent-card'><b>{e['titre']}</b> {badge(kind)}<br>"
                f"<span class='ent-muted'>{e['code']} {e['matiere']}{limite}</span></div>",
                unsafe_allow_html=True,
            )
        st.subheader("Derniers cours")
        for c in db.student_courses(user["id"])[:3]:
            st.markdown(f"- **{c['titre']}** <span class='ent-muted'>({c['code']}, {c['date_publication']})</span>",
                        unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
def notes(user: dict) -> None:
    hero("Mes notes", "Notes par semestre, validation des unités d'enseignement et crédits ECTS")
    grades = db.student_grades(user["id"])
    b = bilan(grades)

    for sem in b.semestres:
        st.markdown(
            f"### Semestre {sem.numero} &nbsp; {badge(sem.statut)}", unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Moyenne du semestre", f"{fmt_note(sem.moyenne)} /20")
        c2.metric("ECTS acquis", f"{sem.ects_acquis} / {sem.ects_total}")
        c3.metric("Matières validées", f"{sum(1 for m in sem.matieres if m['note'] is not None and m['note'] >= 10)} / {len(sem.matieres)}")
        df = pd.DataFrame([
            {
                "Code": m["code"], "Matière": m["matiere"], "Enseignant": m["professeur"],
                "Coef.": m["coefficient"], "ECTS": m["ects"], "Note /20": m["note"],
                "Résultat": statut_matiere(m["note"]),
            }
            for m in sem.matieres
        ])

        def _color(v):
            return {"Validée": "color:#146c2e;font-weight:600", "Non validée": "color:#a1251b;font-weight:600",
                    "En attente": "color:#8a5a00"}.get(v, "")

        st.dataframe(
            df.style.map(_color, subset=["Résultat"]).format({"Note /20": lambda v: fmt_note(None if pd.isna(v) else v), "Coef.": "{:g}"}),
            hide_index=True, width="stretch",
        )
        if sem.complet and sem.valide and any(m["note"] < 10 for m in sem.matieres):
            st.caption("ℹ️ Semestre validé par compensation : les matières sous 10 sont compensées par la moyenne du semestre.")

    st.divider()
    st.subheader("Bilan annuel")
    c1, c2, c3 = st.columns(3)
    c1.metric("Moyenne annuelle", f"{fmt_note(b.moyenne_annuelle)} /20")
    c2.metric("Mention", b.mention)
    c3.metric("Année", "Validée ✅" if b.annee_validee else ("En cours ⏳" if not b.complet else "Non validée ❌"))

    notees = [g for g in grades if g["note"] is not None]
    if notees:
        st.markdown("**Mes notes par matière**")
        st.bar_chart(pd.DataFrame({"Matière": [g["code"] for g in notees], "Note": [g["note"] for g in notees]})
                     .set_index("Matière"), height=260)


# --------------------------------------------------------------------------- #
def mes_documents(user: dict) -> None:
    hero("Mes documents", "Certificat de scolarité, relevé de notes, attestation de réussite")
    b = bilan(db.student_grades(user["id"]))
    num = user.get("numero_etudiant", "")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='ent-card'><h4>🎓 Certificat de scolarité</h4>"
                    f"<span class='ent-muted'>Année {user['annee_universitaire']}</span></div>", unsafe_allow_html=True)
        st.download_button("Télécharger le certificat", documents.certificat_scolarite(user),
                           file_name=f"certificat_scolarite_{num}.pdf", mime="application/pdf", width="stretch")
    with c2:
        etat = "définitif" if b.complet else "provisoire"
        st.markdown(f"<div class='ent-card'><h4>📊 Relevé de notes</h4><span class='ent-muted'>Relevé {etat}</span></div>",
                    unsafe_allow_html=True)
        st.download_button("Télécharger le relevé", documents.releve_notes(user, b),
                           file_name=f"releve_notes_{num}.pdf", mime="application/pdf", width="stretch")
    with c3:
        st.markdown("<div class='ent-card'><h4>🏅 Attestation de réussite</h4>"
                    f"<span class='ent-muted'>{'Disponible' if b.annee_validee else 'Après validation de l’année'}</span></div>",
                    unsafe_allow_html=True)
        if b.annee_validee:
            st.download_button("Télécharger l'attestation", documents.attestation_reussite(user, b),
                               file_name=f"attestation_reussite_{num}.pdf", mime="application/pdf", width="stretch")
        else:
            st.button("Non disponible", disabled=True, width="stretch")
            st.caption("L'attestation est délivrée lorsque tous les semestres de l'année sont validés.")


# --------------------------------------------------------------------------- #
def cours(user: dict) -> None:
    hero("Mes cours", "Supports publiés par vos enseignants")
    courses = db.student_courses(user["id"])
    if not courses:
        st.info("Aucun cours publié pour le moment.")
        return
    matieres = sorted({f"{c['code']} · {c['matiere']}" for c in courses})
    choix = st.selectbox("Filtrer par matière", ["Toutes les matières", *matieres])
    for c in courses:
        if choix != "Toutes les matières" and choix != f"{c['code']} · {c['matiere']}":
            continue
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{c['titre']}**  \n<span class='ent-muted'>{c['code']} · {c['matiere']} · "
                          f"publié le {c['date_publication']}</span>", unsafe_allow_html=True)
            if c["description"]:
                col1.caption(c["description"])
            f = db.get_course_file(c["id"])
            col2.download_button("📥 Télécharger", f["fichier"], file_name=f["fichier_nom"], mime="application/pdf",
                                 key=f"dl_cours_{c['id']}", width="stretch")


# --------------------------------------------------------------------------- #
def evaluations(user: dict) -> None:
    hero("QCM & examens", "Entraînez-vous avec les QCM et passez vos examens en ligne")
    evals = db.student_evaluations(user["id"])
    if not evals:
        st.info("Aucune évaluation publiée.")
        return

    active = st.session_state.get("eval_en_cours")
    if active:
        _passer_qcm(user, active)
        return

    tab_qcm, tab_exam = st.tabs(["🧠 QCM d'entraînement", "📝 Examens"])
    for tab, kind in ((tab_qcm, "qcm"), (tab_exam, "examen")):
        with tab:
            items = [e for e in evals if e["type"] == kind]
            if not items:
                st.info("Rien ici pour le moment.")
            for e in items:
                _carte_evaluation(user, e)


def _carte_evaluation(user: dict, e: dict) -> None:
    rendu = e["soumission_id"] is not None
    clos = is_past(e["date_limite"]) and not rendu
    statut = "Corrigé" if rendu and e["note_sur_20"] is not None else ("Rendu" if rendu else ("Clos" if clos else "À faire"))
    with st.container(border=True):
        st.markdown(
            f"**{e['titre']}** &nbsp; {badge(statut)} &nbsp; {badge('Format PDF' if e['format'] == 'pdf' else 'Format QCM')}"
            + (f" &nbsp; {badge('Compte dans la moyenne')}" if e["compte_dans_moyenne"] else ""),
            unsafe_allow_html=True,
        )
        infos = [f"{e['code']} · {e['matiere']}"]
        if e["duree_minutes"]:
            infos.append(f"durée {e['duree_minutes']} min")
        if e["date_limite"]:
            infos.append(f"à rendre avant le {e['date_limite']}")
        st.caption(" · ".join(infos))
        if e["consignes"]:
            st.write(e["consignes"])

        if rendu:
            if e["note_sur_20"] is not None:
                st.success(f"Note : **{fmt_note(e['note_sur_20'])}/20**" + (f" — {e['score']:g} bonne(s) réponse(s)" if e["score"] is not None else ""))
            else:
                st.info(f"Copie déposée le {e['date_soumission']} — en attente de correction.")
            if e["commentaire"]:
                st.write(f"💬 Commentaire de l'enseignant : {e['commentaire']}")
            if e["format"] == "qcm" and e["type"] == "qcm":
                with st.expander("Voir la correction"):
                    _correction(e["id"], user["id"])
            if e["format"] == "pdf" and e["note_sur_20"] is None and not is_past(e["date_limite"]):
                _depot_copie(user, e, label="Remplacer ma copie")
            return

        if clos:
            st.warning("La date limite est dépassée.")
            return

        if e["format"] == "qcm":
            if st.button("▶️ Commencer", key=f"start_{e['id']}"):
                st.session_state["eval_en_cours"] = e["id"]
                st.rerun()
        else:
            ev = db.get_evaluation(e["id"])
            st.download_button("📥 Télécharger le sujet", ev["sujet"], file_name=ev["sujet_nom"], mime="application/pdf",
                               key=f"sujet_{e['id']}")
            _depot_copie(user, e)


def _depot_copie(user: dict, e: dict, label: str = "Déposer ma copie") -> None:
    up = st.file_uploader(f"{label} (PDF)", type=["pdf"], key=f"up_{e['id']}")
    if up is not None and st.button("📤 Envoyer", key=f"send_{e['id']}"):
        db.submit_pdf_copy(e["id"], user["id"], up.name, up.getvalue())
        st.success("Copie déposée.")
        st.rerun()


def _passer_qcm(user: dict, eval_id: int) -> None:
    ev = db.get_evaluation(eval_id)
    st.subheader(f"{'Examen' if ev['type'] == 'examen' else 'QCM'} · {ev['titre']}")
    if ev["consignes"]:
        st.info(ev["consignes"])
    if ev["duree_minutes"]:
        st.caption(f"⏱️ Durée indicative : {ev['duree_minutes']} minutes")
    with st.form(f"qcm_{eval_id}"):
        reponses: dict[int, list[int]] = {}
        for i, q in enumerate(ev["questions"]):
            st.markdown(f"**Question {i + 1}.** {q['question']}")
            multi = len(q["correctes"]) > 1
            if multi:
                st.caption("Plusieurs réponses attendues")
                reponses[i] = [j for j, c in enumerate(q["choix"]) if st.checkbox(c, key=f"q{eval_id}_{i}_{j}")]
            else:
                r = st.radio("Réponse", q["choix"], index=None, key=f"q{eval_id}_{i}", label_visibility="collapsed")
                reponses[i] = [q["choix"].index(r)] if r is not None else []
            st.write("")
        c1, c2 = st.columns(2)
        valider = c1.form_submit_button("✅ Valider mes réponses", type="primary", width="stretch")
        annuler = c2.form_submit_button("Annuler", width="stretch")
    if annuler:
        st.session_state.pop("eval_en_cours", None)
        st.rerun()
    if valider:
        score, note = db.submit_qcm(eval_id, user["id"], reponses)
        st.session_state.pop("eval_en_cours", None)
        st.session_state["flash"] = f"Réponses enregistrées : {score:g}/{len(ev['questions'])} — note {fmt_note(note)}/20"
        st.rerun()


def _correction(eval_id: int, student_id: int) -> None:
    import json

    ev = db.get_evaluation(eval_id)
    sub = db.query_one("SELECT reponses_json FROM soumissions WHERE evaluation_id = ? AND etudiant_id = ?", (eval_id, student_id))
    mes = json.loads(sub["reponses_json"]) if sub and sub["reponses_json"] else {}
    for i, q in enumerate(ev["questions"]):
        mine = mes.get(str(i), [])
        ok = sorted(mine) == sorted(q["correctes"])
        st.markdown(f"{'✅' if ok else '❌'} **{q['question']}**")
        for j, c in enumerate(q["choix"]):
            mark = "🟢" if j in q["correctes"] else "⚪"
            moi = " ← votre réponse" if j in mine else ""
            st.markdown(f"&nbsp;&nbsp;{mark} {c}{moi}", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
def profil(user: dict) -> None:
    hero("Mon profil", "Informations administratives")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
| | |
|---|---|
| **Nom** | {user['nom'].upper()} |
| **Prénom** | {user['prenom']} |
| **N° étudiant** | {user.get('numero_etudiant') or '—'} |
| **E-mail** | {user.get('email') or '—'} |
| **Formation** | {user['niveau']} {user['programme_nom']} |
| **Année** | {user['annee_universitaire']} |
""")
    with c2:
        _changer_mdp(user)


def _changer_mdp(user: dict) -> None:
    with st.form("mdp"):
        st.markdown("**Changer mon mot de passe**")
        old = st.text_input("Mot de passe actuel", type="password")
        new = st.text_input("Nouveau mot de passe", type="password")
        new2 = st.text_input("Confirmer", type="password")
        if st.form_submit_button("Mettre à jour"):
            if not db.authenticate(user["username"], old):
                st.error("Mot de passe actuel incorrect.")
            elif len(new) < 6 or new != new2:
                st.error("Le nouveau mot de passe doit faire au moins 6 caractères et être confirmé.")
            else:
                db.change_password(user["id"], new)
                st.success("Mot de passe modifié.")


changer_mdp = _changer_mdp
