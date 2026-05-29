from .resolver import CoreferenceResult


def rewrite_text(text: str, results: list[CoreferenceResult]) -> str:
    """Replace resolved pronouns with their antecedents."""
    rewritten = text
    for result in sorted(results, key=lambda item: item.pronoun.start, reverse=True):
        rewritten = (
            rewritten[: result.pronoun.start]
            + result.antecedent.text
            + rewritten[result.pronoun.end :]
        )
    return rewritten

