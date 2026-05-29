import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Mention:
    text: str
    start: int
    end: int
    label: str
    gender: str = "unknown"
    number: str = "singular"


PRONOUNS: dict[str, dict[str, str]] = {
    "这家公司": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
    "该公司": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
    "这所学校": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
    "该校": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
    "这个产品": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该产品": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "这个项目": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该项目": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该系统": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该报告": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该平台": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该通知": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该团队": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
    "这些电脑": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "plural"},
    "这些作业": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "plural"},
    "这本书": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "他们": {"label": "PERSON_PRONOUN", "gender": "unknown", "number": "plural"},
    "她们": {"label": "PERSON_PRONOUN", "gender": "female", "number": "plural"},
    "它们": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "plural"},
    "他": {"label": "PERSON_PRONOUN", "gender": "male", "number": "singular"},
    "她": {"label": "PERSON_PRONOUN", "gender": "female", "number": "singular"},
    "它": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
}

FEMALE_HINTS = {
    "小红",
    "小丽",
    "小芳",
    "小美",
    "小雅",
    "李娜",
    "王芳",
    "杨静",
    "周敏",
    "赵婷",
}
MALE_HINTS = {
    "小明",
    "小刚",
    "小强",
    "小华",
    "小李",
    "张伟",
    "王强",
    "陈明",
    "刘洋",
    "吴磊",
}
KNOWN_NAMES = FEMALE_HINTS | MALE_HINTS

OBJECT_WORDS = {
    "书",
    "通知",
    "作业",
    "礼物",
    "手机",
    "产品",
    "系统",
    "项目",
    "平台",
    "文章",
    "报告",
    "电脑",
    "钥匙",
    "论文",
}

ORG_WORDS = {"学校", "医院", "银行", "政府", "团队", "研究团队"}
ORG_SUFFIXES = ("公司", "大学", "学校", "医院", "银行", "政府", "团队")
ORG_TRIM_MARKERS = ("把", "给", "买", "了", "发布", "加入", "完成", "表示", "认为")


def _trim_org_span(text: str, start: int, end: int) -> tuple[str, int, int]:
    """Trim accidental verb prefixes from simple organization matches."""
    value = text[start:end]
    trim_at = -1
    marker_len = 0
    for marker in ORG_TRIM_MARKERS:
        index = value.rfind(marker)
        if index > trim_at:
            trim_at = index
            marker_len = len(marker)
    if trim_at >= 0:
        start = start + trim_at + marker_len
        value = text[start:end]
    return value, start, end


def extract_pronouns(text: str) -> list[Mention]:
    """Extract pronouns with longest-match priority."""
    mentions: list[Mention] = []
    occupied: list[tuple[int, int]] = []
    for pronoun in sorted(PRONOUNS, key=len, reverse=True):
        for match in re.finditer(re.escape(pronoun), text):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            meta = PRONOUNS[pronoun]
            mentions.append(
                Mention(
                    text=pronoun,
                    start=start,
                    end=end,
                    label=meta["label"],
                    gender=meta["gender"],
                    number=meta["number"],
                )
            )
            occupied.append((start, end))
    return sorted(mentions, key=lambda item: item.start)


def extract_entities(text: str) -> list[Mention]:
    """Extract lightweight entity candidates for the first prototype."""
    mentions: list[Mention] = []
    occupied: list[tuple[int, int]] = []

    for match in re.finditer(r"[\u4e00-\u9fff]{1,6}(?:" + "|".join(ORG_SUFFIXES) + r")", text):
        value, start, end = _trim_org_span(text, match.start(), match.end())
        if len(value) <= 1:
            continue
        mentions.append(Mention(value, start, end, "ORG", "neutral"))
        occupied.append((start, end))

    for word in sorted(ORG_WORDS, key=len, reverse=True):
        for match in re.finditer(re.escape(word), text):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            mentions.append(Mention(word, start, end, "ORG", "neutral"))
            occupied.append((start, end))

    name_pattern = "|".join(re.escape(name) for name in sorted(KNOWN_NAMES, key=len, reverse=True))
    for match in re.finditer(r"小[\u4e00-\u9fff]|" + name_pattern, text):
        start, end = match.span()
        if any(not (end <= a or start >= b) for a, b in occupied):
            continue
        name = match.group()
        gender = "female" if name in FEMALE_HINTS else "male" if name in MALE_HINTS else "unknown"
        mentions.append(Mention(name, start, end, "PERSON", gender))
        occupied.append((start, end))

    for word in sorted(OBJECT_WORDS, key=len, reverse=True):
        for match in re.finditer(re.escape(word), text):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            mentions.append(Mention(word, start, end, "OBJECT", "neutral"))
            occupied.append((start, end))

    return sorted(mentions, key=lambda item: item.start)


def extract_mentions(text: str) -> tuple[list[Mention], list[Mention]]:
    """Return entity candidates and pronoun mentions."""
    return extract_entities(text), extract_pronouns(text)
