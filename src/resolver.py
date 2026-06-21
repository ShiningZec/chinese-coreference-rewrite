from dataclasses import dataclass

from .mention_extractor import Mention, extract_mentions


@dataclass(frozen=True)
class ResolverConfig:
    use_distance: bool = True
    use_position: bool = True
    use_type: bool = True
    use_gender: bool = True
    ambiguity_margin: float = 0.15


DEFAULT_CONFIG = ResolverConfig()


@dataclass(frozen=True)
class CandidateScore:
    pronoun: Mention
    candidate: Mention
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class CoreferenceResult:
    pronoun: Mention
    antecedent: Mention
    score: float
    candidates: list[CandidateScore]
    ambiguous: bool = False


def _type_score(pronoun: Mention, candidate: Mention) -> tuple[float, str]:
    if pronoun.label == "PERSON_PRONOUN" and candidate.label == "PERSON":
        return 0.45, "type match"
    if pronoun.label == "OBJECT_PRONOUN" and candidate.label == "OBJECT":
        return 0.45, "type match"
    if pronoun.label == "ORG_PRONOUN" and candidate.label == "ORG":
        return 0.5, "type match"
    if pronoun.label == "OBJECT_PRONOUN" and candidate.label in {"ORG", "PERSON"}:
        return -0.2, "type mismatch"
    if pronoun.label == "PERSON_PRONOUN" and candidate.label != "PERSON":
        return -0.2, "type mismatch"
    return 0.0, "weak type signal"


def _gender_score(pronoun: Mention, candidate: Mention) -> tuple[float, str]:
    if pronoun.gender in {"unknown", "neutral"} or candidate.gender == "unknown":
        return 0.05, "gender unknown"
    if pronoun.gender == candidate.gender:
        return 0.25, "gender match"
    return -0.35, "gender mismatch"


def score_candidate(
    pronoun: Mention,
    candidate: Mention,
    config: ResolverConfig = DEFAULT_CONFIG,
) -> CandidateScore:
    """Score one candidate antecedent for one pronoun."""
    distance = max(pronoun.start - candidate.end, 0)
    distance_score = max(0.0, 0.3 - distance / 80) if config.use_distance else 0.0
    position_score = (0.15 if candidate.end <= pronoun.start else -0.4) if config.use_position else 0.0

    if config.use_type:
        type_value, type_reason = _type_score(pronoun, candidate)
    else:
        type_value, type_reason = 0.0, "type disabled"

    if config.use_gender:
        gender_value, gender_reason = _gender_score(pronoun, candidate)
    else:
        gender_value, gender_reason = 0.0, "gender disabled"

    score = distance_score + position_score + type_value + gender_value
    reasons = [
        f"distance={distance}",
        type_reason,
        gender_reason,
        "before pronoun" if candidate.end <= pronoun.start else "after pronoun",
    ]
    return CandidateScore(pronoun, candidate, round(score, 4), reasons)


def _interaction_alternatives(
    text: str,
    pronoun_index: int,
    pronouns: list[Mention],
    entities: list[Mention],
) -> list[Mention] | None:
    """Return two plausible people for ambiguous speaker-object patterns."""
    pronoun = pronouns[pronoun_index]
    if pronoun.label != "PERSON_PRONOUN":
        return None

    first_index = None
    if pronoun_index + 1 < len(pronouns):
        next_pronoun = pronouns[pronoun_index + 1]
        if (
            text[pronoun.end : next_pronoun.start] in {"对", "向", "跟"}
            and text[next_pronoun.end : next_pronoun.end + 1] in {"说", "讲", "问"}
        ):
            first_index = pronoun_index
    if pronoun_index > 0:
        previous = pronouns[pronoun_index - 1]
        if (
            text[previous.end : pronoun.start] in {"对", "向", "跟"}
            and text[pronoun.end : pronoun.end + 1] in {"说", "讲", "问"}
        ):
            first_index = pronoun_index - 1

    if first_index is None:
        return None

    people = [entity for entity in entities if entity.label == "PERSON" and entity.end <= pronoun.start]
    if len(people) < 2:
        return None

    subject, obj = people[-2], people[-1]
    between = text[subject.end : obj.start]
    if not any(marker in between for marker in ("会见", "看见", "遇见", "拜访", "采访", "邀请", "找到")):
        return None

    if pronoun_index == first_index:
        return [subject, obj]
    return [obj, subject]


def _benefactive_override(
    text: str,
    pronoun: Mention,
    entities: list[Mention],
) -> Mention | None:
    """Resolve A helps/acts-for B patterns using the beneficiary marker."""
    if pronoun.label != "PERSON_PRONOUN":
        return None

    people = [entity for entity in entities if entity.label == "PERSON" and entity.end <= pronoun.start]
    if len(people) < 2:
        return None

    subject, beneficiary = people[-2], people[-1]
    between = text[subject.end : beneficiary.start]
    if not any(marker in between for marker in ("替", "帮", "为")):
        return None

    previous_char = text[pronoun.start - 1 : pronoun.start]
    if previous_char in {"替", "帮", "为"}:
        return beneficiary
    return subject


def resolve_text(
    text: str,
    backend: str = "rule",
    config: ResolverConfig = DEFAULT_CONFIG,
) -> tuple[list[Mention], list[Mention], list[CoreferenceResult]]:
    """Resolve coreference links with a lightweight rule-based strategy."""
    entities, pronouns = extract_mentions(text, backend=backend)
    results: list[CoreferenceResult] = []

    for index, pronoun in enumerate(pronouns):
        candidates = [
            entity
            for entity in entities
            if entity.end <= pronoun.start
            or (pronoun.start <= entity.start and entity.end <= pronoun.end)
        ]
        scored = sorted(
            [score_candidate(pronoun, candidate, config=config) for candidate in candidates],
            key=lambda item: item.score,
            reverse=True,
        )
        override = _benefactive_override(text, pronoun, entities)
        if override is not None:
            override_score = CandidateScore(
                pronoun=pronoun,
                candidate=override,
                score=1.1,
                reasons=["benefactive pattern", "role marker before beneficiary"],
            )
            scored = [override_score] + [item for item in scored if item.candidate != override]

        alternatives = _interaction_alternatives(text, index, pronouns, entities)
        if alternatives is not None:
            alternative_scores = [
                CandidateScore(
                    pronoun=pronoun,
                    candidate=alternative,
                    score=1.0,
                    reasons=["ambiguous interaction pattern", "manual confirmation needed"],
                )
                for alternative in alternatives
            ]
            scored = alternative_scores + [
                item for item in scored if item.candidate not in alternatives
            ]

        if scored and scored[0].score > 0:
            ambiguous = (
                len(scored) > 1
                and scored[0].score - scored[1].score <= config.ambiguity_margin
            )
            results.append(
                CoreferenceResult(
                    pronoun=pronoun,
                    antecedent=scored[0].candidate,
                    score=scored[0].score,
                    candidates=scored,
                    ambiguous=ambiguous,
                )
            )

    return entities, pronouns, results
