# 🎓 FOREVER — Espace Numérique de Travail (ENT)

Un ENT universitaire complet développé en **Python / Streamlit / SQLite**, avec deux espaces :
**étudiants** et **professeurs**.

## Fonctionnalités

### 👩‍🎓 Espace étudiant
| Module | Ce que l'étudiant peut faire |
|---|---|
| **Accueil** | Moyenne générale, crédits ECTS, résultat de l'année, évaluations à faire, derniers cours |
| **Mes notes** | Notes par semestre, statut de chaque matière (validée / non validée / en attente), moyennes pondérées, ECTS, mention, graphique |
| **Mes documents** | Téléchargement en PDF du **certificat de scolarité**, du **relevé de notes** et de l'**attestation de réussite** (disponible uniquement si l'année est validée) |
| **Mes cours** | Téléchargement des supports PDF publiés par les enseignants, filtre par matière |
| **QCM & examens** | QCM d'entraînement corrigés automatiquement (avec correction détaillée), examens QCM en ligne, examens PDF (téléchargement du sujet + dépôt de la copie) |
| **Mon profil** | Informations administratives, changement de mot de passe |

### 👨‍🏫 Espace professeur
| Module | Ce que le professeur peut faire |
|---|---|
| **Accueil** | Tableau de bord : matières, cours publiés, évaluations, copies à corriger, moyenne et taux de réussite par matière |
| **Publier un cours** | Mise en ligne de supports PDF par matière, suppression |
| **Créer un QCM / examen** | QCM d'entraînement ou examen, au format **QCM** (questions à choix unique ou multiple) ou **PDF** (sujet + dépôt de copies), durée, date limite, report automatique de la note |
| **Saisie des notes** | Tableau éditable des notes sur 20, session 1 / rattrapage, statistiques (moyenne, min, max, taux de réussite) |
| **Résultats & copies** | Résultats des QCM, téléchargement et correction des copies PDF avec commentaire |

## Règles de scolarité (modèle LMD)
- Une matière est **validée** si la note est ≥ 10/20 → ses ECTS sont acquis.
- Un semestre est **validé** si toutes les notes sont saisies et que la moyenne pondérée par les coefficients est ≥ 10 (**compensation**).
- L'année est validée si tous les semestres sont validés → l'attestation de réussite devient disponible.
- Mentions : Passable (10-12), Assez bien (12-14), Bien (14-16), Très bien (≥ 16).

## Comptes de démonstration
| Rôle | Identifiant | Mot de passe | Situation |
|---|---|---|---|
| Étudiant | `m.sarr` | `etudiant` | Année validée, mention Bien |
| Étudiant | `c.dupont` | `etudiant` | Semestre 2 en cours |
| Étudiant | `l.leroy` | `etudiant` | Année non validée |
| Étudiant | `a.fall`, `t.bernard` | `etudiant` | Année validée |
| Professeur | `m.martin`, `j.durand`, `f.ndiaye` | `professeur` | |

La base SQLite est créée et remplie automatiquement au premier lancement (`data/ent.db`).

## Lancer en local
```bash
git clone https://github.com/ABDOULAYEDIOP150/FOREVER.git
cd FOREVER
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Déployer sur Streamlit Community Cloud (gratuit)
1. Aller sur **https://share.streamlit.io** et se connecter avec GitHub.
2. **Create app** → *Deploy a public app from GitHub*.
3. Repository : `ABDOULAYEDIOP150/FOREVER` · Branch : `main` · Main file path : `app.py`.
4. (Optionnel) App URL : `forever-ent` → `https://forever-ent.streamlit.app`.
5. **Deploy**. L'application est en ligne en 1 à 2 minutes.

> ⚠️ Sur Streamlit Cloud le disque est éphémère : les données ajoutées (notes, cours, copies) sont
> réinitialisées au redémarrage de l'app. Pour la production, remplacer SQLite par PostgreSQL
> (Supabase, Neon…) dans `ent/db.py`.

## Structure du projet
```
FOREVER/
├── app.py                  # Point d'entrée : connexion + navigation par rôle
├── ent/
│   ├── db.py               # Schéma SQLite, authentification (PBKDF2), requêtes
│   ├── scolarite.py        # Règles : moyennes, validation, ECTS, mentions
│   ├── documents.py        # Génération des PDF officiels (fpdf2)
│   ├── seed.py             # Données de démonstration
│   ├── ui.py               # Style et composants communs
│   ├── views_etudiant.py   # Espace étudiant
│   └── views_prof.py       # Espace professeur
├── tests/test_ent.py       # Tests unitaires + parcours UI (streamlit AppTest)
├── .streamlit/config.toml
└── requirements.txt
```

## Tests
```bash
pip install pytest
pytest -q
```

## Modèle de données
`programmes` → `users` (étudiants / professeurs) → `matieres` (semestre, ECTS, coefficient, enseignant)
→ `notes` · `cours` (PDF) · `evaluations` (QCM / examen, format QCM ou PDF) → `soumissions` (réponses, copies, notes).
