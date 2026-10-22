"""Génération des documents officiels en PDF (fpdf2)."""
from __future__ import annotations

import hashlib
from datetime import date

from fpdf import FPDF

from ent.scolarite import Bilan, statut_matiere

ETABLISSEMENT = "Université FOREVER"
VILLE = "Paris"
SCOLARITE = "Service de la scolarité"

_REPLACEMENTS = {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "≥": ">=", "≤": "<=", "…": "...", "œ": "oe", "Œ": "OE"}


def _t(text) -> str:
    """Rend un texte compatible avec les polices PDF de base (latin-1)."""
    s = "" if text is None else str(text)
    for a, b in _REPLACEMENTS.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def _fr_date(d: date | None = None) -> str:
    d = d or date.today()
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"]
    return f"{d.day} {mois[d.month - 1]} {d.year}"


def _fmt_note(n) -> str:
    return "-" if n is None else f"{n:.2f}".replace(".", ",")


def _code_verif(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12].upper()


class _Doc(FPDF):
    def __init__(self, titre: str, ref: str):
        super().__init__(format="A4")
        self.titre_doc = titre
        self.ref = ref
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(18, 18, 18)
        self.add_page()

    def header(self):
        self.set_fill_color(18, 52, 86)
        self.rect(0, 0, 210, 30, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 17)
        self.set_xy(18, 8)
        self.cell(0, 8, _t(ETABLISSEMENT))
        self.set_font("Helvetica", "", 9)
        self.set_xy(18, 17)
        self.cell(0, 5, _t(f"{SCOLARITE} - {VILLE}"))
        self.set_text_color(0, 0, 0)
        self.set_y(40)

    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(110, 110, 110)
        self.cell(0, 4, _t(f"Réf. {self.ref} - Document généré le {_fr_date()} depuis l'ENT {ETABLISSEMENT}."), align="C")
        self.ln(4)
        self.cell(0, 4, _t(f"Page {self.page_no()}/{{nb}}"), align="C")

    def title_block(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(18, 52, 86)
        self.cell(0, 10, _t(self.titre_doc.upper()), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(18, 52, 86)
        self.set_line_width(0.6)
        self.line(70, self.get_y() + 1, 140, self.get_y() + 1)
        self.set_text_color(0, 0, 0)
        self.ln(9)

    def para(self, text: str, size: float = 11, style: str = "", h: float = 6.5):
        self.set_font("Helvetica", style, size)
        self.multi_cell(0, h, _t(text), new_x="LMARGIN", new_y="NEXT")

    def kv(self, label: str, value: str):
        self.set_font("Helvetica", "B", 10.5)
        self.cell(55, 6.3, _t(label))
        self.set_font("Helvetica", "", 10.5)
        self.cell(0, 6.3, _t(value), new_x="LMARGIN", new_y="NEXT")

    def signature(self, code: str):
        if self.get_y() > self.h - 22 - 50:
            self.add_page()
        self.ln(6)
        y = self.get_y()
        self.set_font("Helvetica", "", 10.5)
        self.set_x(115)
        self.multi_cell(77, 5.5, _t(f"Fait à {VILLE}, le {_fr_date()}\n\nPour le Président et par délégation,\nLe Responsable de la scolarité"), align="C")
        self.set_draw_color(18, 52, 86)
        self.set_line_width(0.4)
        self.ellipse(142, self.get_y() + 1, 22, 22)
        self.set_xy(142, self.get_y() + 10)
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(18, 52, 86)
        self.cell(22, 3, "SCOLARITE", align="C")
        self.set_text_color(0, 0, 0)
        self.set_xy(18, y + 4)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(90, 90, 90)
        self.multi_cell(85, 5, _t(f"Code de vérification : {code}\nCe document est délivré à l'intéressé(e) pour servir et valoir ce que de droit."))
        self.set_text_color(0, 0, 0)


def _identite(pdf: _Doc, user: dict):
    pdf.kv("Nom :", user["nom"].upper())
    pdf.kv("Prénom :", user["prenom"])
    pdf.kv("N° étudiant :", user.get("numero_etudiant") or "-")
    if user.get("date_naissance"):
        naiss = user["date_naissance"]
        try:
            y, m, d = map(int, naiss.split("-"))
            naiss = _fr_date(date(y, m, d))
        except ValueError:
            pass
        lieu = f" à {user['lieu_naissance']}" if user.get("lieu_naissance") else ""
        pdf.kv("Né(e) le :", f"{naiss}{lieu}")


def certificat_scolarite(user: dict) -> bytes:
    code = _code_verif("CS", user["id"], user["annee_universitaire"])
    pdf = _Doc("Certificat de scolarité", f"CS-{user['annee_universitaire']}-{user.get('numero_etudiant')}")
    pdf.alias_nb_pages()
    pdf.title_block()
    pdf.para(f"Le Responsable de la scolarité de l'{ETABLISSEMENT} certifie que :")
    pdf.ln(4)
    _identite(pdf, user)
    pdf.ln(5)
    pdf.para(
        f"est régulièrement inscrit(e) au titre de l'année universitaire {user['annee_universitaire']} "
        f"en {user['niveau']} - {user['programme_nom']}, en formation initiale, à temps plein."
    )
    pdf.ln(3)
    if user.get("date_inscription"):
        try:
            y, m, d = map(int, user["date_inscription"].split("-"))
            insc = _fr_date(date(y, m, d))
        except ValueError:
            insc = user["date_inscription"]
        pdf.para(f"Date d'inscription administrative : {insc}.", size=10)
    pdf.signature(code)
    return bytes(pdf.output())


def releve_notes(user: dict, b: Bilan) -> bytes:
    code = _code_verif("RN", user["id"], user["annee_universitaire"], b.moyenne_annuelle)
    pdf = _Doc("Relevé de notes", f"RN-{user['annee_universitaire']}-{user.get('numero_etudiant')}")
    pdf.alias_nb_pages()
    pdf.title_block()
    _identite(pdf, user)
    pdf.kv("Formation :", f"{user['niveau']} - {user['programme_nom']}")
    pdf.kv("Année universitaire :", user["annee_universitaire"])
    pdf.ln(4)

    widths = [22, 80, 15, 15, 20, 22]
    heads = ["Code", "Unité d'enseignement", "Coef.", "ECTS", "Note/20", "Résultat"]
    for sem in b.semestres:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(225, 233, 242)
        pdf.cell(sum(widths), 7.5, _t(f"Semestre {sem.numero}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(245, 247, 250)
        for w, h in zip(widths, heads):
            pdf.cell(w, 7, _t(h), border="B", fill=True, align="C" if h != "Unité d'enseignement" else "L")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for m in sem.matieres:
            vals = [m["code"], m["matiere"], f"{m['coefficient']:g}", str(m["ects"]), _fmt_note(m["note"]), statut_matiere(m["note"])]
            for i, (w, v) in enumerate(zip(widths, vals)):
                pdf.cell(w, 6, _t(v), border="B", align="L" if i == 1 else "C")
            pdf.ln()
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(widths[0] + widths[1] + widths[2], 7.5, _t(f"Moyenne du semestre {sem.numero}"), align="R")
        pdf.cell(widths[3], 7.5, _t(f"{sem.ects_acquis}/{sem.ects_total}"), align="C")
        pdf.cell(widths[4], 7.5, _t(_fmt_note(sem.moyenne)), align="C")
        pdf.cell(widths[5], 7.5, _t(sem.statut), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.set_draw_color(18, 52, 86)
    pdf.set_line_width(0.4)
    pdf.set_font("Helvetica", "B", 10.5)
    resultat = "ADMIS(E)" if b.annee_validee else ("EN COURS" if not b.complet else "AJOURNÉ(E)")
    pdf.cell(0, 8, _t(f"Moyenne annuelle : {_fmt_note(b.moyenne_annuelle)}/20   |   ECTS acquis : {b.ects_acquis}/{b.ects_total}"
                     f"   |   Résultat : {resultat}   |   Mention : {b.mention}"), border=1, align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.signature(code)
    return bytes(pdf.output())


def attestation_reussite(user: dict, b: Bilan) -> bytes:
    if not b.annee_validee:
        raise ValueError("L'année n'est pas validée : attestation de réussite indisponible.")
    code = _code_verif("AR", user["id"], user["annee_universitaire"], b.moyenne_annuelle)
    pdf = _Doc("Attestation de réussite", f"AR-{user['annee_universitaire']}-{user.get('numero_etudiant')}")
    pdf.alias_nb_pages()
    pdf.title_block()
    pdf.para(f"Le Président de l'{ETABLISSEMENT} atteste que :")
    pdf.ln(4)
    _identite(pdf, user)
    pdf.ln(5)
    pdf.para(
        f"a satisfait aux épreuves de l'année universitaire {user['annee_universitaire']} et a obtenu "
        f"le {user['niveau']} - {user['programme_nom']}, avec une moyenne générale de "
        f"{_fmt_note(b.moyenne_annuelle)}/20 et {b.ects_acquis} crédits ECTS."
    )
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, _t(f"Mention : {b.mention}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.para("La présente attestation est délivrée dans l'attente de la remise du diplôme.", size=10)
    pdf.signature(code)
    return bytes(pdf.output())


def simple_pdf(titre: str, sections: list[tuple[str, str]], auteur: str = "") -> bytes:
    """Petit PDF de cours/sujet (utilisé pour les données de démonstration)."""
    pdf = _Doc(titre, f"DOC-{_code_verif(titre)[:6]}")
    pdf.alias_nb_pages()
    pdf.title_block()
    if auteur:
        pdf.para(auteur, size=10, style="I")
        pdf.ln(3)
    for h, body in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(18, 52, 86)
        pdf.cell(0, 8, _t(h), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.para(body, size=10.5, h=6)
        pdf.ln(3)
    return bytes(pdf.output())
