import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Self  # noqa: F401

from .rawdata_annotator import Paragraph

class RawdataGather:
    default_data = ["小王喜欢小美，但是她不喜欢他。", "小美喜欢小刚，但是他喜欢小玉。"]

    def __init__(self, path: str | Path):
        if isinstance(path, str):
            path = Path(path)
        self.path = path
    
    def gather(self, filename: str | None = None) -> List[str]:
        """
        :Params:

        filename: str | None, location of the input file

        :What's in the input?:

        Lines of texts.
        """
        if filename is None:
            return RawdataGather.default_data
        elif len(filename) == 0:
            return RawdataGather.default_data
        else:
            try:
                with open(filename, encoding='utf-8') as f:
                    raw_data = f.read().strip()
                raw_data = raw_data.split('\n')
                stripped_data = [data.strip() for data in raw_data if len(data.strip()) > 0]
                return stripped_data
            except OSError:
                return RawdataGather.default_data

    def dump(self, paras: List[Paragraph], filename: str):
        with open(self.path / filename, 'w', encoding='utf-8') as f:
            json.dump([para.to_dict() for para in paras], f, indent=2, ensure_ascii=False)
