"""Core modules for Chinese coreference resolution and rewriting."""

from .evaluator import ErrorCase, evaluate  # noqa: F401
from .nlp_backend import backend_status  # noqa: F401
from .rawdata_annotator import Coreference, Paragraph, annote, bind_ref  # noqa: F401
from .rawdata_gather import RawdataGather  # noqa: F401
from .resolver import CoreferenceResult, ResolverConfig, resolve_text  # noqa: F401
from .rewriter import rewrite_text  # noqa: F401
