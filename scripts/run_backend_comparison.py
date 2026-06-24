import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import backend_status, evaluate, extend_lexicon_from_samples  # noqa: E402


DATASETS = {
    "dev": ROOT / "data" / "dev.json",
    "test": ROOT / "data" / "test.json",
    "real_corpus": ROOT / "data" / "real_corpus.json",
    "samples": ROOT / "data" / "samples.json",
    "train": ROOT / "data" / "train.json",
}

BACKENDS = {
    "rule_baseline": "rule",
    "hanlp": "hanlp",
    "ltp_or_legacy": "ltp",
}


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    available_datasets = {name: path for name, path in DATASETS.items() if path.exists()}
    warmup_samples: list[dict] = []
    for name in ("train", "dev"):
        path = available_datasets.get(name)
        if path is not None:
            warmup_samples.extend(load_json(path))
    extend_lexicon_from_samples(warmup_samples)

    rows: list[dict] = []
    for dataset_name, path in available_datasets.items():
        samples = load_json(path)
        baseline = evaluate(samples, backend="rule")
        for backend_label, backend in BACKENDS.items():
            info = backend_status(backend)
            result = evaluate(samples, backend=backend)
            rows.append({
                "dataset": dataset_name,
                "backend": backend_label,
                "status": "available" if info.available else "fallback",
                "accuracy": round(result.accuracy, 4),
                "precision": round(result.precision, 4),
                "recall": round(result.recall, 4),
                "f1": round(result.f1, 4),
                "delta_f1": round(result.f1 - baseline.f1, 4),
                "correct": result.correct,
                "gold": result.total_gold,
                "predicted": result.total_predicted,
                "errors": len(result.errors),
                "message": info.message,
            })

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    json_path = reports_dir / "backend_comparison.json"
    md_path = reports_dir / "backend_comparison.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 基本模型与 HanLP/LTP 对比",
        "",
        "| 数据集 | 后端 | 状态 | Precision | Recall | F1 | ΔF1 | 正确/真实 | 说明 |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['dataset']} | {row['backend']} | {row['status']} | "
            f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
            f"{row['delta_f1']:+.4f} | {row['correct']}/{row['gold']} | {row['message']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md_path)


if __name__ == "__main__":
    main()
