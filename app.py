import json
from pathlib import Path
from typing import Any, Dict, List, Self  # noqa: F401

import streamlit as st

from src import (
    annote,  # annotator
    backend_status,  # nlp_backend
    bind_ref,  # annotator
    Coreference,  # annotator
    CoreferenceResult,  # after_resolve
    ErrorCase,  # after_evaluate
    evaluate,  # after_evaluate
    extend_lexicon_from_samples,  # mention_extractor
    Paragraph,  # annotator
    RawdataGather,  # data gather(not implemented yet)
    ResolverConfig,  # after_resolve
    resolve_text,  # after_resolve
    rewrite_text,  # after_rewrite
)


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATASETS = {
    "演示集 demo": DATA_DIR / "demo.json",
    "开发集 dev": DATA_DIR / "dev.json",
    "测试集 test": DATA_DIR / "test.json",
    "真实语料 real_corpus": DATA_DIR / "real_corpus.json",
    "完整样本 samples": DATA_DIR / "samples.json",
}
BACKENDS = {
    "规则版 baseline": "rule",
    "HanLP 增强接口": "hanlp",
    "LTP 增强接口": "ltp",
}
RG = RawdataGather(DATA_DIR)


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def render_highlighted_text(text: str, results: list[CoreferenceResult]) -> str:
    spans = []
    for result in results:
        spans.append((result.antecedent.start, result.antecedent.end, "entity"))
        spans.append((result.pronoun.start, result.pronoun.end, "pronoun"))

    html = ""
    cursor = 0
    for start, end, kind in sorted(spans, key=lambda item: item[0]):
        if start < cursor:
            continue
        html += text[cursor:start]
        color = "#d8f3dc" if kind == "entity" else "#775c2a"
        html += (
            f"<mark style='background:{color};padding:2px 4px;"
            f"border-radius:4px'>{text[start:end]}</mark>"
        )
        cursor = end
    html += text[cursor:]
    return html


def render_highlighted_rawtext(text, s=None, t=None, ref_s=None, ref_t=None):
    pieces = []
    for i, ch in enumerate(text):
        if s is not None and s <= i < t:
            pieces.append(f"<span style='background:#9b7022'>{ch}</span>")
        elif ref_s is not None and ref_s <= i < ref_t:
            pieces.append(f"<span style='background:#20642a'>{ch}</span>")
        else:
            pieces.append(ch)

    return "".join(pieces)


def relation_rows(results: list[CoreferenceResult]) -> list[dict]:
    return [
        {
            "代词": item.pronoun.text,
            "先行词": item.antecedent.text,
            "分数": item.score,
            "是否歧义": "是" if item.ambiguous else "否",
            "理由": "；".join(item.candidates[0].reasons),
        }
        for item in results
    ]


def ambiguous_rows(results: list[CoreferenceResult]) -> list[dict]:
    rows = []
    for item in results:
        if not item.ambiguous:
            continue
        rows.append({
            "代词": item.pronoun.text,
            "可能先行词": " / ".join(candidate.candidate.text for candidate in item.candidates[:2]),
            "说明": "候选分数接近，建议人工确认后再改写。",
        })
    return rows


def candidate_rows(results: list[CoreferenceResult]) -> list[dict]:
    rows = []
    for result in results:
        for candidate in result.candidates:
            rows.append({
                "代词": candidate.pronoun.text,
                "候选实体": candidate.candidate.text,
                "类型": candidate.candidate.label,
                "分数": candidate.score,
                "规则说明": "；".join(candidate.reasons),
            })
    return rows


def error_rows(errors: list[ErrorCase]) -> list[dict]:
    return [
        {
            "错误类型": "；".join(item.error_types) or "未分类",
            "原文": item.text,
            "真实关系": "；".join(f"{p}->{a}" for p, a in item.gold),
            "预测关系": "；".join(f"{p}->{a}" for p, a in item.predicted) or "无",
            "漏判": "；".join(f"{p}->{a}" for p, a in item.missing) or "无",
            "误判": "；".join(f"{p}->{a}" for p, a in item.extra) or "无",
        }
        for item in errors
    ]


