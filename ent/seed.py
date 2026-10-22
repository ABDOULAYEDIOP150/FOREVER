"""Données de démonstration : une promo de Master 1, trois professeurs, cinq étudiants."""
from __future__ import annotations

import random

from ent import db
from ent.documents import simple_pdf

PROGRAMME = ("M1-DS", "Data Science", "Master 1", "2025-2026")

PROFESSEURS = [
    ("m.martin", "Marie", "Martin"),
    ("j.durand", "Julien", "Durand"),
    ("f.ndiaye", "Fatou", "Ndiaye"),
]

# code, nom, semestre, ects, coef, prof (username)
MATIERES = [
    ("DS101", "Statistique inférentielle", 1, 6, 2, "m.martin"),
    ("DS102", "Programmation Python", 1, 6, 2, "f.ndiaye"),
    ("DS103", "Bases de données et SQL", 1, 6, 2, "j.durand"),
    ("DS104", "Algèbre linéaire pour la data", 1, 6, 2, "m.martin"),
    ("DS105", "Anglais scientifique", 1, 6, 1, "f.ndiaye"),
    ("DS201", "Machine Learning", 2, 6, 2, "m.martin"),
    ("DS202", "Big Data et Spark", 2, 6, 2, "j.durand"),
    ("DS203", "Data Engineering et pipelines", 2, 6, 2, "j.durand"),
    ("DS204", "Visualisation de données", 2, 6, 1, "f.ndiaye"),
    ("DS205", "Projet tutoré", 2, 6, 2, "m.martin"),
]

# username, prénom, nom, n° étudiant, naissance, lieu, profil de notes
ETUDIANTS = [
    ("m.sarr", "Moussa", "Sarr", "22500117", "1999-04-18", "Dakar", "excellent"),
    ("c.dupont", "Camille", "Dupont", "22500204", "2001-03-02", "Lyon", "en_cours"),
    ("l.leroy", "Lucas", "Leroy", "22500311", "2000-07-21", "Lille", "faible"),
    ("a.fall", "Awa", "Fall", "22500428", "2001-12-09", "Thiès", "bon"),
    ("t.bernard", "Thomas", "Bernard", "22500533", "2000-05-30", "Nantes", "moyen"),
]

PROFILS = {"excellent": (15.5, 1.5), "bon": (13.0, 1.8), "moyen": (11.0, 2.0), "faible": (8.5, 2.2), "en_cours": (12.5, 2.0)}

MDP_ETUDIANT = "etudiant"
MDP_PROFESSEUR = "professeur"


