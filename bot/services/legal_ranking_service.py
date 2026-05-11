"""Ранжирование найденных статей и решение, нужно ли уточнение."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from bot.services.legal_scope_service import CODEX_LABELS, COUNTRY_NAMES, legal_scope_service


class LegalRankingService:
    """Мягкое ранжирование поверх vector search."""

    def rank(
        self,
        question: str,
        articles: List[Dict[str, Any]],
        scope: Dict[str, Any],
        max_articles: int = 5,
    ) -> Dict[str, Any]:
        if not articles:
            return {
                "articles": [],
                "needs_clarification": False,
                "clarification": None,
            }

        ranked = []
        for article in articles:
            normalized = dict(article)
            codex_key = normalized.get("codex_key") or legal_scope_service.normalize_codex_key(
                normalized.get("codex_name")
            )
            normalized["codex_key"] = codex_key
            normalized["rerank_score"] = self._score_article(normalized, scope)
            ranked.append(normalized)

        ranked.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
        relevant = self._keep_relevant(ranked)

        clarification = self._build_clarification(relevant, scope)
        if clarification:
            return {
                "articles": relevant[:max_articles],
                "needs_clarification": True,
                "clarification": clarification,
            }

        return {
            "articles": relevant[:max_articles],
            "needs_clarification": False,
            "clarification": None,
        }

    def _score_article(self, article: Dict[str, Any], scope: Dict[str, Any]) -> float:
        distance = article.get("distance")
        if distance is None:
            score = 0.5
        else:
            try:
                score = max(0.0, 1.0 - float(distance))
            except (TypeError, ValueError):
                score = 0.5

        scope_country = scope.get("country")
        if scope_country:
            score += 0.15 if article.get("country") == scope_country else -0.25

        scope_codex = scope.get("codex")
        codex_confidence = scope.get("codex_confidence")
        article_codex = article.get("codex_key")
        if scope_codex:
            if article_codex == scope_codex:
                score += 0.55 if codex_confidence == "explicit" else 0.25
            elif codex_confidence == "explicit":
                score -= 0.45
            else:
                score -= 0.05

        topic = scope.get("topic")
        topic_tags = article.get("topic_tags") or ""
        if topic and topic in topic_tags:
            score += 0.12

        return score

    def _keep_relevant(self, ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        strict = []
        for article in ranked:
            distance = article.get("distance")
            if distance is None:
                strict.append(article)
                continue
            try:
                if float(distance) < 0.85:
                    strict.append(article)
            except (TypeError, ValueError):
                strict.append(article)

        if len(strict) >= 3:
            return strict[:10]
        return ranked[:5]

    def _build_clarification(
        self,
        articles: List[Dict[str, Any]],
        scope: Dict[str, Any],
    ) -> Optional[str]:
        if len(articles) < 2:
            return None

        country_confidence = scope.get("country_confidence")
        if country_confidence == "none":
            country_scores = self._group_scores(articles, "country")
            countries = list(country_scores.items())
            if self._groups_are_close(countries):
                labels = [
                    COUNTRY_NAMES.get(country, str(country))
                    for country, _ in countries[:3]
                    if country
                ]
                if len(labels) > 1:
                    return (
                        "Тут нормы могут отличаться по странам. "
                        f"Какую страну смотрим: {', '.join(labels)}?"
                    )

        codex_confidence = scope.get("codex_confidence")
        if codex_confidence in ("none", "inferred"):
            codex_scores = self._group_scores(articles, "codex_key")
            codexes = [
                item for item in codex_scores.items()
                if item[0] and item[0] != "unknown"
            ]
            if self._groups_are_close(codexes):
                labels = [CODEX_LABELS.get(codex, codex) for codex, _ in codexes[:3]]
                if len(labels) > 1:
                    return (
                        "Тут возможны разные правовые режимы: "
                        f"{', '.join(labels)}. "
                        "Уточните, пожалуйста, о каком именно варианте речь?"
                    )

        return None

    def _group_scores(self, articles: List[Dict[str, Any]], key: str) -> Dict[str, float]:
        scores: Dict[str, float] = defaultdict(float)
        for article in articles[:8]:
            group_key = str(article.get(key) or "")
            if not group_key:
                continue
            scores[group_key] += float(article.get("rerank_score", 0.0))
        return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))

    def _groups_are_close(self, groups: List[tuple[str, float]]) -> bool:
        if len(groups) < 2:
            return False
        top = groups[0][1]
        second = groups[1][1]
        if top <= 0:
            return False
        return (top - second) <= 0.18


legal_ranking_service = LegalRankingService()
