from dataclasses import dataclass

from .resolver import resolve_text


@dataclass(frozen=True)
class EvaluationResult:
    total: int
    correct: int
    accuracy: float


def evaluate(samples: list[dict]) -> EvaluationResult:
    """Evaluate antecedent accuracy on annotated samples."""
    total = 0
    correct = 0

    for sample in samples:
        _, _, results = resolve_text(sample["text"])
        predicted = {
            (item.pronoun.text, item.pronoun.start): item.antecedent.text
            for item in results
        }

        for gold in sample.get("coreference", []):
            key = (gold["pronoun"], gold.get("pronoun_start", -1))
            if key[1] == -1:
                matched = [
                    value
                    for (pronoun, _), value in predicted.items()
                    if pronoun == gold["pronoun"]
                ]
                is_correct = gold["antecedent"] in matched
            else:
                is_correct = predicted.get(key) == gold["antecedent"]
            total += 1
            correct += int(is_correct)

    accuracy = correct / total if total else 0.0
    return EvaluationResult(total=total, correct=correct, accuracy=round(accuracy, 4))

