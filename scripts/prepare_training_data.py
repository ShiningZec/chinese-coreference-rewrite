import argparse
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path} should contain a JSON list.")
    return data


def dump_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _span_from_item(item: dict[str, Any]) -> tuple[int, int] | None:
    """Read optional pronoun offsets if the annotation contains them."""
    start = item.get("start", item.get("pronoun_start"))
    end = item.get("end", item.get("pronoun_end"))
    if isinstance(start, int) and isinstance(end, int) and start < end:
        return start, end
    return None


def generate_rewrite(text: str, coreferences: list[dict[str, Any]]) -> str:
    """Generate a simple gold rewrite from annotated coreference pairs."""
    replacements: list[tuple[int, int, str]] = []
    cursor = 0

    for item in coreferences:
        pronoun = str(item.get("pronoun", "")).strip()
        antecedent = str(item.get("antecedent", "")).strip()
        if not pronoun or not antecedent:
            continue

        span = _span_from_item(item)
        if span is None:
            start = text.find(pronoun, cursor)
            if start < 0:
                start = text.find(pronoun)
            if start < 0:
                continue
            end = start + len(pronoun)
        else:
            start, end = span
            if text[start:end] != pronoun:
                continue

        replacements.append((start, end, antecedent))
        cursor = end

    rewritten = text
    for start, end, antecedent in sorted(replacements, reverse=True):
        rewritten = rewritten[:start] + antecedent + rewritten[end:]
    return rewritten


def normalize_sample(sample: dict[str, Any]) -> dict[str, Any]:
    text = str(sample.get("text", "")).strip()
    coreferences = sample.get("coreference", [])
    if not text:
        raise ValueError("sample missing text")
    if not isinstance(coreferences, list):
        raise ValueError(f"sample coreference should be a list: {text}")

    normalized_coreferences = []
    for item in coreferences:
        if not isinstance(item, dict):
            continue
        pronoun = str(item.get("pronoun", "")).strip()
        antecedent = str(item.get("antecedent", "")).strip()
        if pronoun and antecedent:
            normalized_coreferences.append({
                "pronoun": pronoun,
                "antecedent": antecedent,
            })

    rewrite = str(sample.get("rewrite", "")).strip()
    if not rewrite:
        rewrite = generate_rewrite(text, normalized_coreferences)

    return {
        "text": text,
        "coreference": normalized_coreferences,
        "rewrite": rewrite,
    }


def sample_key(sample: dict[str, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
    pairs = tuple(
        (item["pronoun"], item["antecedent"])
        for item in sample.get("coreference", [])
    )
    return sample["text"], pairs


def merge_samples(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen = set()
    for group in groups:
        for sample in group:
            key = sample_key(sample)
            if key in seen:
                continue
            merged.append(sample)
            seen.add(key)
    return merged


def write_summary(path: Path, source_count: int, output_count: int, missing_rewrite: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
            "# 新标注训练集接入记录",
            "",
            f"- 新标注样本数：{source_count}",
            f"- 生成 rewrite 的样本数：{missing_rewrite}",
            f"- 合并后 train.json 样本数：{output_count}",
            "",
            "说明：当前项目采用规则增强路线，不进行神经网络参数训练；"
            "这里的“训练”指把新标注样本并入训练词表，并补全可用于评估和展示的改写文本。",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare annotated samples for training.")
    parser.add_argument("--source", default="data/new_set.json", help="new annotated JSON file")
    parser.add_argument("--output", default="data/train.json", help="merged training JSON file")
    parser.add_argument("--replace", action="store_true", help="replace output instead of merging")
    args = parser.parse_args()

    source_path = BASE_DIR / args.source
    output_path = BASE_DIR / args.output
    if not source_path.exists():
        raise FileNotFoundError(f"Cannot find {source_path}")

    raw_samples = load_json(source_path)
    missing_rewrite = sum(1 for sample in raw_samples if not str(sample.get("rewrite", "")).strip())
    normalized_new = [normalize_sample(sample) for sample in raw_samples]

    existing = [] if args.replace or not output_path.exists() else load_json(output_path)
    normalized_existing = [normalize_sample(sample) for sample in existing]
    merged = merge_samples(normalized_existing, normalized_new)

    dump_json(output_path, merged)
    write_summary(
        REPORT_DIR / "training_data_summary.md",
        source_count=len(raw_samples),
        output_count=len(merged),
        missing_rewrite=missing_rewrite,
    )

    print(f"source samples: {len(raw_samples)}")
    print(f"generated rewrite: {missing_rewrite}")
    print(f"training samples: {len(merged)}")
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
