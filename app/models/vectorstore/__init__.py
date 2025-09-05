import inspect
import sys

from .base import BaseModel as PGVectorModel
from .semantic_retrieval import SemanticSearchModel

__all__ = ["SemanticSearchModel"]


def list_vector_store_models() -> list[PGVectorModel]:
    return [
        model
        for _, model in inspect.getmembers(sys.modules[__name__])
        if inspect.isclass(model)
        and issubclass(model, PGVectorModel)
        and model.__tablename__ is not None
    ]
