"""Règles de scolarité : moyennes, validation des matières, semestres et année, mentions.

Règles appliquées (modèle LMD classique) :
- une matière est validée si la note est >= 10/20 ; ses crédits ECTS sont alors acquis ;
- un semestre est validé si toutes ses notes sont saisies et que sa moyenne pondérée
  (coefficients) est >= 10/20 : la compensation s'applique et tous les ECTS du semestre sont acquis ;
- l'année est validée si tous les semestres sont validés ;
- mention selon la moyenne annuelle.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SEUIL = 10.0


def mention(moyenne: float | None) -> str:
    if moyenne is None or moyenne < SEUIL:
        return "—"
    if moyenne >= 16:
        return "Très bien"
    if moyenne >= 14:
        return "Bien"
    if moyenne >= 12:
        return "Assez bien"
    return "Passable"


def statut_matiere(note: float | None) -> str:
    if note is None:
        return "En attente"
    return "Validée" if note >= SEUIL else "Non validée"


@dataclass
class Semestre:
    numero: int
    matieres: list[dict] = field(default_factory=list)

    @property
    def complet(self) -> bool:
        return all(m["note"] is not None for m in self.matieres)

    @property
    def moyenne(self) -> float | None:
        notees = [m for m in self.matieres if m["note"] is not None]
        if not notees:
            return None
        total_coef = sum(m["coefficient"] for m in notees)
        return round(sum(m["note"] * m["coefficient"] for m in notees) / total_coef, 2)

    @property
    def ects_total(self) -> int:
        return sum(m["ects"] for m in self.matieres)

    @property
    def valide(self) -> bool:
        return self.complet and self.moyenne is not None and self.moyenne >= SEUIL

    @property
    def ects_acquis(self) -> int:
        if self.valide:
            return self.ects_total
        return sum(m["ects"] for m in self.matieres if m["note"] is not None and m["note"] >= SEUIL)

    @property
    def statut(self) -> str:
        if not self.complet:
            return "En cours"
        return "Validé" if self.valide else "Non validé"


@dataclass
class Bilan:
    semestres: list[Semestre]

    @property
    def moyenne_annuelle(self) -> float | None:
        moyennes = [s.moyenne for s in self.semestres if s.moyenne is not None]
        if not moyennes:
            return None
        return round(sum(moyennes) / len(moyennes), 2)

    @property
    def complet(self) -> bool:
        return all(s.complet for s in self.semestres)

    @property
    def annee_validee(self) -> bool:
        return bool(self.semestres) and all(s.valide for s in self.semestres)

    @property
    def ects_acquis(self) -> int:
        return sum(s.ects_acquis for s in self.semestres)

    @property
    def ects_total(self) -> int:
        return sum(s.ects_total for s in self.semestres)

    @property
    def mention(self) -> str:
        return mention(self.moyenne_annuelle) if self.annee_validee else "—"


def bilan(grades: list[dict]) -> Bilan:
    """Construit le bilan à partir des lignes renvoyées par db.student_grades."""
    by_sem: dict[int, Semestre] = {}
    for g in grades:
        by_sem.setdefault(g["semestre"], Semestre(g["semestre"])).matieres.append(g)
    return Bilan([by_sem[k] for k in sorted(by_sem)])
