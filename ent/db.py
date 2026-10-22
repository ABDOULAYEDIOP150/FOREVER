"""Couche d'accès aux données de l'ENT FOREVER (SQLite)."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("ENT_DB_PATH", Path(__file__).resolve().parent.parent / "data" / "ent.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS programmes (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    niveau TEXT NOT NULL,
    annee_universitaire TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('etudiant', 'professeur', 'admin')),
    prenom TEXT NOT NULL,
    nom TEXT NOT NULL,
    email TEXT,
    numero_etudiant TEXT,
    date_naissance TEXT,
    lieu_naissance TEXT,
    programme_id INTEGER REFERENCES programmes(id),
    date_inscription TEXT
);

CREATE TABLE IF NOT EXISTS matieres (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    semestre INTEGER NOT NULL,
    ects INTEGER NOT NULL,
    coefficient REAL NOT NULL DEFAULT 1,
    programme_id INTEGER NOT NULL REFERENCES programmes(id),
    professeur_id INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    etudiant_id INTEGER NOT NULL REFERENCES users(id),
    matiere_id INTEGER NOT NULL REFERENCES matieres(id),
    note REAL NOT NULL CHECK (note >= 0 AND note <= 20),
    session TEXT NOT NULL DEFAULT 'Session 1',
    date_saisie TEXT NOT NULL,
    UNIQUE (etudiant_id, matiere_id)
);

CREATE TABLE IF NOT EXISTS cours (
    id INTEGER PRIMARY KEY,
    matiere_id INTEGER NOT NULL REFERENCES matieres(id),
    titre TEXT NOT NULL,
    description TEXT,
    fichier_nom TEXT NOT NULL,
    fichier BLOB NOT NULL,
    date_publication TEXT NOT NULL
);

-- Évaluations : QCM d'entraînement ou examens (format QCM ou PDF)
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY,
    matiere_id INTEGER NOT NULL REFERENCES matieres(id),
    titre TEXT NOT NULL,
    consignes TEXT,
    type TEXT NOT NULL CHECK (type IN ('qcm', 'examen')),
    format TEXT NOT NULL CHECK (format IN ('qcm', 'pdf')),
    questions_json TEXT,
    sujet_nom TEXT,
    sujet BLOB,
    duree_minutes INTEGER,
    date_limite TEXT,
    compte_dans_moyenne INTEGER NOT NULL DEFAULT 0,
    date_publication TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS soumissions (
    id INTEGER PRIMARY KEY,
    evaluation_id INTEGER NOT NULL REFERENCES evaluations(id),
    etudiant_id INTEGER NOT NULL REFERENCES users(id),
    reponses_json TEXT,
    copie_nom TEXT,
    copie BLOB,
    score REAL,
    note_sur_20 REAL,
    commentaire TEXT,
    date_soumission TEXT NOT NULL,
    UNIQUE (evaluation_id, etudiant_id)
);
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Authentification
# --------------------------------------------------------------------------- #
def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return digest.hex(), salt


def authenticate(username: str, password: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    if not row:
        return None
    digest, _ = hash_password(password, row["salt"])
    if secrets.compare_digest(digest, row["password_hash"]):
        return dict(row)
    return None


def create_user(username, password, role, prenom, nom, **extra) -> int:
    digest, salt = hash_password(password)
    cols = ["username", "password_hash", "salt", "role", "prenom", "nom", *extra.keys()]
    vals = [username.lower(), digest, salt, role, prenom, nom, *extra.values()]
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO users ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals
        )
        return cur.lastrowid


def change_password(user_id: int, new_password: str) -> None:
    digest, salt = hash_password(new_password)
    with get_conn() as conn:
        conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (digest, salt, user_id))


# --------------------------------------------------------------------------- #
# Lectures génériques
# --------------------------------------------------------------------------- #
def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def get_user(user_id: int) -> dict | None:
    return query_one(
        """SELECT u.*, p.nom AS programme_nom, p.niveau, p.annee_universitaire, p.code AS programme_code
           FROM users u LEFT JOIN programmes p ON p.id = u.programme_id WHERE u.id = ?""",
        (user_id,),
    )


# --------------------------------------------------------------------------- #
# Étudiant
# --------------------------------------------------------------------------- #
def student_grades(student_id: int) -> list[dict]:
    """Toutes les matières du programme de l'étudiant, avec la note si elle existe."""
    return query(
        """SELECT m.id AS matiere_id, m.code, m.nom AS matiere, m.semestre, m.ects, m.coefficient,
                  n.note, n.session, n.date_saisie,
                  pr.prenom || ' ' || pr.nom AS professeur
           FROM users u
           JOIN matieres m ON m.programme_id = u.programme_id
           LEFT JOIN notes n ON n.matiere_id = m.id AND n.etudiant_id = u.id
           LEFT JOIN users pr ON pr.id = m.professeur_id
           WHERE u.id = ?
           ORDER BY m.semestre, m.code""",
        (student_id,),
    )


