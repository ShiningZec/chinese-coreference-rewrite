import re

from .mention_extractor_types import Mention


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
    "该平台": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
    "该通知": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该政策": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该方案": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该课程": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该活动": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "这项活动": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该会议": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该订单": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该城市": {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": "singular"},
    "该企业": {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"},
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

COMMON_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张"
    "孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎"
    "鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤"
    "罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴谈宋庞"
    "熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜"
    "郭梅盛林刁钟徐邱骆高夏蔡田胡凌霍虞万支柯昝管卢"
    "莫经房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉"
    "龚程嵇邢裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴"
    "糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰"
    "秋仲伊宫宁仇栾暴甘斜厉戎祖武符刘景詹束龙叶幸"
    "司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙"
    "池乔阴郁胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰"
    "郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏"
    "柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居"
    "衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆"
    "师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠"
    "须丰巢关蒯相查后荆红游竺权逯盖益桓公"
)
NAME_VERB_SUFFIXES = (
    "会见",
    "看见",
    "遇见",
    "拜访",
    "采访",
    "邀请",
    "整理",
    "准备",
    "找到",
    "认为",
    "表示",
    "说",
    "告诉",
    "给",
    "把",
    "对",
    "向",
    "替",
    "帮",
    "为",
)
NAME_VERB_PREFIX_CHARS = set("整准确阅读写拿放给把对向替帮为说讲问看见遇找邀采拜访认表")
LEXICON_ENTITIES: dict[str, dict[str, str]] = {}
LEXICON_PRONOUNS: dict[str, dict[str, str]] = {}

ORG_PRONOUN_TERMS = (
    "公司",
    "学校",
    "该校",
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
    "频道",
    "基地",
    "巨头",
    "企业",
    "团队",
    "机构",
    "银行",
    "政府",
)

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
    "政策",
    "方案",
    "课程",
    "活动",
    "会议",
    "订单",
    "城市",
    "计划",
}

ORG_WORDS = {"学校", "医院", "银行", "政府", "团队", "研究团队", "企业"}
ORG_SUFFIXES = ("公司", "大学", "学校", "医院", "银行", "政府", "团队", "企业")
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
    pronoun_dict = {**PRONOUNS, **LEXICON_PRONOUNS}
    for pronoun in sorted(pronoun_dict, key=len, reverse=True):
        for match in re.finditer(re.escape(pronoun), text):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            meta = pronoun_dict[pronoun]
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

    for entity, meta in sorted(LEXICON_ENTITIES.items(), key=lambda item: len(item[0]), reverse=True):
        for match in re.finditer(re.escape(entity), text):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            mentions.append(Mention(entity, start, end, meta["label"], meta["gender"]))
            occupied.append((start, end))

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

    surname_pattern = "[" + re.escape(COMMON_SURNAMES) + r"][\u4e00-\u9fff]{1,3}"
    for match in re.finditer(surname_pattern, text):
        start, end = match.span()
        name = match.group()
        for suffix in NAME_VERB_SUFFIXES:
            if name.endswith(suffix) and len(name) - len(suffix) >= 2:
                name = name[: -len(suffix)]
                end = start + len(name)
                break
        if len(name) >= 3 and name[-1] in NAME_VERB_PREFIX_CHARS:
            name = name[:-1]
            end = start + len(name)
        if len(name) < 2 or name in KNOWN_NAMES:
            continue
        if any(not (end <= a or start >= b) for a, b in occupied):
            continue
        mentions.append(Mention(name, start, end, "PERSON", "unknown"))
        occupied.append((start, end))

    for word in sorted(OBJECT_WORDS, key=len, reverse=True):
        for match in re.finditer(re.escape(word), text):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            mentions.append(Mention(word, start, end, "OBJECT", "neutral"))
            occupied.append((start, end))

    return sorted(mentions, key=lambda item: item.start)


def extract_mentions(text: str, backend: str = "rule") -> tuple[list[Mention], list[Mention]]:
    """Return entity candidates and pronoun mentions."""
    entities = extract_entities(text)
    if backend != "rule":
        from .nlp_backend import extract_backend_entities

        backend_result = extract_backend_entities(text, backend)
        entities = _merge_entities(entities, backend_result.entities)
    return entities, extract_pronouns(text)


def _pronoun_meta(pronoun: str) -> dict[str, str]:
    """Infer pronoun metadata from an annotated training item."""
    if any(term in pronoun for term in ORG_PRONOUN_TERMS):
        return {"label": "ORG_PRONOUN", "gender": "neutral", "number": "singular"}
    if pronoun in PRONOUNS:
        return PRONOUNS[pronoun]
    if pronoun in {"他", "她", "他们", "她们"}:
        gender = "female" if "她" in pronoun else "male" if pronoun == "他" else "unknown"
        number = "plural" if pronoun.endswith("们") else "singular"
        return {"label": "PERSON_PRONOUN", "gender": gender, "number": number}
    if pronoun in {"它", "它们"} or pronoun.startswith(("该", "这")):
        number = "plural" if pronoun.endswith("们") or pronoun.startswith("这些") else "singular"
        return {"label": "OBJECT_PRONOUN", "gender": "neutral", "number": number}
    return {"label": "PERSON_PRONOUN", "gender": "unknown", "number": "singular"}


def _entity_meta_from_pronoun(pronoun_meta: dict[str, str]) -> dict[str, str]:
    """Infer antecedent metadata from the paired pronoun type."""
    label_map = {
        "PERSON_PRONOUN": "PERSON",
        "OBJECT_PRONOUN": "OBJECT",
        "ORG_PRONOUN": "ORG",
    }
    return {
        "label": label_map.get(pronoun_meta["label"], "OBJECT"),
        "gender": pronoun_meta.get("gender", "unknown"),
    }


def extend_lexicon_from_samples(samples: list[dict]) -> None:
    """Add annotated pronouns and antecedents into the runtime lexicon."""
    for sample in samples:
        for item in sample.get("coreference", []):
            pronoun = item.get("pronoun", "").strip()
            antecedent = item.get("antecedent", "").strip()
            if not pronoun or not antecedent:
                continue
            pronoun_meta = _pronoun_meta(pronoun)
            LEXICON_PRONOUNS.setdefault(pronoun, pronoun_meta)
            entity_meta = _entity_meta_from_pronoun(pronoun_meta)
            current_meta = LEXICON_ENTITIES.get(antecedent)
            if current_meta is None:
                LEXICON_ENTITIES[antecedent] = entity_meta
            elif current_meta["label"] == "OBJECT" and entity_meta["label"] in {"ORG", "PERSON"}:
                # Prefer a more specific entity type learned from annotated aliases.
                LEXICON_ENTITIES[antecedent] = entity_meta
            elif current_meta.get("gender") == "unknown" and entity_meta.get("gender") != "unknown":
                LEXICON_ENTITIES[antecedent] = {**current_meta, "gender": entity_meta["gender"]}


def _merge_entities(primary: list[Mention], extra: list[Mention]) -> list[Mention]:
    """Merge backend entities without duplicating spans."""
    seen = {(item.start, item.end, item.label) for item in primary}
    merged = list(primary)
    for item in extra:
        key = (item.start, item.end, item.label)
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return sorted(merged, key=lambda item: item.start)
