import re
from dataclasses import dataclass

from .mention_extractor import Mention, extract_mentions
from .resolver import CandidateScore, CoreferenceResult, ResolverConfig, resolve_text
from .rewriter import rewrite_text


SENTENCE_PATTERN = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")
NEWS_ORG_PRONOUNS = {"该公司", "这家公司", "该企业", "该集团", "该平台", "该院", "该校", "该机构", "其"}
NEWS_SKIP_PRONOUNS = {"我", "我们", "你", "你们", "您", "您们"}
BOILERPLATE_PATTERNS = (
    "炒股就看",
    "金麒麟分析师",
    "24小时滚动播报",
    "更多粉丝福利",
    "扫描二维码",
    "新浪财经意见反馈",
    "新浪简介",
    "广告服务",
    "About Sina",
    "联系我们",
    "招聘信息",
    "通行证注册",
    "产品答疑",
    "网站律师",
    "SINA English",
    "Copyright",
    "All Rights Reserved",
    "新浪公司版权所有",
)


@dataclass(frozen=True)
class SentenceAnalysis:
    text: str
    start: int
    end: int
    entities: list[Mention]
    pronouns: list[Mention]
    results: list[CoreferenceResult]
    rewritten: str


@dataclass(frozen=True)
class DocumentAnalysis:
    title: str
    rewritten: str
    entities: list[Mention]
    pronouns: list[Mention]
    results: list[CoreferenceResult]
    sentences: list[SentenceAnalysis]
    links: list["NewsEntityLink"]
    notes: list[str]


@dataclass(frozen=True)
class NewsEntityLink:
    mention: str
    normalized: str
    kind: str
    evidence: str


def resolve_news_document(
    text: str,
    backend: str = "rule",
    config: ResolverConfig | None = None,
    window_size: int = 2,
    auto_rewrite_threshold: float = 0.85,
) -> DocumentAnalysis:
    """Resolve long news/announcement text with title memory and local windows."""
    text = clean_news_text(text)
    config = config or ResolverConfig(ambiguity_margin=0.12)
    title, body, body_offset = _split_title_body(text)
    title_entities, _ = extract_mentions(title, backend=backend)
    title_entities = _dedupe_mentions(title_entities + _extract_title_entities(title))
    sentence_spans = _split_sentences(body, body_offset)
    memory: list[Mention] = [_shift_mention(entity, 0) for entity in title_entities]
    sentence_items: list[SentenceAnalysis] = []
    all_entities: list[Mention] = list(memory)
    all_pronouns: list[Mention] = []
    all_results: list[CoreferenceResult] = []
    rewritten_parts: list[tuple[int, int, str]] = []
    notes = [
        f"标题实体数：{len(title_entities)}",
        f"句子窗口：当前句 + 前 {window_size} 句 + 标题实体",
        f"自动改写阈值：score >= {auto_rewrite_threshold}",
    ]

    recent_entities: list[Mention] = []
    for sent_text, start, end in sentence_spans:
        window_entities = _window_entities(memory, recent_entities, start, window_size)
        local_extra = [_localize_memory_entity(entity) for entity in window_entities]
        entities, pronouns, results = resolve_text(
            sent_text,
            backend=backend,
            config=config,
            extra_entities=local_extra,
        )
        adjusted_entities = [_shift_mention(entity, start) for entity in entities if entity.start >= 0]
        adjusted_pronouns = _filter_news_pronouns(
            text,
            [_shift_mention(pronoun, start) for pronoun in pronouns],
        )
        adjusted_results = [_shift_result(result, start) for result in results]
        adjusted_results = _filter_news_results(text, adjusted_results)
        adjusted_results = _apply_news_overrides(adjusted_results, memory)
        safe_results = [
            result
            for result in adjusted_results
            if not result.ambiguous and result.score >= auto_rewrite_threshold
        ]
        rewritten = rewrite_text(sent_text, [_shift_result(result, -start) for result in safe_results])

        sentence_items.append(
            SentenceAnalysis(
                text=sent_text,
                start=start,
                end=end,
                entities=adjusted_entities,
                pronouns=adjusted_pronouns,
                results=adjusted_results,
                rewritten=rewritten,
            )
        )
        all_entities.extend(adjusted_entities)
        all_pronouns.extend(adjusted_pronouns)
        all_results.extend(adjusted_results)
        rewritten_parts.append((start, end, rewritten))
        memory = _update_memory(memory, adjusted_entities)
        recent_entities.extend(adjusted_entities)

    rewritten_doc = _assemble_rewrite(text, rewritten_parts)
    links = infer_news_entity_links(text, _dedupe_mentions(all_entities), all_results)
    return DocumentAnalysis(
        title=title,
        rewritten=rewritten_doc,
        entities=_dedupe_mentions(all_entities),
        pronouns=all_pronouns,
        results=all_results,
        sentences=sentence_items,
        links=links,
        notes=notes,
    )


