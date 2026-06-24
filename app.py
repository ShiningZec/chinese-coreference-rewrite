import json
from pathlib import Path
from typing import Any, Dict, List, Self  # noqa: F401

import streamlit as st

from src import (
    annote,  # annotator
    backend_status,  # nlp_backend
    bind_ref,  # annotator
    clean_news_text,  # document_resolver
    Coreference,  # annotator
    CoreferenceResult,  # after_resolve
    ErrorCase,  # after_evaluate
    evaluate,  # after_evaluate
    extend_lexicon_from_samples,  # mention_extractor
    extend_resolution_memory_from_samples,  # resolver
    Paragraph,  # annotator
    RawdataGather,  # data gather(not implemented yet)
    ResolverConfig,  # after_resolve
    resolve_news_document,  # document_resolver
    resolve_text,  # after_resolve
    rewrite_text,  # after_rewrite
    split_news_articles,  # document_resolver
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
OPTIONAL_DATASETS = {
    "训练集 train": DATA_DIR / "train.json",
    "新标注集 new_set": DATA_DIR / "new_set.json",
    "公开集 CLUEWSC2020": DATA_DIR / "clue_wsc.json",
    "CLUEWSC 训练切分": DATA_DIR / "clue_wsc_train.json",
    "CLUEWSC 验证切分": DATA_DIR / "clue_wsc_dev.json",
}
DATASETS.update({
    label: path
    for label, path in OPTIONAL_DATASETS.items()
    if path.exists()
})
BACKENDS = {
    "规则版 baseline": "rule",
    "HanLP 增强接口": "hanlp",
    "LTP 增强接口": "ltp",
}
NEWS_DEMO = (
    "阿里巴巴发布企业智能助手\n"
    "阿里巴巴集团今日发布企业智能助手。该公司表示，该产品将首先服务中小企业。\n"
    "其负责人介绍，平台会整合订单、客服和办公数据。该公司还计划在下季度开放更多行业模板。"
)
RG = RawdataGather(DATA_DIR)


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def render_highlighted_text(text: str, results: list[CoreferenceResult]) -> str:
    spans = []
    for result in results:
        if text[result.antecedent.start : result.antecedent.end] == result.antecedent.text:
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


def news_link_rows(document) -> list[dict]:
    preferred_mentions = {
        item.mention
        for item in document.links
        if item.kind != "指代消解"
    }
    rows = []
    for item in document.links:
        if item.kind == "指代消解" and item.mention in preferred_mentions:
            continue
        if item.normalized.startswith(("据", "关于")):
            continue
        rows.append({
            "表述": item.mention,
            "归一实体": item.normalized,
            "类型": item.kind,
            "依据": item.evidence,
        })
    return rows


def news_display_summary(document) -> tuple[list[str], list[str]]:
    entities = []
    mentions = []
    for item in document.links:
        if item.normalized not in entities:
            entities.append(item.normalized)
        if item.mention not in mentions:
            mentions.append(item.mention)
    return entities, mentions


def news_sentence_link_summary(sentence: str, document) -> list[str]:
    summaries = []
    for item in document.links:
        if item.mention in sentence:
            summary = f"{item.mention}→{item.normalized}"
            if summary not in summaries:
                summaries.append(summary)
    return summaries


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
clue_train_path = DATA_DIR / "clue_wsc_train.json"
clue_train_samples = load_json(clue_train_path) if clue_train_path.exists() else []
training_samples = train_samples + clue_train_samples + demo_samples + dev_samples
extend_lexicon_from_samples(training_samples)
extend_resolution_memory_from_samples(training_samples)
analysis_tab, evaluation_tab, ablation_tab, comparison_tab, annotator_tab = st.tabs([
    "单文本分析",
    "数据集评估",
    "消融实验",
    "模型对比",
    "数据标注",
])

with analysis_tab:
    analysis_mode = st.radio(
        "处理模式",
        ["通用短文本", "新闻/公告长文本"],
        horizontal=True,
    )
    selected_sample = st.selectbox(
        "示例文本",
        ["自定义输入", "新闻公告示例"] + [sample["text"] for sample in demo_samples],
    )
    if selected_sample == "新闻公告示例":
        default_text = NEWS_DEMO
    elif selected_sample == "自定义输入":
        default_text = NEWS_DEMO if analysis_mode == "新闻/公告长文本" else demo_samples[0]["text"]
    else:
        default_text = selected_sample
    text = st.text_area("输入中文文本", default_text, height=210 if analysis_mode == "新闻/公告长文本" else 130)

    if st.button("开始分析", type="primary"):
        if analysis_mode == "新闻/公告长文本":
            original_text = text
            articles = split_news_articles(text)
            text = "\n\n".join(clean_news_text(article) for article in articles)
            document = resolve_news_document(text, backend=backend)
            entities, pronouns, results = document.entities, document.pronouns, document.results
            rewritten = document.rewritten
        else:
            entities, pronouns, results = resolve_text(text, backend=backend)
            rewritten = rewrite_text(text, results)

        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("原文高亮")
            st.markdown(render_highlighted_text(text, results), unsafe_allow_html=True)
            st.subheader("改写结果")
            if analysis_mode == "通用短文本" and any(result.ambiguous for result in results):
                st.warning("检测到指代歧义，歧义代词已跳过自动改写。")
            st.success(rewritten)
            if analysis_mode == "新闻/公告长文本":
                if text != original_text:
                    st.info("已自动移除广告、版权、站点导航等网页噪声行。")
                st.caption(f"检测到新闻篇数：{len(articles)}")
                st.subheader("长文本处理策略")
                for note in document.notes:
                    st.caption(note)

        with right:
            st.subheader("识别结果")
            if analysis_mode == "新闻/公告长文本":
                display_entities, display_mentions = news_display_summary(document)
                st.write(f"归一实体：{', '.join(display_entities) or '无'}")
                st.write(f"新闻表述：{', '.join(display_mentions) or '无'}")
                st.caption("新闻模式隐藏底层碎片候选，只展示清洗后的实体归一结果。")
            else:
                st.write(
                    f"候选实体：{', '.join(entity.text for entity in entities) or '无'}"
                )
                st.write(f"代词：{', '.join(pronoun.text for pronoun in pronouns) or '无'}")

            st.subheader("指代关系")
            rows = news_link_rows(document) if analysis_mode == "新闻/公告长文本" else relation_rows(results)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
                if analysis_mode != "新闻/公告长文本":
                    ambiguities = ambiguous_rows(results)
                    if ambiguities:
                        st.warning("该文本存在多种可能解释。")
                        st.dataframe(ambiguities, use_container_width=True, hide_index=True)
            else:
                st.info("暂未识别到可消解的指代关系。")

        if analysis_mode == "新闻/公告长文本":
            st.subheader("新闻实体归一")
            link_rows = news_link_rows(document)
            if link_rows:
                st.dataframe(link_rows, use_container_width=True, hide_index=True)
            else:
                st.info("暂无可展示的新闻实体归一关系。")

            if len(articles) > 1:
                st.subheader("多篇新闻拆分分析")
                for index, article in enumerate(articles, 1):
                    article_doc = resolve_news_document(article, backend=backend)
                    with st.expander(f"新闻 {index}｜{len(article_doc.sentences)} 句｜{len(article_doc.links)} 条归一关系"):
                        if article_doc.links:
                            st.dataframe(
                                [
                                    {
                                        "表述": item.mention,
                                        "归一实体": item.normalized,
                                        "类型": item.kind,
                                        "依据": item.evidence,
                                    }
                                    for item in article_doc.links
                                ],
                                use_container_width=True,
                                hide_index=True,
                            )
                        st.success(article_doc.rewritten)

            st.subheader("分句处理结果")
            sentence_rows = []
            for item in document.sentences:
                summaries = news_sentence_link_summary(item.text, document)
                sentence_rows.append({
                    "句子": item.text,
                    "实体数": len(item.entities),
                    "新闻表述数": len(summaries),
                    "归一关系数": len(summaries),
                    "关系摘要": "；".join(summaries) or "无",
                    "分句改写": item.rewritten,
                })
            st.dataframe(sentence_rows, use_container_width=True, hide_index=True)
        else:
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

with comparison_tab:
    st.subheader("基本模型与 HanLP/LTP 对比")
    st.caption(
        "固定 resolver / rewriter / evaluator，只比较不同 Mention 抽取后端对最终指代消解结果的影响。"
    )

    status_cols = st.columns(len(BACKENDS))
    for col, (label, backend_name) in zip(status_cols, BACKENDS.items()):
        status = backend_status(backend_name)
        status_message = status.message
        if backend_name in {"hanlp", "ltp"} and not status.available:
            status_message += "；当前对比使用同名启发式 fallback。"
        with col:
            st.markdown(f"**{label}**")
            if status.available:
                st.success("可用")
            else:
                st.warning("未启用 / 回退")
            st.caption(status_message)

    metric_left, metric_right = st.columns([1, 1])
    with metric_left:
        compare_dataset = st.selectbox(
            "选择对比数据集",
            list(DATASETS.keys()),
            index=list(DATASETS.keys()).index("测试集 test") if "测试集 test" in DATASETS else 0,
            key="compare_dataset",
        )
    with metric_right:
        use_memory_in_compare = st.checkbox(
            "使用训练记忆增强",
            value=False,
            help="关闭后更能观察 HanLP/LTP 实体抽取对规则消解的真实影响。",
        )
        run_compare = st.button("运行模型对比", type="primary")

    compare_config = ResolverConfig(use_memory=use_memory_in_compare)
    compare_state_key = (compare_dataset, use_memory_in_compare)
    if (
        run_compare
        or "backend_metric_rows" not in st.session_state
        or st.session_state.get("backend_metric_key") != compare_state_key
    ):
        samples = load_json(DATASETS[compare_dataset])
        baseline_result = evaluate(samples, backend="rule", config=compare_config)
        metric_rows = []
        for label, backend_name in BACKENDS.items():
            status = backend_status(backend_name)
            status_message = status.message
            if backend_name in {"hanlp", "ltp"} and not status.available:
                status_message += "；当前对比使用同名启发式 fallback。"
            result = evaluate(samples, backend=backend_name, config=compare_config)
            metric_rows.append({
                "模型/后端": label,
                "状态": "可用" if status.available else "未启用/回退",
                "Accuracy": round(result.accuracy, 4),
                "Precision": round(result.precision, 4),
                "Recall": round(result.recall, 4),
                "F1": round(result.f1, 4),
                "ΔF1 vs baseline": round(result.f1 - baseline_result.f1, 4),
                "正确/真实": f"{result.correct}/{result.total_gold}",
                "预测关系数": result.total_predicted,
                "错误样本": len(result.errors),
                "说明": status_message,
            })
        st.session_state.backend_metric_rows = metric_rows
        st.session_state.backend_metric_dataset = compare_dataset
        st.session_state.backend_metric_key = compare_state_key

    memory_note = "开启训练记忆" if use_memory_in_compare else "关闭训练记忆"
    st.markdown(f"**数据集指标对比：{st.session_state.backend_metric_dataset}（{memory_note}）**")
    st.dataframe(st.session_state.backend_metric_rows, use_container_width=True, hide_index=True)
    st.caption(
        "说明：HanLP/LTP 主要增强分词和实体识别；本项目的指代关系判断仍由同一套规则打分完成，"
        "因此在 CLUEWSC 这类常识推理数据集上，不保证 F1 一定高于规则版。"
    )
    st.download_button(
        "下载对比结果 JSON",
        data=json.dumps(st.session_state.backend_metric_rows, ensure_ascii=False, indent=2),
        file_name="backend_comparison.json",
        mime="application/json",
    )

    st.divider()
    st.subheader("同一句文本的后端效果对照")
    sample_options = ["自定义输入"] + [sample["text"] for sample in demo_samples[:8]]
    compare_sample = st.selectbox("选择示例文本", sample_options, key="compare_sample")
    compare_default = demo_samples[0]["text"] if compare_sample == "自定义输入" else compare_sample
    compare_text = st.text_area("对比文本", compare_default, height=95, key="compare_text")

    for label, backend_name in BACKENDS.items():
        status = backend_status(backend_name)
        entities, pronouns, results = resolve_text(compare_text, backend=backend_name)
        rewritten = rewrite_text(compare_text, results)
        with st.expander(f"{label}｜{'可用' if status.available else '回退 baseline'}", expanded=(backend_name == "rule")):
            cols = st.columns(4)
            cols[0].metric("候选实体", len(entities))
            cols[1].metric("代词", len(pronouns))
            cols[2].metric("指代关系", len(results))
            cols[3].metric("歧义关系", sum(1 for item in results if item.ambiguous))
            st.caption(status.message)
            st.markdown("**候选实体**")
            st.write(", ".join(f"{item.text}/{item.label}" for item in entities) or "无")
            st.markdown("**指代关系**")
            relation_data = relation_rows(results)
            if relation_data:
                st.dataframe(relation_data, use_container_width=True, hide_index=True)
            else:
                st.info("暂未识别到可消解的指代关系。")
            st.markdown("**改写结果**")
            st.success(rewritten)


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
