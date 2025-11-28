"""
Service d'évaluation de la qualité du traitement de documents.
Génère un score de 0 à 100 avec des métriques détaillées.
"""

from typing import Dict, List, Tuple, Any
from app.models.schemas.document import (
    ProcessedDocument,
    Section,
    DocumentOutline,
    DocumentMetadata,
    OutlineNode
)
import re
from statistics import mean, stdev
import logging

logger = logging.getLogger(__name__)


class QualityScorer:
    """
    Évalue la qualité du traitement d'un document.

    Score total : 0-100
    - 0-40 : Mauvais (nécessite retraitement)
    - 41-70 : Moyen (à vérifier)
    - 71-85 : Bon
    - 86-100 : Excellent
    """

    def __init__(self):
        # Patterns pour détecter les problèmes OCR
        self.noise_patterns = [
            r'[\\]{2,}',           # LaTeX non nettoyé
            r'[\^_]{2,}',          # Symboles mathématiques
            r'[|]{2,}',            # Tableaux mal parsés
            r'[#]{3,}',            # Markdown corrompu
            r'[\x00-\x1F]',        # Caractères de contrôle
        ]

        # Mots courts souvent indicateurs de bruit
        self.noise_words = {'--', ':--', '|', '```', '***'}

        # Longueurs idéales
        self.ideal_section_length = (50, 500)  # mots
        self.min_sections = 5
        self.ideal_sections_range = (10, 100)

    def score_document(
        self,
        document: ProcessedDocument
    ) -> Dict[str, Any]:
        """
        Évalue la qualité globale d'un document traité.

        Returns:
            {
                "overall_score": 85,
                "grade": "Bon",
                "needs_review": False,
                "scores": {
                    "ocr_quality": 28/30,
                    "structure_quality": 22/25,
                    "metadata_completeness": 18/20,
                    "content_quality": 12/15,
                    "coherence": 9/10
                },
                "issues": [
                    {
                        "severity": "warning",
                        "category": "content",
                        "message": "3 sections ont moins de 10 mots",
                        "sections_affected": [12, 14, 26]
                    }
                ],
                "recommendations": [
                    "Vérifier les sections courtes (12, 14, 26)",
                    "Certaines sections contiennent du LaTeX résiduel"
                ]
            }
        """
        logger.info(f"Starting quality scoring for document {document.documentId}")

        scores = {}
        issues = []

        try:
            # A. Évaluer la qualité OCR
            ocr_score, ocr_issues = self._score_ocr_quality(document.sections)
            scores["ocr_quality"] = ocr_score
            issues.extend(ocr_issues)

            # B. Évaluer la structure
            structure_score, structure_issues = self._score_structure(
                document.documentOutline,
                document.sections
            )
            scores["structure_quality"] = structure_score
            issues.extend(structure_issues)

            # C. Évaluer les métadonnées
            metadata_score, metadata_issues = self._score_metadata(
                document.metadata
            )
            scores["metadata_completeness"] = metadata_score
            issues.extend(metadata_issues)

            # D. Évaluer le contenu
            content_score, content_issues = self._score_content(
                document.sections
            )
            scores["content_quality"] = content_score
            issues.extend(content_issues)

            # E. Évaluer la cohérence
            coherence_score, coherence_issues = self._score_coherence(
                document.sections,
                document.documentOutline
            )
            scores["coherence"] = coherence_score
            issues.extend(coherence_issues)

            # Calculer le score total
            overall_score = sum(scores.values())

            # Déterminer le grade
            grade, needs_review = self._get_grade(overall_score)

            # Générer des recommandations
            recommendations = self._generate_recommendations(issues, scores)

            # Générer les métriques détaillées
            metrics = self._get_detailed_metrics(document)

            logger.info(
                f"Quality scoring completed: {overall_score:.1f}/100 ({grade}) - "
                f"Review needed: {needs_review}"
            )

            return {
                "overall_score": round(overall_score, 1),
                "grade": grade,
                "needs_review": needs_review,
                "scores": scores,
                "issues": sorted(issues, key=lambda x: self._severity_order(x["severity"])),
                "recommendations": recommendations,
                "metrics": metrics
            }

        except Exception as e:
            logger.error(f"Error during quality scoring: {str(e)}")
            # Return a minimal score in case of error
            return {
                "overall_score": 0,
                "grade": "Erreur",
                "needs_review": True,
                "scores": {},
                "issues": [{
                    "severity": "error",
                    "category": "system",
                    "message": f"Erreur lors du scoring: {str(e)}"
                }],
                "recommendations": ["Erreur lors de l'évaluation - vérifier les logs"],
                "metrics": {}
            }

    def _score_ocr_quality(
        self,
        sections: List[Section]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Évalue la qualité de l'OCR (max 30 points).

        Critères :
        - Absence de caractères corrompus (10 pts)
        - Ratio texte/noise élevé (10 pts)
        - LaTeX bien nettoyé (5 pts)
        - Cohérence des mots (5 pts)
        """
        max_score = 30
        score = max_score
        issues: List[Dict[str, Any]] = []

        if not sections:
            return 0, [{
                "severity": "error",
                "category": "ocr",
                "message": "Aucune section à évaluer",
                "impact": "-30 points"
            }]

        all_content = " ".join([s.content for s in sections])
        total_words = sum(s.wordCount for s in sections)

        # 1. Détecter les patterns de bruit
        noise_count = 0
        for pattern in self.noise_patterns:
            matches = re.findall(pattern, all_content)
            noise_count += len(matches)

        if noise_count > 0:
            penalty = min(10, noise_count * 0.5)
            score -= penalty
            issues.append({
                "severity": "warning" if penalty < 5 else "error",
                "category": "ocr",
                "message": f"{noise_count} patterns de bruit détectés (LaTeX, symboles corrompus)",
                "impact": f"-{penalty:.1f} points"
            })

        # 2. Ratio texte/noise
        noise_words = sum(1 for word in all_content.split() if word in self.noise_words)
        if total_words > 0:
            noise_ratio = noise_words / total_words
            if noise_ratio > 0.05:  # Plus de 5% de bruit
                penalty = min(10, noise_ratio * 100)
                score -= penalty
                issues.append({
                    "severity": "error",
                    "category": "ocr",
                    "message": f"Ratio de bruit élevé : {noise_ratio*100:.1f}%",
                    "impact": f"-{penalty:.1f} points"
                })

        # 3. Vérifier LaTeX résiduel
        latex_residual = len(re.findall(r'\\[a-z]+\{', all_content))
        if latex_residual > 5:
            penalty = min(5, latex_residual * 0.2)
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "ocr",
                "message": f"{latex_residual} commandes LaTeX résiduelles détectées",
                "impact": f"-{penalty:.1f} points"
            })

        # 4. Cohérence des mots (détection de charabia)
        gibberish_count = self._detect_gibberish(sections)
        if gibberish_count > 0:
            penalty = min(5, gibberish_count * 0.5)
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "ocr",
                "message": f"{gibberish_count} sections avec du texte incohérent",
                "impact": f"-{penalty:.1f} points"
            })

        return max(0, score), issues

    def _score_structure(
        self,
        outline: DocumentOutline,
        sections: List[Section]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Évalue la qualité de la structure (max 25 points).

        Critères :
        - Plan hiérarchique valide (10 pts)
        - Profondeur appropriée (5 pts)
        - Nombre de sections cohérent (5 pts)
        - Hiérarchie logique (5 pts)
        """
        max_score = 25
        score = max_score
        issues: List[Dict[str, Any]] = []

        # 1. Vérifier la présence d'un plan
        if not outline or not outline.nodes:
            score -= 10
            issues.append({
                "severity": "error",
                "category": "structure",
                "message": "Aucun plan hiérarchique détecté",
                "impact": "-10 points"
            })
            return score, issues

        # 2. Évaluer la profondeur
        max_depth = self._get_max_depth(outline.nodes)
        if max_depth < 2:
            score -= 3
            issues.append({
                "severity": "warning",
                "category": "structure",
                "message": f"Hiérarchie peu profonde (depth={max_depth})",
                "impact": "-3 points"
            })
        elif max_depth > 5:
            score -= 2
            issues.append({
                "severity": "info",
                "category": "structure",
                "message": f"Hiérarchie très profonde (depth={max_depth})",
                "impact": "-2 points"
            })

        # 3. Vérifier le nombre de sections
        num_sections = len(sections)
        if num_sections < self.min_sections:
            score -= 5
            issues.append({
                "severity": "error",
                "category": "structure",
                "message": f"Trop peu de sections ({num_sections}), document mal découpé",
                "impact": "-5 points"
            })
        elif not (self.ideal_sections_range[0] <= num_sections <= self.ideal_sections_range[1]):
            score -= 2
            issues.append({
                "severity": "info",
                "category": "structure",
                "message": f"Nombre de sections inhabituel ({num_sections})",
                "impact": "-2 points"
            })

        # 4. Vérifier la cohérence hiérarchique (H3 sans H2, etc.)
        hierarchy_issues = self._check_hierarchy_coherence(sections)
        if hierarchy_issues:
            penalty = min(5, len(hierarchy_issues))
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "structure",
                "message": f"{len(hierarchy_issues)} incohérences hiérarchiques",
                "details": hierarchy_issues[:3],  # Limiter à 3 exemples
                "impact": f"-{penalty} points"
            })

        return max(0, score), issues

    def _score_metadata(
        self,
        metadata: DocumentMetadata
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Évalue la complétude des métadonnées (max 20 points).

        Critères :
        - Titre présent et valide (8 pts)
        - Type de document identifié (5 pts)
        - Référence présente (4 pts)
        - Parties identifiées (3 pts)
        """
        max_score = 20
        score = max_score
        issues: List[Dict[str, Any]] = []

        # 1. Vérifier le titre
        if not metadata.documentTitle or len(metadata.documentTitle) < 5:
            score -= 8
            issues.append({
                "severity": "error",
                "category": "metadata",
                "message": "Titre manquant ou invalide",
                "impact": "-8 points"
            })

        # 2. Vérifier le type
        if not metadata.documentType or metadata.documentType == "unknown":
            score -= 5
            issues.append({
                "severity": "warning",
                "category": "metadata",
                "message": "Type de document non identifié",
                "impact": "-5 points"
            })

        # 3. Vérifier la référence
        if not metadata.reference:
            score -= 4
            issues.append({
                "severity": "info",
                "category": "metadata",
                "message": "Référence du document manquante",
                "impact": "-4 points"
            })

        # 4. Vérifier les parties
        if not metadata.parties or len(metadata.parties) == 0:
            score -= 3
            issues.append({
                "severity": "info",
                "category": "metadata",
                "message": "Aucune partie identifiée dans le document",
                "impact": "-3 points"
            })

        return max(0, score), issues

    def _score_content(
        self,
        sections: List[Section]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Évalue la qualité du contenu (max 15 points).

        Critères :
        - Longueur des sections appropriée (6 pts)
        - Présence de mots-clés (4 pts)
        - Distribution cohérente (3 pts)
        - Densité d'information (2 pts)
        """
        max_score = 15
        score = max_score
        issues: List[Dict[str, Any]] = []

        if not sections:
            return 0, [{
                "severity": "error",
                "category": "content",
                "message": "Aucune section à évaluer",
                "impact": "-15 points"
            }]

        # 1. Vérifier la longueur des sections
        too_short = [s for s in sections if s.wordCount < self.ideal_section_length[0]]
        too_long = [s for s in sections if s.wordCount > self.ideal_section_length[1]]

        if too_short:
            penalty = min(3, len(too_short) * 0.3)
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "content",
                "message": f"{len(too_short)} sections trop courtes (<{self.ideal_section_length[0]} mots)",
                "sections_affected": [s.sectionPosition for s in too_short[:5]],
                "impact": f"-{penalty:.1f} points"
            })

        if too_long:
            penalty = min(3, len(too_long) * 0.3)
            score -= penalty
            issues.append({
                "severity": "info",
                "category": "content",
                "message": f"{len(too_long)} sections très longues (>{self.ideal_section_length[1]} mots)",
                "sections_affected": [s.sectionPosition for s in too_long[:5]],
                "impact": f"-{penalty:.1f} points"
            })

        # 2. Vérifier les mots-clés
        sections_without_keywords = [s for s in sections if not s.keywords or len(s.keywords) == 0]
        if sections_without_keywords:
            penalty = min(4, len(sections_without_keywords) * 0.2)
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "content",
                "message": f"{len(sections_without_keywords)} sections sans mots-clés",
                "impact": f"-{penalty:.1f} points"
            })

        # 3. Vérifier la distribution
        word_counts = [s.wordCount for s in sections if s.wordCount > 0]
        if word_counts and len(word_counts) > 3:
            try:
                cv = stdev(word_counts) / mean(word_counts)  # Coefficient de variation
                if cv > 2:  # Très grande variation
                    score -= 3
                    issues.append({
                        "severity": "info",
                        "category": "content",
                        "message": "Distribution très inégale des longueurs de sections",
                        "impact": "-3 points"
                    })
            except Exception:
                pass

        # 4. Vérifier la densité d'information
        avg_keywords_per_section = mean([len(s.keywords) for s in sections])
        if avg_keywords_per_section < 2:
            score -= 2
            issues.append({
                "severity": "warning",
                "category": "content",
                "message": f"Faible densité d'information (avg {avg_keywords_per_section:.1f} mots-clés/section)",
                "impact": "-2 points"
            })

        return max(0, score), issues

    def _score_coherence(
        self,
        sections: List[Section],
        outline: DocumentOutline
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Évalue la cohérence globale (max 10 points).

        Critères :
        - Positions séquentielles (3 pts)
        - Breadcrumbs cohérents (3 pts)
        - Relations parent-enfant valides (2 pts)
        - Siblings cohérents (2 pts)
        """
        max_score = 10
        score = max_score
        issues: List[Dict[str, Any]] = []

        if not sections:
            return 0, [{
                "severity": "error",
                "category": "coherence",
                "message": "Aucune section à évaluer",
                "impact": "-10 points"
            }]

        # 1. Vérifier les positions séquentielles
        positions = [s.sectionPosition for s in sections]
        if positions != sorted(positions):
            score -= 3
            issues.append({
                "severity": "error",
                "category": "coherence",
                "message": "Positions de sections non séquentielles",
                "impact": "-3 points"
            })

        # 2. Vérifier les breadcrumbs
        invalid_breadcrumbs = [
            s for s in sections
            if not s.breadcrumb or len(s.breadcrumb.split('>')) < 2
        ]
        if invalid_breadcrumbs:
            penalty = min(3, len(invalid_breadcrumbs) * 0.5)
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "coherence",
                "message": f"{len(invalid_breadcrumbs)} breadcrumbs invalides",
                "impact": f"-{penalty:.1f} points"
            })

        # 3. Vérifier les relations parent-enfant
        orphan_sections = [
            s for s in sections
            if s.h2 and not s.parentSection
        ]
        if orphan_sections:
            penalty = min(2, len(orphan_sections) * 0.3)
            score -= penalty
            issues.append({
                "severity": "warning",
                "category": "coherence",
                "message": f"{len(orphan_sections)} sections sans parent valide",
                "impact": f"-{penalty:.1f} points"
            })

        # 4. Vérifier les siblings
        sections_with_invalid_siblings = 0
        for section in sections:
            if section.siblingSections:
                # Vérifier que les siblings existent
                sibling_titles = [s.title for s in sections]
                invalid_siblings = [
                    sib for sib in section.siblingSections
                    if sib not in sibling_titles
                ]
                if invalid_siblings:
                    sections_with_invalid_siblings += 1

        if sections_with_invalid_siblings > 0:
            penalty = min(2, sections_with_invalid_siblings * 0.2)
            score -= penalty
            issues.append({
                "severity": "info",
                "category": "coherence",
                "message": f"{sections_with_invalid_siblings} sections avec références siblings invalides",
                "impact": f"-{penalty:.1f} points"
            })

        return max(0, score), issues

    # Méthodes utilitaires

    def _detect_gibberish(self, sections: List[Section]) -> int:
        """Détecte les sections avec du texte incohérent"""
        gibberish_count = 0
        for section in sections:
            words = section.content.split()
            if len(words) < 5:
                continue

            # Vérifier la proportion de "mots" suspects
            suspect_words = sum(
                1 for word in words
                if len(word) > 20 or  # Mots trop longs
                not any(c.isalpha() for c in word) or  # Pas de lettres
                (len(word) > 0 and sum(1 for c in word if c.isupper()) / len(word) > 0.5)  # Trop de majuscules
            )

            if suspect_words / len(words) > 0.3:  # Plus de 30% de mots suspects
                gibberish_count += 1

        return gibberish_count

    def _get_max_depth(self, nodes: List[OutlineNode], current_depth: int = 1) -> int:
        """Calcule la profondeur maximale de l'arbre"""
        if not nodes:
            return current_depth

        max_child_depth = current_depth
        for node in nodes:
            if node.children:
                child_depth = self._get_max_depth(node.children, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def _check_hierarchy_coherence(self, sections: List[Section]) -> List[str]:
        """Vérifie la cohérence de la hiérarchie H1/H2/H3"""
        issues = []

        for section in sections:
            # H3 sans H2
            if section.h3 and not section.h2:
                issues.append(f"Section {section.sectionPosition}: H3 sans H2")

            # H2 sans H1
            if section.h2 and not section.h1:
                issues.append(f"Section {section.sectionPosition}: H2 sans H1")

        return issues

    def _get_grade(self, score: float) -> Tuple[str, bool]:
        """Détermine le grade et si une revue est nécessaire"""
        if score >= 86:
            return "Excellent", False
        elif score >= 71:
            return "Bon", False
        elif score >= 41:
            return "Moyen", True
        else:
            return "Mauvais", True

    def _severity_order(self, severity: str) -> int:
        """Ordre de priorité des sévérités"""
        return {"error": 0, "warning": 1, "info": 2}.get(severity, 3)

    def _generate_recommendations(
        self,
        issues: List[Dict[str, Any]],
        scores: Dict[str, float]
    ) -> List[str]:
        """Génère des recommandations basées sur les issues"""
        recommendations = []

        # Recommandations basées sur les scores faibles
        if scores.get("ocr_quality", 30) < 20:
            recommendations.append("⚠️ Qualité OCR faible - envisager un retraitement avec de meilleurs paramètres")

        if scores.get("structure_quality", 25) < 15:
            recommendations.append("⚠️ Structure mal détectée - vérifier le plan hiérarchique manuellement")

        if scores.get("metadata_completeness", 20) < 10:
            recommendations.append("⚠️ Métadonnées incomplètes - compléter manuellement le titre et la référence")

        # Recommandations basées sur les issues spécifiques
        error_count = sum(1 for issue in issues if issue["severity"] == "error")
        if error_count > 0:
            recommendations.append(f"🔴 {error_count} erreur(s) critique(s) détectée(s) - revue manuelle nécessaire")

        warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
        if warning_count > 3:
            recommendations.append(f"🟡 {warning_count} avertissements - vérifier les sections signalées")

        # Recommandations pour sections courtes
        short_section_issues = [i for i in issues if "sections trop courtes" in i.get("message", "")]
        if short_section_issues:
            sections = short_section_issues[0].get("sections_affected", [])
            if sections:
                recommendations.append(f"📝 Vérifier les sections courtes : {', '.join(map(str, sections[:5]))}")

        if not recommendations:
            recommendations.append("✅ Document bien traité - aucune action requise")

        return recommendations

    def _get_detailed_metrics(self, document: ProcessedDocument) -> Dict[str, Any]:
        """Calcule des métriques détaillées pour analyse"""
        sections = document.sections

        if not sections:
            return {
                "total_sections": 0,
                "total_words": 0,
                "avg_words_per_section": 0,
                "min_words": 0,
                "max_words": 0,
                "sections_by_type": {},
                "hierarchy_depth": 0,
                "sections_with_h1": 0,
                "sections_with_h2": 0,
                "sections_with_h3": 0,
                "avg_keywords_per_section": 0
            }

        return {
            "total_sections": len(sections),
            "total_words": sum(s.wordCount for s in sections),
            "avg_words_per_section": round(mean([s.wordCount for s in sections]), 1) if sections else 0,
            "min_words": min([s.wordCount for s in sections]) if sections else 0,
            "max_words": max([s.wordCount for s in sections]) if sections else 0,
            "sections_by_type": self._count_by_type(sections),
            "hierarchy_depth": self._get_max_depth(document.documentOutline.nodes) if document.documentOutline else 0,
            "sections_with_h1": sum(1 for s in sections if s.h1),
            "sections_with_h2": sum(1 for s in sections if s.h2),
            "sections_with_h3": sum(1 for s in sections if s.h3),
            "avg_keywords_per_section": round(mean([len(s.keywords) for s in sections]), 1) if sections else 0
        }

    def _count_by_type(self, sections: List[Section]) -> Dict[str, int]:
        """Compte les sections par type"""
        types: Dict[str, int] = {}
        for section in sections:
            types[section.type] = types.get(section.type, 0) + 1
        return types