def student_courses(student_id: int) -> list[dict]:
    return query(
        """SELECT c.id, c.titre, c.description, c.fichier_nom, c.date_publication,
                  m.code, m.nom AS matiere, m.semestre
           FROM cours c JOIN matieres m ON m.id = c.matiere_id
           JOIN users u ON u.programme_id = m.programme_id
           WHERE u.id = ? ORDER BY c.date_publication DESC""",
        (student_id,),
    )


def student_evaluations(student_id: int) -> list[dict]:
    return query(
        """SELECT e.id, e.titre, e.consignes, e.type, e.format, e.duree_minutes, e.date_limite,
                  e.compte_dans_moyenne, e.date_publication, e.sujet_nom,
                  m.code, m.nom AS matiere,
                  s.id AS soumission_id, s.note_sur_20, s.score, s.commentaire, s.date_soumission
           FROM evaluations e JOIN matieres m ON m.id = e.matiere_id
           JOIN users u ON u.programme_id = m.programme_id
           LEFT JOIN soumissions s ON s.evaluation_id = e.id AND s.etudiant_id = u.id
           WHERE u.id = ? ORDER BY e.date_publication DESC""",
        (student_id,),
    )


def get_course_file(course_id: int) -> dict | None:
    return query_one("SELECT fichier_nom, fichier FROM cours WHERE id = ?", (course_id,))


def get_evaluation(eval_id: int) -> dict | None:
    row = query_one("SELECT * FROM evaluations WHERE id = ?", (eval_id,))
    if row and row.get("questions_json"):
        row["questions"] = json.loads(row["questions_json"])
    return row


def submit_qcm(eval_id: int, student_id: int, answers: dict[int, list[int]]) -> tuple[float, float]:
    """Corrige un QCM. Une question vaut 1 point si l'ensemble des bonnes réponses est exactement coché."""
    ev = get_evaluation(eval_id)
    questions = ev["questions"]
    score = 0.0
    for i, q in enumerate(questions):
        if sorted(answers.get(i, [])) == sorted(q["correctes"]):
            score += 1
    note20 = round(score / len(questions) * 20, 2) if questions else 0.0
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO soumissions (evaluation_id, etudiant_id, reponses_json, score, note_sur_20, date_soumission)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (eval_id, student_id, json.dumps({str(k): v for k, v in answers.items()}), score, note20, _now()),
        )
        if ev["compte_dans_moyenne"]:
            _upsert_grade(conn, student_id, ev["matiere_id"], note20)
    return score, note20


def submit_pdf_copy(eval_id: int, student_id: int, filename: str, data: bytes) -> None:
    execute(
        """INSERT INTO soumissions (evaluation_id, etudiant_id, copie_nom, copie, date_soumission)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(evaluation_id, etudiant_id) DO UPDATE SET
             copie_nom = excluded.copie_nom, copie = excluded.copie, date_soumission = excluded.date_soumission""",
        (eval_id, student_id, filename, data, _now()),
    )


# --------------------------------------------------------------------------- #
# Professeur
# --------------------------------------------------------------------------- #
def teacher_subjects(teacher_id: int) -> list[dict]:
    return query(
        """SELECT m.*, p.nom AS programme, p.code AS programme_code,
                  (SELECT COUNT(*) FROM users u WHERE u.programme_id = m.programme_id AND u.role='etudiant') AS nb_etudiants
           FROM matieres m JOIN programmes p ON p.id = m.programme_id
           WHERE m.professeur_id = ? ORDER BY m.semestre, m.code""",
        (teacher_id,),
    )


def subject_students_with_grades(matiere_id: int) -> list[dict]:
    return query(
        """SELECT u.id, u.numero_etudiant, u.nom, u.prenom, n.note
           FROM matieres m JOIN users u ON u.programme_id = m.programme_id AND u.role = 'etudiant'
           LEFT JOIN notes n ON n.etudiant_id = u.id AND n.matiere_id = m.id
           WHERE m.id = ? ORDER BY u.nom, u.prenom""",
        (matiere_id,),
    )