def seed_demo_data() -> None:
    rng = random.Random(42)
    prog_id = db.execute(
        "INSERT INTO programmes (code, nom, niveau, annee_universitaire) VALUES (?, ?, ?, ?)", PROGRAMME
    )

    prof_ids = {}
    for username, prenom, nom in PROFESSEURS:
        prof_ids[username] = db.create_user(
            username, MDP_PROFESSEUR, "professeur", prenom, nom, email=f"{username}@forever-univ.fr"
        )

    mat_ids = {}
    for code, nom, sem, ects, coef, prof in MATIERES:
        mat_ids[code] = db.execute(
            """INSERT INTO matieres (code, nom, semestre, ects, coefficient, programme_id, professeur_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, nom, sem, ects, coef, prog_id, prof_ids[prof]),
        )

    etu_ids = {}
    for username, prenom, nom, num, naiss, lieu, profil in ETUDIANTS:
        etu_ids[username] = db.create_user(
            username, MDP_ETUDIANT, "etudiant", prenom, nom,
            email=f"{username}@etu.forever-univ.fr", numero_etudiant=num, date_naissance=naiss,
            lieu_naissance=lieu, programme_id=prog_id, date_inscription="2025-09-02",
        )
        mu, sigma = PROFILS[profil]
        grades = {}
        for code, *_ in MATIERES:
            if profil == "en_cours" and code in ("DS202", "DS203", "DS205"):
                continue  # notes du S2 pas encore saisies
            grades[code] = round(min(20, max(0, rng.gauss(mu, sigma))) * 4) / 4
        for code, note in grades.items():
            db.save_grades(mat_ids[code], {etu_ids[username]: note})

    _seed_contents(mat_ids)


def _seed_contents(mat_ids: dict[str, int]) -> None:
    # --- Cours PDF ---------------------------------------------------------
    db.add_course(
        mat_ids["DS201"], "Chapitre 1 - Introduction au Machine Learning",
        "Apprentissage supervisé / non supervisé, biais-variance, validation croisée.",
        "DS201_chapitre1_intro_ML.pdf",
        simple_pdf("Introduction au Machine Learning", [
            ("1. Définition", "Le Machine Learning consiste à apprendre une fonction à partir de données "
             "plutôt qu'à la programmer explicitement."),
            ("2. Supervisé vs non supervisé", "En apprentissage supervisé, chaque exemple possède une étiquette "
             "(régression, classification). En non supervisé, on cherche une structure (clustering, réduction de dimension)."),
            ("3. Compromis biais-variance", "Un modèle trop simple sous-apprend (biais élevé), un modèle trop complexe "
             "sur-apprend (variance élevée). La validation croisée permet de choisir la bonne complexité."),
            ("4. Métriques", "Régression : RMSE, MAE, R2. Classification : accuracy, précision, rappel, F1, AUC."),
        ], auteur="Pr. Marie Martin - Master 1 Data Science"),
    )
    db.add_course(
        mat_ids["DS103"], "Cours SQL - Jointures et agrégations",
        "INNER/LEFT JOIN, GROUP BY, HAVING, fonctions de fenêtre.",
        "DS103_jointures_agregations.pdf",
        simple_pdf("SQL : jointures et agrégations", [
            ("Jointures", "INNER JOIN conserve les lignes présentes des deux côtés ; LEFT JOIN conserve toutes les "
             "lignes de la table de gauche et complète par NULL."),
            ("Agrégations", "GROUP BY regroupe les lignes ; HAVING filtre après agrégation, WHERE filtre avant."),
            ("Fonctions de fenêtre", "ROW_NUMBER(), RANK(), SUM() OVER (PARTITION BY ... ORDER BY ...) calculent "
             "sans réduire le nombre de lignes."),
        ], auteur="Pr. Julien Durand - Master 1 Data Science"),
    )
    db.add_course(
        mat_ids["DS102"], "TP Python - Pandas",
        "Manipulation de DataFrames : sélection, filtres, groupby, merge.",
        "DS102_TP_pandas.pdf",
        simple_pdf("TP Python : Pandas", [
            ("Objectifs", "Charger un CSV, nettoyer les valeurs manquantes, agréger et fusionner des tables."),
            ("Exercice 1", "Charger ventes.csv avec pd.read_csv puis afficher les 5 premières lignes."),
            ("Exercice 2", "Calculer le chiffre d'affaires par région avec groupby et sum."),
        ], auteur="Pr. Fatou Ndiaye - Master 1 Data Science"),
    )

    # --- QCM d'entraînement --------------------------------------------------
    db.add_evaluation(
        mat_ids["DS201"], "QCM - Bases du Machine Learning",
        "10 minutes conseillées. Plusieurs réponses peuvent être correctes : cochez-les toutes.",
        "qcm", "qcm", duree_minutes=10,
        questions=[
            {"question": "Lesquelles sont des tâches d'apprentissage supervisé ?",
             "choix": ["Régression", "Classification", "Clustering", "Réduction de dimension"], "correctes": [0, 1]},
            {"question": "Un modèle qui a une très bonne performance sur le train et mauvaise sur le test :",
             "choix": ["Sous-apprend", "Sur-apprend", "Est parfaitement calibré"], "correctes": [1]},
            {"question": "Quelle métrique est adaptée à une classification déséquilibrée ?",
             "choix": ["Accuracy", "F1-score", "RMSE"], "correctes": [1]},
            {"question": "La validation croisée sert à :",
             "choix": ["Estimer la performance en généralisation", "Accélérer l'entraînement", "Choisir des hyperparamètres"],
             "correctes": [0, 2]},
        ],
    )
    db.add_evaluation(
        mat_ids["DS103"], "QCM - SQL",
        "Entraînement sur les jointures et les agrégations.", "qcm", "qcm", duree_minutes=8,
        questions=[
            {"question": "Quelle clause filtre après un GROUP BY ?", "choix": ["WHERE", "HAVING", "ORDER BY"], "correctes": [1]},
            {"question": "LEFT JOIN renvoie :", "choix": ["Seulement les correspondances",
             "Toutes les lignes de gauche + correspondances", "Toutes les lignes des deux tables"], "correctes": [1]},
            {"question": "Quelles fonctions sont des fonctions de fenêtre ?", "choix": ["ROW_NUMBER()", "RANK()", "CONCAT()"],
             "correctes": [0, 1]},
        ],
    )

    # --- Examens --------------------------------------------------------------
    db.add_evaluation(
        mat_ids["DS202"], "Examen final - Big Data et Spark",
        "Durée 2h. Téléchargez le sujet, rédigez votre copie et déposez-la au format PDF avant la date limite.",
        "examen", "pdf", duree_minutes=120, date_limite="2026-12-15 18:00", compte_dans_moyenne=True,
        sujet_nom="DS202_examen_final_sujet.pdf",
        sujet=simple_pdf("Examen final - Big Data et Spark", [
            ("Consignes", "Documents non autorisés. Durée : 2 heures. Barème indicatif sur 20 points."),
            ("Exercice 1 (6 pts)", "Expliquez la différence entre transformation et action dans Spark. Donnez deux exemples de chaque."),
            ("Exercice 2 (8 pts)", "Écrivez en PySpark le calcul du chiffre d'affaires mensuel par catégorie à partir "
             "d'une table orders(order_id, date, category, amount)."),
            ("Exercice 3 (6 pts)", "Qu'est-ce que le partitionnement ? Quel impact sur les performances d'un shuffle ?"),
        ], auteur="Pr. Julien Durand"),
    )
    db.add_evaluation(
        mat_ids["DS205"], "Examen QCM - Gestion de projet data",
        "Examen noté : une seule tentative, la note est reportée automatiquement dans la matière.",
        "examen", "qcm", duree_minutes=15, date_limite="2026-12-20 23:59", compte_dans_moyenne=True,
        questions=[
            {"question": "Dans Scrum, qui priorise le backlog produit ?",
             "choix": ["Le Scrum Master", "Le Product Owner", "L'équipe de développement"], "correctes": [1]},
            {"question": "Quels éléments font partie d'un bon README de projet data ?",
             "choix": ["Instructions d'installation", "Description des données", "Mot de passe de la base"], "correctes": [0, 1]},
            {"question": "Git : quelle commande crée une nouvelle branche et bascule dessus ?",
             "choix": ["git checkout -b", "git merge", "git switch -c"], "correctes": [0, 2]},
        ],
    )