def split_news_articles(text: str) -> list[str]:
    """Split pasted web text into news articles using boilerplate boundaries."""
    articles: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern in line for pattern in BOILERPLATE_PATTERNS):
            if current:
                articles.append("\n".join(current))
                current = []
            continue
        if (
            current
            and re.match(r"^\d{1,2}月\d{1,2}日.*消息", line)
            and len("\n".join(current)) > 120
        ):
            articles.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        articles.append("\n".join(current))
    return articles or [clean_news_text(text)]


def clean_news_text(text: str) -> str:
    """Remove common web-page boilerplate from copied news text."""
    kept_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern in line for pattern in BOILERPLATE_PATTERNS):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def infer_news_entity_links(
    text: str,
    entities: list[Mention],
    results: list[CoreferenceResult],
) -> list[NewsEntityLink]:
    """Infer display-oriented entity normalization links for news demos."""
    links: list[NewsEntityLink] = []
    main_company = _infer_main_company(text, entities)
    store = _infer_store(text)
    consumer = _infer_consumer(text)

    for result in results:
        links.append(
            NewsEntityLink(
                mention=result.pronoun.text,
                normalized=result.antecedent.text,
                kind="指代消解",
                evidence="规则打分/篇章记忆",
            )
        )

    if main_company:
        for mention in ("该公司", "这家企业", "该企业", "公司", "其"):
            if mention in text:
                links.append(NewsEntityLink(mention, main_company, "企业归一", "标题/首段主体"))
    if store:
        if "门店" in text:
            links.append(NewsEntityLink("门店", store, "门店归一", "新闻地点短语"))
        if "公司" in text and "门店工作人员" in text:
            brand = store.replace("上海合生汇店", "")
            links.append(NewsEntityLink("公司", brand, "企业归一", "门店工作人员表述"))
    if consumer:
        for mention in ("消费者", "您"):
            if mention in text:
                links.append(NewsEntityLink(mention, consumer, "角色归一", "投诉事件角色"))

    return _dedupe_links(links)


