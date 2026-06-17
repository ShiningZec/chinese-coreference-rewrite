import copy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Self  # noqa: F401

@dataclass
class Coreference:
    pronoun: str
    antecedent: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    def deepcopy(self) -> Self:
        return copy.deepcopy(self)

@dataclass
class Paragraph:
    text: str = ""
    coreference: List[Coreference] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def deepcopy(self) -> Self:
        return copy.deepcopy(self)
    
    def __len__(self) -> int:
        return len(self.text)
    
    def __getitem__(self, key) -> str:
        return self.text[key]

    def __iter__(self) -> Iterator[str]:
        return self.text.__iter__()


def annote(paragraph: Paragraph | str, s: int, t: int, ref_s: int, ref_t: int) -> Coreference:
    return Coreference(pronoun=paragraph[s:t], antecedent=paragraph[ref_s:ref_t])

def bind_ref(paragraph: Paragraph | str, annotations: Coreference | List[Coreference]) -> Paragraph:
    if isinstance(annotations, Coreference):
        annotations = list[annotations]
    if isinstance(paragraph, str):
        paragraph = Paragraph(paragraph)
    paragraph.coreference = copy.deepcopy(annotations)
    return paragraph


if __name__ == '__main__':
    corre = Coreference(pronoun="它", antecedent="“你好，世界”")
    para_raw = Paragraph(text="“你好，世界”，是一句让世界振奋的讯息，当它从电报机中问世。")
    print(para_raw.to_dict())
    para = bind_ref(para_raw, corre)
    print(para.to_dict())
    print(para[::-1])

    for idx, x in enumerate(para):
        print(f"{idx}: {x};")