def _upsert_grade(conn, student_id: int, matiere_id: int, note: float, session: str = "Session 1") -> None:
    conn.execute(
        """INSERT INTO notes (etudiant_id, matiere_id, note, session, date_saisie) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(etudiant_id, matiere_id) DO UPDATE SET
             note = excluded.note, session = excluded.session, date_saisie = excluded.date_saisie""",
        (student_id, matiere_id, note, session, _now()),
    )


def save_grades(matiere_id: int, grades: dict[int, float | None], session: str = "Session 1") -> int:
    n = 0
    with get_conn() as conn:
        for student_id, note in grades.items():
            if note is None:
                conn.execute("DELETE FROM notes WHERE etudiant_id = ? AND matiere_id = ?", (student_id, matiere_id))
            else:
                _upsert_grade(conn, student_id, matiere_id, float(note), session)
                n += 1
    return n


def add_course(matiere_id, titre, description, fichier_nom, fichier: bytes) -> int:
    return execute(
        """INSERT INTO cours (matiere_id, titre, description, fichier_nom, fichier, date_publication)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (matiere_id, titre, description, fichier_nom, fichier, _now()),
    )


def teacher_courses(teacher_id: int) -> list[dict]:
    return query(
        """SELECT c.id, c.titre, c.fichier_nom, c.date_publication, m.code, m.nom AS matiere
           FROM cours c JOIN matieres m ON m.id = c.matiere_id
           WHERE m.professeur_id = ? ORDER BY c.date_publication DESC""",
        (teacher_id,),
    )


def delete_course(course_id: int) -> None:
    execute("DELETE FROM cours WHERE id = ?", (course_id,))


def add_evaluation(matiere_id, titre, consignes, type_, format_, questions=None, sujet_nom=None, sujet=None,
                   duree_minutes=None, date_limite=None, compte_dans_moyenne=False) -> int:
    return execute(
        """INSERT INTO evaluations (matiere_id, titre, consignes, type, format, questions_json, sujet_nom, sujet,
                                    duree_minutes, date_limite, compte_dans_moyenne, date_publication)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (matiere_id, titre, consignes, type_, format_, json.dumps(questions, ensure_ascii=False) if questions else None,
         sujet_nom, sujet, duree_minutes, date_limite, int(bool(compte_dans_moyenne)), _now()),
    )


def teacher_evaluations(teacher_id: int) -> list[dict]:
    return query(
        """SELECT e.id, e.titre, e.type, e.format, e.date_limite, e.compte_dans_moyenne, e.date_publication,
                  m.id AS matiere_id, m.code, m.nom AS matiere,
                  (SELECT COUNT(*) FROM soumissions s WHERE s.evaluation_id = e.id) AS nb_soumissions,
                  (SELECT ROUND(AVG(note_sur_20), 2) FROM soumissions s WHERE s.evaluation_id = e.id) AS moyenne
           FROM evaluations e JOIN matieres m ON m.id = e.matiere_id
           WHERE m.professeur_id = ? ORDER BY e.date_publication DESC""",
        (teacher_id,),
    )


def delete_evaluation(eval_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM soumissions WHERE evaluation_id = ?", (eval_id,))
        conn.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))


def evaluation_submissions(eval_id: int) -> list[dict]:
    return query(
        """SELECT s.id, s.etudiant_id, u.numero_etudiant, u.nom, u.prenom, s.score, s.note_sur_20,
                  s.copie_nom, s.commentaire, s.date_soumission
           FROM soumissions s JOIN users u ON u.id = s.etudiant_id
           WHERE s.evaluation_id = ? ORDER BY u.nom""",
        (eval_id,),
    )


def get_submission_copy(sub_id: int) -> dict | None:
    return query_one("SELECT copie_nom, copie FROM soumissions WHERE id = ?", (sub_id,))


def grade_submission(sub_id: int, note: float, commentaire: str) -> None:
    sub = query_one(
        """SELECT s.etudiant_id, e.matiere_id, e.compte_dans_moyenne FROM soumissions s
           JOIN evaluations e ON e.id = s.evaluation_id WHERE s.id = ?""",
        (sub_id,),
    )
    with get_conn() as conn:
        conn.execute("UPDATE soumissions SET note_sur_20 = ?, commentaire = ? WHERE id = ?", (note, commentaire, sub_id))
        if sub and sub["compte_dans_moyenne"]:
            _upsert_grade(conn, sub["etudiant_id"], sub["matiere_id"], note)


# --------------------------------------------------------------------------- #
# Initialisation + données de démonstration
# --------------------------------------------------------------------------- #
def init_db(seed: bool = True) -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        already = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if seed and not already:
        from ent.seed import seed_demo_data
        seed_demo_data()
