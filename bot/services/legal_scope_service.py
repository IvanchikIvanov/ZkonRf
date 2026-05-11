"""Определение юридического scope: intent, страна, кодекс и тема."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


COUNTRY_NAMES = {
    "ru": "Россия",
    "kz": "Казахстан",
    "am": "Армения",
    "by": "Беларусь",
    "tj": "Таджикистан",
    "uz": "Узбекистан",
    "az": "Азербайджан",
    "thai": "Таиланд",
}

CODEX_LABELS = {
    "criminal": "уголовный кодекс",
    "civil": "гражданский кодекс",
    "labor": "трудовой кодекс",
    "koap": "КоАП",
    "family": "семейный кодекс",
    "consumer": "закон о защите прав потребителей",
    "tax": "налоговый кодекс",
    "housing": "жилищный кодекс",
    "procedural": "процессуальный кодекс",
    "unknown": "неопределенный источник",
}


class LegalScopeService:
    """Rule-based классификатор юридического intent/scope."""

    COUNTRY_PATTERNS = {
        "thai": ("таиланд", "тайланд", "thailand", "thai"),
        "ru": ("россия", "рф", "russia", "российск"),
        "kz": ("казахстан", "kazakhstan", "казахск", "рк"),
        "am": ("армения", "armenia", "армянск"),
        "by": ("беларусь", "belarus", "белорусск", "рб"),
        "tj": ("таджикистан", "tajikistan", "таджикск"),
        "uz": ("узбекистан", "uzbekistan", "узбекск"),
        "az": ("азербайджан", "azerbaijan", "азербайджанск"),
    }

    EXPLICIT_CODEX_PATTERNS = {
        "criminal": (
            "ук рф", "уголовн", "преступлен", "краж", "мошеннич", "убийств",
            "наркотик", "срок лишения", "лишение свободы",
        ),
        "civil": (
            "гк рф", "гражданск", "договор", "сделк", "неустойк",
            "взыск", "ущерб", "компенсац",
        ),
        "labor": (
            "тк рф", "трудов", "работодатель", "увол", "зарплат",
            "отпуск", "больничн", "рабочее время", "сотрудник",
        ),
        "koap": (
            "коап", "административ", "админ", "протокол",
            "постановление об административном",
        ),
        "family": ("семейн", "ск рф", "брак", "развод", "алименты", "ребенок"),
        "consumer": (
            "зозпп", "защите прав потреб", "потребител", "магазин",
            "возврат", "гаранти", "товар", "услуг",
        ),
        "tax": ("налогов", "нк рф", "налог", "ндфл", "ип"),
        "housing": ("жилищ", "жк рф", "квартира", "жкх", "управляющая компания"),
        "procedural": ("гпк", "апк", "кас", "процессуаль", "иск", "суд"),
    }

    TOPIC_PATTERNS = {
        "employment": ("увол", "работодатель", "зарплат", "отпуск", "трудов", "сотрудник"),
        "crime": ("краж", "уголов", "преступлен", "мошеннич", "лишение свободы"),
        "consumer": ("возврат", "потребител", "магазин", "гаранти", "товар", "услуг"),
        "admin_fine": ("штраф", "коап", "административ", "протокол"),
        "family": ("алименты", "развод", "брак", "ребенок", "семейн"),
        "housing": ("жкх", "квартира", "сосед", "жилищ", "управляющая компания"),
    }

    LEGAL_MARKERS = (
        "статья", "кодекс", "закон", "штраф", "суд", "иск", "права",
        "обязан", "договор", "увол", "работодатель", "зарплат", "возврат",
        "товар", "гаранти", "протокол", "наказан", "срок", "алименты",
        "развод", "краж", "наруш", "компенсац", "ответствен",
    )

    CASUAL_PATTERNS = (
        "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер",
        "как дела", "спасибо", "благодарю", "кто ты", "что умеешь",
    )

    META_PATTERNS = (
        "покажи промпт", "system prompt", "системный промпт", "покажи все статьи",
        "выведи все статьи", "dump", "экспорт базы", "как ты работаешь",
    )

    SHORT_FOLLOWUP_PATTERNS = (
        "да", "нет", "расскажи", "подробнее", "а дальше", "что дальше",
        "что делать", "про нее", "про неё", "рф", "россия", "таиланд",
    )

    def detect_scope(
        self,
        question: str,
        conversation_context: str = "",
        context_info: Optional[Dict[str, Any]] = None,
        last_scope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Вернуть intent/scope для текущего сообщения."""
        context_info = context_info or {}
        last_scope = last_scope or {}
        text = question.strip()
        lowered = text.lower()
        has_context = bool(conversation_context)

        intent = self._detect_intent(lowered, has_context)
        explicit_country = self._detect_country(lowered)
        context_country = context_info.get("country") or last_scope.get("country")
        country = explicit_country or context_country
        country_confidence = "explicit" if explicit_country else ("context" if context_country else "none")

        explicit_codex = self._detect_explicit_codex(lowered)
        inferred_codex, topic = self._detect_inferred_codex_and_topic(lowered)
        context_codex = self.normalize_codex_key(
            context_info.get("codex") or last_scope.get("codex")
        )

        if explicit_codex:
            codex = explicit_codex
            codex_confidence = "explicit"
        elif inferred_codex:
            codex = inferred_codex
            codex_confidence = "inferred"
        elif context_codex != "unknown":
            codex = context_codex
            codex_confidence = "context"
        else:
            codex = None
            codex_confidence = "none"

        if not topic:
            topic = last_scope.get("topic")

        if intent == "clarification_answer" and (explicit_country or explicit_codex):
            # Ответ на уточнение должен переиспользовать прошлую тему.
            topic = topic or last_scope.get("topic")

        return {
            "intent": intent,
            "country": country,
            "codex": codex,
            "country_confidence": country_confidence,
            "codex_confidence": codex_confidence,
            "topic": topic,
        }

    def _detect_intent(self, lowered: str, has_context: bool) -> str:
        if any(pattern in lowered for pattern in self.META_PATTERNS):
            return "unsafe_or_meta"

        compact = lowered.strip(" .,!?\n\t")
        if has_context and (
            compact in self.SHORT_FOLLOWUP_PATTERNS or len(compact) <= 12
        ):
            if self._detect_country(lowered) or self._detect_explicit_codex(lowered):
                return "clarification_answer"
            return "legal_followup"

        has_legal_marker = any(marker in lowered for marker in self.LEGAL_MARKERS)
        if has_legal_marker:
            return "legal_question"

        if any(pattern in lowered for pattern in self.CASUAL_PATTERNS):
            return "casual_chat"

        # Нейтральный fallback: лучше попытаться помочь по юридической базе, чем молча болтать.
        return "legal_question"

    def _detect_country(self, lowered: str) -> Optional[str]:
        for country_code, patterns in self.COUNTRY_PATTERNS.items():
            if any(pattern in lowered for pattern in patterns):
                return country_code
        return None

    def _detect_explicit_codex(self, lowered: str) -> Optional[str]:
        for codex_key, patterns in self.EXPLICIT_CODEX_PATTERNS.items():
            if any(pattern in lowered for pattern in patterns):
                return codex_key
        return None

    def _detect_inferred_codex_and_topic(self, lowered: str) -> tuple[Optional[str], Optional[str]]:
        topic_to_codex = {
            "employment": "labor",
            "crime": "criminal",
            "consumer": "consumer",
            "admin_fine": "koap",
            "family": "family",
            "housing": "housing",
        }
        for topic, patterns in self.TOPIC_PATTERNS.items():
            if any(pattern in lowered for pattern in patterns):
                return topic_to_codex.get(topic), topic
        return None, None

    def normalize_codex_key(self, codex_name: Optional[str]) -> str:
        """Привести имя файла/кодекса/синоним к стабильному ключу."""
        if not codex_name:
            return "unknown"

        normalized = re.sub(r"[^a-zа-я0-9]+", " ", str(codex_name).lower()).strip()
        checks = {
            "criminal": ("уголов", " uk ", "criminal", "penal"),
            "civil": ("граждан", " gk ", "civil"),
            "labor": ("труд", " tk ", "labor", "employment"),
            "koap": ("коап", " koap ", "административ", "admin"),
            "family": ("семейн", " sk ", "family"),
            "consumer": ("потреб", "зпп", "zpp", "2300", "consumer"),
            "tax": ("налог", " nk ", "tax"),
            "housing": ("жилищ", " jk ", "housing"),
            "procedural": ("гпк", "апк", "кас", "process", "procedural"),
        }
        padded = f" {normalized} "
        for codex_key, patterns in checks.items():
            if any(pattern in padded or pattern in normalized for pattern in patterns):
                return codex_key
        return "unknown"

    def infer_source_type(self, codex_name: str) -> str:
        normalized = str(codex_name).lower()
        if any(marker in normalized for marker in ("plenum", "пленум", "sudact", "суд")):
            return "plenum"
        if any(marker in normalized for marker in ("registry", "реестр")):
            return "registry"
        if self.normalize_codex_key(codex_name) != "unknown":
            return "code"
        return "law"

    def infer_topic_tags(self, codex_key: str, text: str = "") -> str:
        tags = set()
        text_lower = text.lower()
        for topic, patterns in self.TOPIC_PATTERNS.items():
            if any(pattern in text_lower for pattern in patterns):
                tags.add(topic)
        if codex_key == "labor":
            tags.add("employment")
        elif codex_key == "criminal":
            tags.add("crime")
        elif codex_key == "consumer":
            tags.add("consumer")
        elif codex_key == "koap":
            tags.add("admin_fine")
        return ",".join(sorted(tags))

    def build_enhanced_question(self, question: str, scope: Dict[str, Any]) -> str:
        parts = [question]
        country = scope.get("country")
        codex = scope.get("codex")
        topic = scope.get("topic")
        if country:
            parts.append(COUNTRY_NAMES.get(country, country))
        if codex:
            parts.append(CODEX_LABELS.get(codex, codex))
        if topic:
            parts.append(str(topic))
        return " ".join(part for part in parts if part)

    def build_scope_note(self, scope: Dict[str, Any]) -> str:
        return (
            f"LEGAL_SCOPE: country={scope.get('country')}; "
            f"codex={scope.get('codex')}; topic={scope.get('topic')}; "
            f"intent={scope.get('intent')}; "
            f"country_confidence={scope.get('country_confidence')}; "
            f"codex_confidence={scope.get('codex_confidence')}"
        )

    def build_casual_response(self, question: str) -> str:
        lowered = question.lower()
        if "спасибо" in lowered or "благодар" in lowered:
            return "Пожалуйста 🙂 Если будет юридический вопрос — разберем по статьям и шагам."
        if "что умеешь" in lowered or "кто ты" in lowered:
            return "Я помогаю разбирать юридические вопросы: ищу релевантные статьи, объясняю их простым языком и даю практические шаги."
        return "Привет 🙂 Можем спокойно обсудить ситуацию. Если есть юридический вопрос — напишите, что случилось, страну и, если знаете, кодекс."


legal_scope_service = LegalScopeService()
