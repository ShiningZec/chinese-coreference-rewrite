import json
from pathlib import Path
from typing import Any, Dict, List, Self  # noqa: F401

from .rawdata_annotator import Paragraph

class RawdataGather:
    def __init__(self, path: str | Path):
        if isinstance(path, str):
            path = Path(path)
        self.path = path
    
    def gather(self):
        # Not Implemented Yet
        return ["小王喜欢小美，但是她不喜欢他。"]

    def dump(self, paras: List[Paragraph], filename: str):
        with open(self.path / filename, 'w', encoding='utf-8') as f:
            json.dump([para.to_dict() for para in paras], f, indent=2, ensure_ascii=False)