st.set_page_config(page_title="中文指代消解与句子改写系统", layout="wide")
st.title("中文指代消解与句子改写系统")

backend_label = st.sidebar.selectbox("NLP 后端", list(BACKENDS.keys()))
backend = BACKENDS[backend_label]
info = backend_status(backend)
if info.available:
    st.sidebar.success(info.message)
else:
    st.sidebar.warning(info.message)
    st.sidebar.caption("当前仍使用规则版 baseline，后续安装模型后可接入真实抽取结果。")

demo_samples = load_json(DATASETS["演示集 demo"])
dev_samples = load_json(DATASETS["开发集 dev"])
train_path = DATA_DIR / "train.json"
train_samples = load_json(train_path) if train_path.exists() else []
extend_lexicon_from_samples(train_samples + demo_samples + dev_samples)
analysis_tab, evaluation_tab, ablation_tab, annotator_tab = st.tabs([
    "单文本分析",
    "数据集评估",
    "消融实验",
    "数据标注",
])

with analysis_tab:
    selected_sample = st.selectbox(
        "示例文本",
        ["自定义输入"] + [sample["text"] for sample in demo_samples],
    )
    default_text = (
        demo_samples[0]["text"] if selected_sample == "自定义输入" else selected_sample
    )
    text = st.text_area("输入中文文本", default_text, height=130)

    if st.button("开始分析", type="primary"):
        entities, pronouns, results = resolve_text(text, backend=backend)
        rewritten = rewrite_text(text, results)

        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("原文高亮")
            st.markdown(render_highlighted_text(text, results), unsafe_allow_html=True)
            st.subheader("改写结果")
            if any(result.ambiguous for result in results):
                st.warning("检测到指代歧义，歧义代词已跳过自动改写。")
            st.success(rewritten)

        with right:
            st.subheader("识别结果")
            st.write(
                f"候选实体：{', '.join(entity.text for entity in entities) or '无'}"
            )
            st.write(f"代词：{', '.join(pronoun.text for pronoun in pronouns) or '无'}")

            st.subheader("指代关系")
            rows = relation_rows(results)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
                ambiguities = ambiguous_rows(results)
                if ambiguities:
                    st.warning("该文本存在多种可能解释。")
                    st.dataframe(ambiguities, use_container_width=True, hide_index=True)
            else:
                st.info("暂未识别到可消解的指代关系。")

        st.subheader("候选实体得分")
        candidates = candidate_rows(results)
        if candidates:
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        else:
            st.info("暂无候选实体得分。")

with evaluation_tab:
    dataset_name = st.selectbox("选择评估数据集", list(DATASETS.keys()), index=2)
    samples = load_json(DATASETS[dataset_name])
    result = evaluate(samples, backend=backend)

    st.subheader("评估指标")
    cols = st.columns(5)
    cols[0].metric("Accuracy", f"{result.accuracy:.2%}")
    cols[1].metric("Precision", f"{result.precision:.2%}")
    cols[2].metric("Recall", f"{result.recall:.2%}")
    cols[3].metric("F1", f"{result.f1:.2%}")
    cols[4].metric("正确/真实", f"{result.correct}/{result.total_gold}")

    st.caption(f"预测关系数：{result.total_predicted}，样本数：{len(samples)}")

    st.subheader("错误分析")
    rows = error_rows(result.errors)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.success("当前数据集没有错误样本。")

