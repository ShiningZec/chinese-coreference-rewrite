from dataclasses import dataclass
import os
import re
from functools import lru_cache
from typing import Any

from .mention_extractor_types import Mention


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv() -> None:
    """Load simple KEY=VALUE pairs from project .env if present."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class BackendInfo:
    name: str
    available: bool
    message: str


@dataclass(frozen=True)
class BackendResult:
    info: BackendInfo
    entities: list[Mention]


def backend_status(backend: str) -> BackendInfo:
    """Return whether an optional NLP backend can be imported."""
    if backend == "rule":
        return BackendInfo("rule", True, "使用内置规则抽取。")
    if backend == "hanlp":
        try:
            import hanlp  # noqa: F401
        except Exception as exc:
            return BackendInfo("hanlp", False, f"HanLP 未启用：{exc}")
        if not os.getenv("HANLP_MODEL"):
            return BackendInfo(
                "hanlp",
                False,
                "HanLP 已安装，但未设置 HANLP_MODEL，已回退规则抽取。",
            )
        return BackendInfo("hanlp", True, "HanLP 模型已配置，可参与实体抽取对比。")
    if backend == "ltp":
        modern_error = None
        legacy_error = None
        try:
            import ltp  # noqa: F401

            if os.getenv("LTP_MODEL"):
                return BackendInfo("ltp", True, "LTP 模型已配置，可参与实体抽取对比。")
            modern_error = "未设置 LTP_MODEL"
        except Exception as exc:
            modern_error = str(exc)
        try:
            import pyltp  # noqa: F401

            if all(os.getenv(name) for name in ("PYLTP_CWS_MODEL", "PYLTP_POS_MODEL", "PYLTP_NER_MODEL")):
                return BackendInfo("ltp", True, "pyltp legacy 模型已配置，可参与实体抽取对比。")
            legacy_error = "未设置 PYLTP_CWS_MODEL/PYLTP_POS_MODEL/PYLTP_NER_MODEL"
        except Exception as exc:
            legacy_error = str(exc)
        return BackendInfo("ltp", False, f"LTP 未启用：modern={modern_error}；legacy={legacy_error}")
    return BackendInfo(backend, False, "未知 NLP 后端，已回退到规则抽取。")


def extract_backend_entities(text: str, backend: str) -> BackendResult:
    """Hook for optional HanLP/LTP extraction.

    The project keeps rule extraction as the stable baseline. This hook makes
    the architecture ready for HanLP/LTP without forcing heavy model downloads.
    """
    info = backend_status(backend)
    if backend == "hanlp":
        entities = _extract_hanlp_entities(text) if info.available else []
        if not entities:
            entities = _extract_hanlp_style_entities(text)
        return BackendResult(info=info, entities=entities)
    if backend == "ltp":
        entities = _extract_ltp_entities(text) if info.available else []
        if not entities:
            entities = _extract_ltp_style_entities(text)
        return BackendResult(info=info, entities=entities)
    if not info.available:
        return BackendResult(info=info, entities=[])
    return BackendResult(info=info, entities=[])


def _label_from_ner_tag(tag: str) -> str | None:
    """Map common NER labels to project entity labels."""
    upper = tag.upper()
    if any(value in upper for value in ("PER", "PERSON", "NH")):
        return "PERSON"
    if any(value in upper for value in ("ORG", "ORGANIZATION", "NI")):
        return "ORG"
    if any(value in upper for value in ("LOC", "LOCATION", "NS", "GPE")):
        return "LOCATION"
    return None


def _token_offsets(text: str, tokens: list[str]) -> list[tuple[int, int]]:
    """Align token sequence back to character offsets."""
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for token in tokens:
        start = text.find(token, cursor)
        if start < 0:
            start = cursor
        end = start + len(token)
        offsets.append((start, end))
        cursor = end
    return offsets


def _mention_from_span(text: str, start: int, end: int, tag: str) -> Mention | None:
    """Create a Mention if a backend NER span can be mapped."""
    label = _label_from_ner_tag(tag)
    value = text[start:end].strip()
    if label is None or not value:
        return None
    gender = "neutral" if label in {"ORG", "LOCATION"} else "unknown"
    return Mention(value, start, end, label, gender)


@lru_cache(maxsize=1)
def _hanlp_model() -> Any:
    """Load configured HanLP model lazily."""
    import hanlp

    model_name = os.environ["HANLP_MODEL"]
    if model_name.lower() in {"default", "mtl"}:
        model_name = hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH
    return hanlp.load(model_name)


def _extract_hanlp_entities(text: str) -> list[Mention]:
    """Extract entities from HanLP output with tolerant format handling."""
    try:
        output = _hanlp_model()(text)
    except Exception:
        return []
    entities: list[Mention] = []
    for item in _walk_ner_items(output):
        mention = _parse_hanlp_item(text, item)
        if mention is not None:
            entities.append(mention)
    return _dedupe_entities(entities)


def _walk_ner_items(value: Any) -> list[Any]:
    """Collect NER-like items from nested HanLP outputs."""
    if isinstance(value, dict):
        items: list[Any] = []
        for key, child in value.items():
            if "ner" in str(key).lower() and isinstance(child, list):
                items.extend(child)
            else:
                items.extend(_walk_ner_items(child))
        return items
    if isinstance(value, list):
        if value and all(isinstance(item, (list, tuple)) for item in value):
            return value
        items = []
        for child in value:
            items.extend(_walk_ner_items(child))
        return items
    return []


def _parse_hanlp_item(text: str, item: Any) -> Mention | None:
    """Parse common HanLP NER tuple variants."""
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return None
    values = list(item)
    tag = next((str(value) for value in values if isinstance(value, str) and _label_from_ner_tag(str(value))), "")
    if not tag:
        return None

    ints = [value for value in values if isinstance(value, int)]
    span_text = next((str(value) for value in values if isinstance(value, str) and value != tag), "")
    if len(ints) >= 2 and 0 <= ints[-2] < ints[-1] <= len(text):
        return _mention_from_span(text, ints[-2], ints[-1], tag)
    if span_text:
        start = text.find(span_text)
        if start >= 0:
            return _mention_from_span(text, start, start + len(span_text), tag)
    return None


def _extract_ltp_entities(text: str) -> list[Mention]:
    """Extract entities from modern LTP or pyltp legacy models."""
    if os.getenv("LTP_MODEL"):
        return _extract_modern_ltp_entities(text)
    return _extract_pyltp_entities(text)


@lru_cache(maxsize=1)
def _modern_ltp_model() -> Any:
    """Load configured modern LTP model lazily."""
    from ltp import LTP

    return LTP(os.environ["LTP_MODEL"])


def _extract_modern_ltp_entities(text: str) -> list[Mention]:
    """Extract entities from modern ltp package."""
    try:
        ltp_model = _modern_ltp_model()
        result = ltp_model.pipeline([text], tasks=["cws", "ner"])
    except Exception:
        return []
    tokens = list(result.cws[0]) if getattr(result, "cws", None) else []
    offsets = _token_offsets(text, tokens)
    entities: list[Mention] = []
    for item in getattr(result, "ner", [[]])[0]:
        if len(item) < 3:
            continue
        tag, start_idx, end_idx = item[0], int(item[1]), int(item[2])
        if start_idx < 0 or end_idx >= len(offsets):
            continue
        start = offsets[start_idx][0]
        end = offsets[end_idx][1]
        mention = _mention_from_span(text, start, end, str(tag))
        if mention is not None:
            entities.append(mention)
    return _dedupe_entities(entities)


@lru_cache(maxsize=1)
def _pyltp_models() -> tuple[Any, Any, Any]:
    """Load configured pyltp legacy models lazily."""
    from pyltp import NamedEntityRecognizer, Postagger, Segmentor

    segmentor = Segmentor()
    segmentor.load(os.environ["PYLTP_CWS_MODEL"])
    postagger = Postagger()
    postagger.load(os.environ["PYLTP_POS_MODEL"])
    recognizer = NamedEntityRecognizer()
    recognizer.load(os.environ["PYLTP_NER_MODEL"])
    return segmentor, postagger, recognizer


def _extract_pyltp_entities(text: str) -> list[Mention]:
    """Extract entities from pyltp BIOES NER tags."""
    try:
        segmentor, postagger, recognizer = _pyltp_models()
        tokens = list(segmentor.segment(text))
        postags = list(postagger.postag(tokens))
        netags = list(recognizer.recognize(tokens, postags))
    except Exception:
        return []
    offsets = _token_offsets(text, tokens)
    entities: list[Mention] = []
    start_idx: int | None = None
    tag = ""
    for index, netag in enumerate(netags):
        if netag == "O":
            start_idx = None
            continue
        prefix, _, raw_tag = netag.partition("-")
        if prefix == "S":
            mention = _mention_from_span(text, offsets[index][0], offsets[index][1], raw_tag)
            if mention is not None:
                entities.append(mention)
            start_idx = None
        elif prefix == "B":
            start_idx = index
            tag = raw_tag
        elif prefix == "E" and start_idx is not None:
            mention = _mention_from_span(text, offsets[start_idx][0], offsets[index][1], tag or raw_tag)
            if mention is not None:
                entities.append(mention)
            start_idx = None
    return _dedupe_entities(entities)


def _extract_hanlp_style_entities(text: str) -> list[Mention]:
    """Fallback NER-style extractor used when HanLP is not installed."""
    entities: list[Mention] = []
    org_suffixes = (
        "公司",
        "集团",
        "大学",
        "学院",
        "医院",
        "银行",
        "机构",
        "企业",
        "门店",
        "商场",
        "资本",
        "科技",
        "部门",
        "委员会",
    )
    org_pattern = r"[A-Za-z0-9\u4e00-\u9fa5·]{2,28}(?:" + "|".join(org_suffixes) + r")"
    for match in re.finditer(org_pattern, text):
        value = match.group(0)
        if len(value) > 30:
            value = value[-30:]
        start = match.end() - len(value)
        entities.append(Mention(value, start, match.end(), "ORG", "neutral"))

    brand_pattern = r"(?:XLight|阿斯麦|英伟达|台积电|英特尔|美光科技|新浪财经|TechCrunch)"
    for match in re.finditer(brand_pattern, text):
        entities.append(Mention(match.group(0), match.start(), match.end(), "ORG", "neutral"))

    person_pattern = r"[\u4e00-\u9fa5]{2,4}(?=(?:表示|认为|指出|介绍|透露|称|说|回应|会见|整理|准备))"
    for match in re.finditer(person_pattern, text):
        entities.append(Mention(match.group(0), match.start(), match.end(), "PERSON", "unknown"))

    return _dedupe_entities(entities)


def _extract_ltp_style_entities(text: str) -> list[Mention]:
    """Fallback segmentation-style extractor used when LTP is not installed."""
    entities: list[Mention] = []
    noun_suffixes = (
        "产品",
        "项目",
        "方案",
        "技术",
        "设备",
        "材料",
        "资金",
        "证据",
        "烟头",
        "问题",
        "菜品",
        "食材",
        "部门",
        "门店",
        "消费者",
        "工作人员",
    )
    noun_pattern = r"[\u4e00-\u9fa5]{1,12}(?:" + "|".join(noun_suffixes) + r")"
    for match in re.finditer(noun_pattern, text):
        value = match.group(0)
        if len(value) > 14:
            value = value[-14:]
        start = match.end() - len(value)
        label = "PERSON" if value.endswith(("消费者", "工作人员")) else "OBJECT"
        entities.append(Mention(value, start, match.end(), label, "unknown"))

    short_name_pattern = r"[\u4e00-\u9fa5]{2,3}(?=(?:把|向|给|对|替|帮|准备|整理|认为|感到))"
    for match in re.finditer(short_name_pattern, text):
        entities.append(Mention(match.group(0), match.start(), match.end(), "PERSON", "unknown"))

    return _dedupe_entities(entities)


def _dedupe_entities(entities: list[Mention]) -> list[Mention]:
    """Deduplicate backend entities by span and label."""
    seen: set[tuple[int, int, str]] = set()
    result: list[Mention] = []
    for entity in sorted(entities, key=lambda item: (item.start, item.end, item.label)):
        key = (entity.start, entity.end, entity.label)
        if key in seen:
            continue
        seen.add(key)
        result.append(entity)
    return result
