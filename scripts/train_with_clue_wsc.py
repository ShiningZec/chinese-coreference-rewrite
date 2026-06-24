import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import evaluate, extend_lexicon_from_samples, extend_resolution_memory_from_samples  # noqa: E402


DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"


def load_json(path: Path) -> list[dict]:
    """Load project-format samples."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, rows: list[dict]) -> None:
    """Save project-format samples."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe_samples(samples: list[dict]) -> list[dict]:
    """Remove duplicated text/coreference pairs while preserving order."""
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    unique: list[dict] = []
    for sample in samples:
        links = tuple(
            sorted(
                (item.get("pronoun", ""), item.get("antecedent", ""))
                for item in sample.get("coreference", [])
            )
        )
        key = (sample.get("text", ""), links)
        if key in seen:
            continue
        seen.add(key)
        unique.append(sample)
    return unique


def split_samples(samples: list[dict], train_ratio: float = 0.8) -> tuple[list[dict], list[dict]]:
    """Make a deterministic train/dev split for classroom reproduction."""
    pivot = int(len(samples) * train_ratio)
    return samples[:pivot], samples[pivot:]


def metric_row(name: str, result) -> str:
    """Format one markdown metric row."""
    return (
        f"| {name} | {result.total_gold} | {result.total_predicted} | "
        f"{result.correct} | {result.precision:.4f} | {result.recall:.4f} | {result.f1:.4f} | "
        f"{len(result.errors)} |"
    )


def main() -> None:
    clue_samples = load_json(DATA_DIR / "clue_wsc.json")
    if not clue_samples:
        raise FileNotFoundError("Cannot find data/clue_wsc.json. Run scripts/convert_clue_wsc.py first.")

    base_train = load_json(DATA_DIR / "train.json")
    clue_train, clue_dev = split_samples(clue_samples)
    train_with_clue = dedupe_samples(base_train + clue_train)

    save_json(DATA_DIR / "clue_wsc_train.json", clue_train)
    save_json(DATA_DIR / "clue_wsc_dev.json", clue_dev)
    save_json(DATA_DIR / "train_with_clue_wsc.json", train_with_clue)

    before = evaluate(clue_dev)
    extend_lexicon_from_samples(train_with_clue)
    after_lexicon_clue_dev = evaluate(clue_dev)
    after_lexicon_all = evaluate(clue_samples)
    extend_resolution_memory_from_samples(train_with_clue)
    after_memory_clue_dev = evaluate(clue_dev)
    after_memory_all = evaluate(clue_samples)
    after_test = evaluate(load_json(DATA_DIR / "test.json"))
    after_real = evaluate(load_json(DATA_DIR / "real_corpus.json"))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "clue_wsc_training_report.md"
    lines = [
        "# CLUEWSC2020 训练接入报告",
        "",
        "说明：当前项目是可解释规则系统，这里的“训练”不是神经网络参数训练，",
        "而是把 CLUEWSC2020 的训练切分并入运行时 mention 词表，用公开集增强实体识别和指代候选覆盖。",
        "",
        "## 数据切分",
        "",
        f"- CLUEWSC 转换样本数：{len(clue_samples)}",
        f"- CLUEWSC 训练切分：{len(clue_train)}",
        f"- CLUEWSC 验证切分：{len(clue_dev)}",
        f"- 原项目训练样本：{len(base_train)}",
        f"- 合并训练样本：{len(train_with_clue)}",
        "",
        "## 指标对比",
        "",
        "| 数据集 | Gold | Pred | Correct | Precision | Recall | F1 | Error Samples |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        metric_row("CLUE dev 接入前", before),
        metric_row("CLUE dev 仅扩词表后", after_lexicon_clue_dev),
        metric_row("CLUE 全量仅扩词表后", after_lexicon_all),
        metric_row("CLUE dev 记忆增强后", after_memory_clue_dev),
        metric_row("CLUE 全量记忆增强后", after_memory_all),
        metric_row("项目 test 接入后", after_test),
        metric_row("真实语料 real_corpus 接入后", after_real),
        "",
        "## 可写入报告的结论",
        "",
        "- 公开集接入后，系统获得了更多真实中文指代样式，尤其是“它们/他们/其/该实体”等表达。",
        "- CLUEWSC 更偏 Winograd Schema，很多样本需要常识语义推理；规则系统只能提升候选覆盖，不能完全解决深层语义判断。",
        "- 记忆增强会显著提高训练集相关指标，但这属于 supervised exact-match fitting，应与验证集泛化结果分开汇报。",
        "- 因此该实验适合放在“公开数据集扩展”和“局限性分析”中：它证明系统可以接入公开语料，也说明后续需要 BERT/语义匹配模型。",
        "",
        "## 生成文件",
        "",
        "- `data/clue_wsc_train.json`",
        "- `data/clue_wsc_dev.json`",
        "- `data/train_with_clue_wsc.json`",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(report_path)
    print(f"CLUE samples: {len(clue_samples)}")
    print(f"CLUE train/dev: {len(clue_train)}/{len(clue_dev)}")
    print(f"merged train: {len(train_with_clue)}")
    print(f"CLUE dev F1 before/lexicon/memory: {before.f1:.4f}/{after_lexicon_clue_dev.f1:.4f}/{after_memory_clue_dev.f1:.4f}")
    print(f"CLUE all F1 lexicon/memory: {after_lexicon_all.f1:.4f}/{after_memory_all.f1:.4f}")


if __name__ == "__main__":
    main()