with ablation_tab:
    st.subheader("规则消融实验")
    ablation_dataset = st.selectbox(
        "选择消融数据集",
        ["测试集 test", "真实语料 real_corpus", "完整样本 samples"],
        index=1,
    )
    ablation_map = {
        "测试集 test": DATASETS["测试集 test"],
        "真实语料 real_corpus": DATASETS["真实语料 real_corpus"],
        "完整样本 samples": DATASETS["完整样本 samples"],
    }
    samples = load_json(ablation_map[ablation_dataset])
    experiments = [
        ("完整规则", ResolverConfig()),
        ("去掉距离规则", ResolverConfig(use_distance=False)),
        ("去掉位置规则", ResolverConfig(use_position=False)),
        ("去掉类型规则", ResolverConfig(use_type=False)),
        ("去掉性别规则", ResolverConfig(use_gender=False)),
        ("仅距离+位置", ResolverConfig(use_type=False, use_gender=False)),
        ("仅类型+性别", ResolverConfig(use_distance=False, use_position=False)),
    ]
    baseline = evaluate(samples, backend=backend)
    rows = []
    for name, config in experiments:
        result = evaluate(samples, backend=backend, config=config)
        rows.append({
            "实验": name,
            "正确/真实": f"{result.correct}/{result.total_gold}",
            "Precision": result.precision,
            "Recall": result.recall,
            "F1": result.f1,
            "ΔF1": round(result.f1 - baseline.f1, 4),
            "错误样本": len(result.errors),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "消融实验用于观察每类规则信号对最终效果的贡献，可直接作为报告中的实验补充。"
    )


if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

if "annotations" not in st.session_state:
    st.session_state.annotations = []

if "paras" not in st.session_state:
    st.session_state.paras = {}

if "results" not in st.session_state:
    st.session_state.results = RG.gather()
    
results = st.session_state.results

with annotator_tab:
    st.subheader("数据标注器")

    if st.button("Prev"):
        st.session_state.annotations = []
        st.session_state.current_idx -= 1
        if st.session_state.current_idx < 0:
            st.session_state.current_idx = 0
        idx = st.session_state.current_idx
        text = results[idx]
    if st.button("Next"):
        st.session_state.annotations = []
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(results):
            st.session_state.current_idx = len(results) - 1
        idx = st.session_state.current_idx
        text = results[idx]
    
    input_file = st.text_input("数据来源", "")
    if st.button("读取输入"):
        st.session_state.results = RG.gather(input_file)
        st.session_state.current_idx = 0
    results: List[str] = st.session_state.results

    idx = st.session_state.current_idx
    text = results[idx]

    # 展示文本
    text = st.text_input("文本修改", text)
    text_with_index = " ".join(f"{i:02d}:{c}" for i, c in enumerate(text))
    st.code(text_with_index)

    n = len(text)
    s, t, ref_s, ref_t = None, None, None, None
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        s = st.number_input("s", min_value=0, max_value=n - 1, value=0, step=1)
    with col2:
        t = st.number_input(
            "t", min_value=s + 1, max_value=n, value=min(s + 1, n), step=1
        )
    with col3:
        ref_s = st.number_input("ref_s", min_value=0, max_value=n - 1, value=0, step=1)
    with col4:
        ref_t = st.number_input(
            "ref_t", min_value=ref_s + 1, max_value=n, value=min(ref_s + 1, n), step=1
        )
    text_renderer = st.markdown(
        render_highlighted_rawtext(text, s, t, ref_s, ref_t), unsafe_allow_html=True
    )

    st.write("pronoun:", text[s:t])
    st.write("antecedent:", text[ref_s:ref_t])

    if st.button("添加标注"):
        c: Coreference = annote(text, s, t, ref_s, ref_t)
        st.session_state.annotations.append(c)

    st.write("已有标注")
    for i, c in enumerate(st.session_state.annotations):
        st.write(f"{i + 1}. {c.pronoun} -> {c.antecedent}")

    if st.button("绑定当前文本"):
        para: Paragraph = bind_ref(text, st.session_state.annotations)
        st.session_state.paras[idx] = para
        st.session_state.annotations = []
        st.success("已绑定")

    dump_to: str = st.text_input("Where to dump to?", "test_dump")

    if st.button("Dump"):
        if not dump_to.endswith(".json"):
            dump_to = dump_to + ".json"
        RG.dump(
            st.session_state.paras.values(),
            filename=dump_to,
        )
        st.success(f"Dump {len(st.session_state.paras)} paragraphs to {dump_to}.")
