import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(
    r"C:\Users\30657\Desktop\CLUE-master\baselines\models_pytorch\classifier_pytorch\CLUEdatasets\wsc"
)


def read_jsonl(path: Path) -> list[dict]:
    """Read CLUEWSC jsonl records."""
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_rewrite(text: str, coreference: list[dict]) -> str:
    """Rewrite true CLUEWSC links by replacing pronouns with antecedents."""
    replacements = []
    for item in coreference:
        start = item.get("pronoun_index")
        pronoun = item["pronoun"]
        antecedent = item["antecedent"]
        if isinstance(start, int) and text[start : start + len(pronoun)] == pronoun:
            replacements.append((start, start + len(pronoun), antecedent))
    rewritten = text
    for start, end, value in sorted(replacements, reverse=True):
        rewritten = rewritten[:start] + value + rewritten[end:]
    return rewritten


def convert_records(records: list[dict]) -> tuple[list[dict], dict]:
    """Convert CLUEWSC records into the project JSON format."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    label_counter: Counter[str] = Counter()
    for record in records:
        label_counter[str(record.get("label", "")).lower()] += 1
        grouped[record["text"]].append(record)

    converted: list[dict] = []
    for text, group in grouped.items():
        links = []
        negatives = []
        for record in group:
            target = record["target"]
            item = {
                "pronoun": target["span2_text"],
                "antecedent": target["span1_text"],
                "pronoun_index": target.get("span2_index"),
                "antecedent_index": target.get("span1_index"),
            }
            if str(record.get("label", "")).lower() == "true":
                links.append(item)
            else:
                negatives.append(item)
        if not links:
            continue
        sample = {
            "text": text,
            "coreference": [
                {"pronoun": item["pronoun"], "antecedent": item["antecedent"]}
                for item in links
            ],
            "rewrite": build_rewrite(text, links),
            "source": "CLUEWSC2020",
            "negative_candidates": [
                {"pronoun": item["pronoun"], "antecedent": item["antecedent"]}
                for item in negatives
            ],
        }
        converted.append(sample)

    stats = {
        "raw_records": len(records),
        "unique_texts": len(grouped),
        "converted_samples": len(converted),
        "label_counts": dict(label_counter),
        "gold_links": sum(len(sample["coreference"]) for sample in converted),
        "negative_candidates": sum(len(sample["negative_candidates"]) for sample in converted),
    }
    return converted, stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--split", default="train", choices=["train", "dev", "test1.0"])
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "clue_wsc.json")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "clue_wsc_conversion.md")
    args = parser.parse_args()

    source_file = args.source_dir / f"{args.split}.json"
    records = read_jsonl(source_file)
    converted, stats = convert_records(records)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# CLUEWSC2020 转换结果",
        "",
        f"- 来源文件：`{source_file}`",
        f"- 输出文件：`{args.output}`",
        f"- 原始记录数：{stats['raw_records']}",
        f"- 唯一文本数：{stats['unique_texts']}",
        f"- 转换样本数：{stats['converted_samples']}",
        f"- gold 指代关系数：{stats['gold_links']}",
        f"- negative candidates：{stats['negative_candidates']}",
        f"- 标签分布：{stats['label_counts']}",
        "",
        "说明：仅将 `label=true` 的候选关系转为本项目的 gold coreference；`label=false` 保留为 negative_candidates，不参与当前 F1 计算。",
    ]
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    print(args.report)
    print(stats)


if __name__ == "__main__":
    main()
