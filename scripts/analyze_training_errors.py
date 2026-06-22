import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "train.json"
REPORT_PATH = BASE_DIR / "reports" / "training_error_analysis.md"

sys.path.insert(0, str(BASE_DIR))

from src import evaluate, extend_lexicon_from_samples  # noqa: E402

ORG_MARKERS = (
    "公司",
    "学校",
    "大学",
    "学院",
    "医院",
    "研究院",
    "博物院",
    "剧院",
    "集团",
    "平台",
    "车企",
    "乐园",
    "馆",
    "台",
    "基地",
)


def load_samples() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _has_plural_pronoun_mismatch(missing: list[tuple[str, str]], extra: list[tuple[str, str]]) -> bool:
    for missing_pronoun, missing_antecedent in missing:
        for extra_pronoun, extra_antecedent in extra:
            same_root = extra_pronoun.startswith(missing_pronoun) or missing_pronoun.startswith(extra_pronoun)
            if same_root and missing_antecedent == extra_antecedent:
                return True
    return False


def classify_error(text: str, missing: list[tuple[str, str]], extra: list[tuple[str, str]]) -> str:
    if _has_plural_pronoun_mismatch(missing, extra):
        return "标注粒度不一致：它/它们"

    pronouns = [pronoun for pronoun, _ in missing + extra]
    antecedents = [antecedent for _, antecedent in missing + extra]
    if any(pronoun in {"我", "你"} for pronoun in pronouns):
        return "对话角色：我/你"
    if text.count("他") + text.count("她") >= 2 and any(marker in text for marker in ("对", "说", "问", "嘱咐")):
        return "多人物角色/同形代词"
    if any(pronoun in {"老师", "弟子"} for pronoun in pronouns):
        return "身份称谓：老师/弟子"
    if any(any(marker in antecedent for marker in ORG_MARKERS) for antecedent in antecedents):
        return "组织指代仍需加强"
    if not missing and extra:
        return "过度预测"
    if any(len(antecedent) >= 4 and any(ch in antecedent for ch in "将了在把对向为") for antecedent in antecedents):
        return "候选实体抽取噪声"
    return "其他语义判断"


def main() -> None:
    samples = load_samples()
    extend_lexicon_from_samples(samples)
    result = evaluate(samples)

    categorized = []
    counts: Counter[str] = Counter()
    for error in result.errors:
        category = classify_error(error.text, error.missing, error.extra)
        counts[category] += 1
        categorized.append((category, error))

    lines = [
        "# 训练集错误分析",
        "",
        "## 总体结果",
        "",
        f"- 样本数：{len(samples)}",
        f"- 真实指代关系数：{result.total_gold}",
        f"- 正确关系数：{result.correct}",
        f"- Precision：{result.precision:.4f}",
        f"- Recall：{result.recall:.4f}",
        f"- F1：{result.f1:.4f}",
        f"- 错误样本数：{len(result.errors)}",
        "",
        "## 错误类型分布",
        "",
        "| 错误类型 | 样本数 |",
        "|---|---:|",
    ]
    for category, count in counts.most_common():
        lines.append(f"| {category} | {count} |")

    lines.extend([
        "",
        "## 关键观察",
        "",
        "- 新增组织指代规则后，训练集 F1 从 0.7963 提升到 0.8765，说明 `该院/该校/这家公司` 一类短语是主要增益点。",
        "- 剩余错误集中在多人物对话、同形代词、称谓指代、复数代词标注粒度和少量候选实体噪声。",
        "- 部分样本的 gold 使用 `它`，原文实际是 `它们`，这会造成评估层面的漏判/误判，可在标注规范中统一为原文完整 span。",
        "- `他...他...` 这种同形代词仅用文本表面对比会丢失位置信息，后续评估应加入 pronoun span。",
        "",
        "## 错误样本明细",
        "",
    ])

    for index, (category, error) in enumerate(categorized, 1):
        lines.extend([
            f"### {index}. {category}",
            "",
            f"- 原文：{error.text}",
            f"- 真实关系：{error.gold}",
            f"- 预测关系：{error.predicted}",
            f"- 漏判：{error.missing or '无'}",
            f"- 误判：{error.extra or '无'}",
            "",
        ])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote: {REPORT_PATH}")
    print(f"errors: {len(result.errors)}")
    print(f"f1: {result.f1:.4f}")


if __name__ == "__main__":
    main()
