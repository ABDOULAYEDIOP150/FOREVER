"""Tests de l'ENT : règles de scolarité, documents PDF et parcours dans l'interface (AppTest)."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True, scope="session")
def _tmp_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["ENT_DB_PATH"] = str(path)
    from ent import db
    db.DB_PATH = path
    db.init_db(seed=True)
    yield


def _uid(username):
    from ent import db
    return db.query_one("SELECT id FROM users WHERE username = ?", (username,))["id"]


# --------------------------------------------------------------------------- #
def test_regles_validation():
    from ent.scolarite import bilan, mention

    g = [
        {"semestre": 1, "note": 8.0, "coefficient": 1, "ects": 6},
        {"semestre": 1, "note": 14.0, "coefficient": 1, "ects": 6},
        {"semestre": 2, "note": 12.0, "coefficient": 1, "ects": 6},
        {"semestre": 2, "note": None, "coefficient": 1, "ects": 6},
    ]
    b = bilan(g)
    s1, s2 = b.semestres
    assert s1.moyenne == 11.0 and s1.valide and s1.ects_acquis == 12  # compensation
    assert not s2.complet and s2.statut == "En cours" and s2.ects_acquis == 6
    assert not b.annee_validee
    assert mention(16.2) == "Très bien" and mention(9.9) == "—"


def test_documents_pdf():
    from ent import db, documents
    from ent.scolarite import bilan

    u = db.get_user(_uid("m.sarr"))
    b = bilan(db.student_grades(u["id"]))
    assert b.annee_validee
    for pdf in (documents.certificat_scolarite(u), documents.releve_notes(u, b), documents.attestation_reussite(u, b)):
        assert pdf[:4] == b"%PDF" and len(pdf) > 1500

    ajourne = db.get_user(_uid("l.leroy"))
    with pytest.raises(ValueError):
        documents.attestation_reussite(ajourne, bilan(db.student_grades(ajourne["id"])))


def test_qcm_correction_et_report_de_note():
    from ent import db

    etu = _uid("c.dupont")
    exam = db.query_one("SELECT id, matiere_id FROM evaluations WHERE titre LIKE 'Examen QCM%'")
    score, note = db.submit_qcm(exam["id"], etu, {0: [1], 1: [0, 1], 2: [0]})  # 2 bonnes sur 3
    assert score == 2 and note == pytest.approx(13.33)
    reported = db.query_one("SELECT note FROM notes WHERE etudiant_id = ? AND matiere_id = ?", (etu, exam["matiere_id"]))
    assert reported["note"] == pytest.approx(13.33)


# --------------------------------------------------------------------------- #
def _app():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)


def _login(at, username, password):
    at.run()
    at.text_input[0].input(username)
    at.text_input[1].input(password)
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def test_login_refuse():
    at = _app()
    at.run()
    at.text_input[0].input("m.sarr")
    at.text_input[1].input("mauvais")
    at.button[0].click().run()
    assert any("incorrect" in e.value for e in at.error)


@pytest.mark.parametrize("username,password,module", [
    ("m.sarr", "etudiant", "views_etudiant"),
    ("m.martin", "professeur", "views_prof"),
])
def test_toutes_les_pages(username, password, module):
    import importlib

    pages = importlib.import_module(f"ent.{module}").PAGES
    at = _login(_app(), username, password)
    for page in pages:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, (page, at.exception)


def test_etudiant_passe_un_qcm():
    at = _login(_app(), "a.fall", "etudiant")
    at.sidebar.radio[0].set_value("📝 QCM & examens").run()
    start = [b for b in at.button if b.label == "▶️ Commencer"][0]
    start.click().run()
    assert at.session_state["eval_en_cours"]
    for r in at.main.radio:
        r.set_value(r.options[0])
    [b for b in at.button if "Valider" in b.label][0].click().run()
    assert not at.exception
    assert "eval_en_cours" not in at.session_state


def test_prof_cree_un_qcm():
    from ent import db

    before = len(db.query("SELECT id FROM evaluations"))
    at = _login(_app(), "m.martin", "professeur")
    at.sidebar.radio[0].set_value("🧠 Créer un QCM / examen").run()
    at.text_input(key="ev_titre").input("QCM test automatique")
    at.number_input[1].set_value(1).run()
    at.text_input(key="q_txt_0").input("2 + 2 = ?")
    at.text_area(key="q_ch_0").input("3\n4\n5").run()
    at.multiselect(key="q_ok_0").set_value(["4"]).run()
    [b for b in at.button if "Publier" in b.label][0].click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    assert len(db.query("SELECT id FROM evaluations")) == before + 1