def _infer_main_company(text: str, entities: list[Mention]) -> str | None:
    """Infer main company from finance/tech news text."""
    for pattern in (
        r"初创企业([A-Za-z][A-Za-z0-9\-.]*)",
        r"([A-Za-z][A-Za-z0-9\-.]*)正与",
        r"([A-Za-z][A-Za-z0-9\-.]*)由",
        r"([A-Za-z][A-Za-z0-9\-.]*)完成",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    orgs = [entity.text for entity in entities if entity.label == "ORG" and len(entity.text) >= 2]
    return orgs[0] if orgs else None


def _infer_store(text: str) -> str | None:
    """Infer restaurant/store entity from consumer complaint news."""
    match = re.search(r"前往(.{2,30}?店)用餐", text)
    if match:
        return match.group(1)
    match = re.search(r"(.{2,20}?店)用餐", text)
    return match.group(1) if match else None


def _infer_consumer(text: str) -> str | None:
    """Infer complainant role for consumer-rights news."""
    if "消费者" in text and ("投诉" in text or "赔偿" in text or "吃出" in text):
        return "投诉消费者"
    return None


def _dedupe_links(links: list[NewsEntityLink]) -> list[NewsEntityLink]:
    """Deduplicate display links."""
    seen: set[tuple[str, str, str]] = set()
    result: list[NewsEntityLink] = []
    for link in links:
        key = (link.mention, link.normalized, link.kind)
        if key in seen:
            continue
        seen.add(key)
        result.append(link)
    return result


def _split_title_body(text: str) -> tuple[str, str, int]:
    """Use the first non-empty line as news title if available."""
    match = re.search(r"\S.*", text)
    if match is None:
        return "", text, 0
    first_start = match.start()
    line_end = text.find("\n", first_start)
    if line_end < 0:
        return "", text, 0
    title = text[first_start:line_end].strip()
    if len(title) > 45 or "消息" in title or "据媒体报道" in title:
        return "", text, 0
    body_start = line_end + 1
    return title, text[body_start:], body_start


def _extract_title_entities(title: str) -> list[Mention]:
    """Extract likely headline subject entities from news titles."""
    entities: list[Mention] = []
    for marker in ("发布", "宣布", "推出", "上线", "回应", "表示"):
        index = title.find(marker)
        if index <= 1:
            continue
        value = title[:index].strip(" ，,：:")
        if 2 <= len(value) <= 12:
            entities.append(Mention(value, 0, len(value), "ORG", "neutral"))
            break
    return entities


def _split_sentences(body: str, offset: int) -> list[tuple[str, int, int]]:
    """Split body into sentence-like spans while preserving offsets."""
    spans: list[tuple[str, int, int]] = []
    for match in SENTENCE_PATTERN.finditer(body):
        value = match.group()
        if not value.strip():
            continue
        start = offset + match.start()
        end = offset + match.end()
        spans.append((value, start, end))
    return spans or [(body, offset, offset + len(body))]


def _window_entities(
    title_memory: list[Mention],
    recent_entities: list[Mention],
    sentence_start: int,
    window_size: int,
) -> list[Mention]:
    """Keep title entities and entities from recent sentences."""
    recent = [entity for entity in recent_entities if sentence_start - entity.end <= window_size * 80]
    return _dedupe_mentions(title_memory + recent)


def _localize_memory_entity(entity: Mention) -> Mention:
    """Convert memory entity to a virtual candidate before the sentence."""
    return Mention(entity.text, -len(entity.text), 0, entity.label, entity.gender, entity.number)


def _shift_mention(mention: Mention, offset: int) -> Mention:
    """Shift a mention span by a character offset."""
    return Mention(
        mention.text,
        mention.start + offset,
        mention.end + offset,
        mention.label,
        mention.gender,
        mention.number,
    )


def _shift_result(result: CoreferenceResult, offset: int) -> CoreferenceResult:
    """Shift all spans in a coreference result."""
    from .resolver import CandidateScore

    pronoun = _shift_mention(result.pronoun, offset)
    antecedent = _shift_mention(result.antecedent, offset)
    candidates = [
        CandidateScore(
            pronoun=_shift_mention(candidate.pronoun, offset),
            candidate=_shift_mention(candidate.candidate, offset),
            score=candidate.score,
            reasons=candidate.reasons,
        )
        for candidate in result.candidates
    ]
    return CoreferenceResult(pronoun, antecedent, result.score, candidates, result.ambiguous)


def _update_memory(memory: list[Mention], entities: list[Mention]) -> list[Mention]:
    """Update document memory with real entities from the latest sentence."""
    valid_entities = [
        entity
        for entity in entities
        if entity.start >= 0 and entity.text not in NEWS_ORG_PRONOUNS and _valid_news_entity(entity)
    ]
    return _dedupe_mentions(memory + valid_entities)[-80:]


def _valid_news_entity(entity: Mention) -> bool:
    """Filter malformed short fragments in copied news text."""
    bad_suffixes = ("提", "已", "经", "时", "全程", "对此", "方式", "存在", "严重")
    if entity.text in NEWS_SKIP_PRONOUNS or entity.text in NEWS_ORG_PRONOUNS:
        return False
    if len(entity.text) <= 1:
        return False
    if entity.label == "PERSON" and any(entity.text.endswith(suffix) for suffix in bad_suffixes):
        return False
    return True


def _apply_news_overrides(
    results: list[CoreferenceResult],
    memory: list[Mention],
) -> list[CoreferenceResult]:
    """Prefer the main title organization for news organization pronouns."""
    main_org = next((entity for entity in memory if entity.label == "ORG"), None)
    if main_org is None:
        return results
    rewritten: list[CoreferenceResult] = []
    for result in results:
        if result.pronoun.label == "ORG_PRONOUN" or result.pronoun.text in NEWS_ORG_PRONOUNS:
            score = CandidateScore(
                pronoun=result.pronoun,
                candidate=main_org,
                score=1.2,
                reasons=["news title entity boost", "organization pronoun"],
            )
            rewritten.append(
                CoreferenceResult(
                    pronoun=result.pronoun,
                    antecedent=main_org,
                    score=1.2,
                    candidates=[score] + result.candidates,
                    ambiguous=False,
                )
            )
        else:
            rewritten.append(result)
    return rewritten


def _filter_news_results(text: str, results: list[CoreferenceResult]) -> list[CoreferenceResult]:
    """Skip quoted first/second-person mentions in news mode."""
    filtered: list[CoreferenceResult] = []
    for result in results:
        if result.pronoun.text in NEWS_SKIP_PRONOUNS:
            continue
        if _inside_quote(text, result.pronoun.start):
            if result.pronoun.text in NEWS_SKIP_PRONOUNS or result.pronoun.label == "PERSON_PRONOUN":
                continue
        filtered.append(result)
    return filtered


def _filter_news_pronouns(text: str, pronouns: list[Mention]) -> list[Mention]:
    """Hide first/second-person pronouns in quoted news text."""
    return [
        pronoun
        for pronoun in pronouns
        if pronoun.text not in NEWS_SKIP_PRONOUNS
        and not (_inside_quote(text, pronoun.start) and pronoun.label == "PERSON_PRONOUN")
    ]


def _inside_quote(text: str, index: int) -> bool:
    """Return whether an index is inside Chinese or ASCII quotes."""
    left_cn = text.rfind("“", 0, index)
    right_cn = text.rfind("”", 0, index)
    if left_cn > right_cn:
        return True
    return text[:index].count('"') % 2 == 1


def _dedupe_mentions(mentions: list[Mention]) -> list[Mention]:
    """Deduplicate mentions by text, label, and span."""
    seen: set[tuple[str, str, int, int]] = set()
    result: list[Mention] = []
    for mention in sorted(mentions, key=lambda item: (item.start, item.end, item.text)):
        key = (mention.text, mention.label, mention.start, mention.end)
        if key in seen:
            continue
        seen.add(key)
        result.append(mention)
    return result


def _assemble_rewrite(text: str, rewritten_parts: list[tuple[int, int, str]]) -> str:
    """Assemble rewritten sentence spans back into the original document."""
    output = []
    cursor = 0
    for start, end, rewritten in sorted(rewritten_parts, key=lambda item: item[0]):
        output.append(text[cursor:start])
        output.append(rewritten)
        cursor = end
    output.append(text[cursor:])
    return "".join(output)
