import json
from pathlib import Path

import streamlit as st

from src.evaluator import evaluate
from src.resolver import CoreferenceResult, resolve_text
from src.rewriter import rewrite_text


BASE_DIR = Path(__file__).parent
SAMPLES_PATH = BASE_DIR / "data" / "samples.json"


def load_samples() -> list[dict]:
    with SAMPLES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def render_highlighted_text(text: str, results: list[CoreferenceResult]) -> str:
    spans = []
    for result in results:
        spans.append((result.antecedent.start, result.antecedent.end, "entity"))
        spans.append((result.pronoun.start, result.pronoun.end, "pronoun"))

    spans = sorted(spans, key=lambda item: item[0])
    html = ""
    cursor = 0
    for start, end, kind in spans:
        if start < cursor:
            continue
        html += text[cursor:start]
        color = "#d8f3dc" if kind == "entity" else "#ffe5b4"
        html += f"<mark style='background:{color};padding:2px 4px;border-radius:4px'>{text[start:end]}</mark>"
        cursor = end
    html += text[cursor:]
    return html


def result_table(results: list[CoreferenceResult]) -> list[dict]:
    return [
        {
            "代词": item.pronoun.text,
            "先行词": item.antecedent.text,
            "分数": item.score,
            "理由": "；".join(item.candidates[0].reasons),
        }
        for item in results
    ]


def candidate_table(results: list[CoreferenceResult]) -> list[dict]:
    rows = []
    for result in results:
        for candidate in result.candidates:
            rows.append(
                {
                    "代词": candidate.pronoun.text,
                    "候选实体": candidate.candidate.text,
                    "类型": candidate.candidate.label,
                    "分数": candidate.score,
                    "规则说明": "；".join(candidate.reasons),
                }
            )
    return rows


st.set_page_config(page_title="中文指代消解与句子改写系统", layout="wide")
st.title("中文指代消解与句子改写系统")

samples = load_samples()
sample_options = ["自定义输入"] + [sample["text"] for sample in samples]
selected = st.selectbox("示例文本", sample_options)

default_text = samples[0]["text"] if selected == "自定义输入" else selected
text = st.text_area("输入中文文本", default_text, height=130)

if st.button("开始分析", type="primary"):
    entities, pronouns, results = resolve_text(text)
    rewritten = rewrite_text(text, results)

    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("原文高亮")
        st.markdown(render_highlighted_text(text, results), unsafe_allow_html=True)

        st.subheader("改写结果")
        st.success(rewritten)

    with right:
        st.subheader("识别结果")
        st.write(f"候选实体：{', '.join(entity.text for entity in entities) or '无'}")
        st.write(f"代词：{', '.join(pronoun.text for pronoun in pronouns) or '无'}")

        st.subheader("指代关系")
        table = result_table(results)
        if not table:
            st.info("暂未识别到可消解的指代关系。")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True)

    st.subheader("候选实体得分")
    candidates = candidate_table(results)
    if not candidates:
        st.info("暂无候选实体得分。")
    else:
        st.dataframe(candidates, use_container_width=True, hide_index=True)

st.divider()
st.subheader("样本集基础评估")
evaluation = evaluate(samples)
st.metric("Accuracy", f"{evaluation.accuracy:.2%}", f"{evaluation.correct}/{evaluation.total}")
