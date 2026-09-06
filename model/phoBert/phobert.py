from __future__ import annotations

from typing import Protocol

from file_process.errors import ModelUnavailableError
from file_process import settings

_MODEL_NAME = "vinai/phobert-large"


class _Tensor(Protocol):
    def unsqueeze(self, dim: int) -> _Tensor: ...
    def expand(self, sizes: tuple[int, ...]) -> _Tensor: ...
    def float(self) -> _Tensor: ...
    def sum(self, dim: int) -> _Tensor: ...
    def clamp(self, min: float) -> _Tensor: ...
    def squeeze(self) -> _Tensor: ...
    def cpu(self) -> _Tensor: ...
    def numpy(self) -> _NumpyArray: ...
    def size(self) -> tuple[int, ...]: ...
    def __mul__(self, other: _Tensor) -> _Tensor: ...
    def __truediv__(self, other: _Tensor) -> _Tensor: ...
    def __getitem__(self, key: str) -> _Tensor: ...


class _NumpyArray(Protocol):
    def tolist(self) -> object: ...


class _BatchEncoding(Protocol):
    def keys(self) -> object: ...
    def __getitem__(self, key: str) -> _Tensor: ...


class _Tokenizer(Protocol):
    def __call__(
        self,
        text: str | list[str],
        *,
        return_tensors: str,
        padding: bool,
        truncation: bool,
        max_length: int,
    ) -> _BatchEncoding: ...


class _ModelOutput(Protocol):
    @property
    def last_hidden_state(self) -> _Tensor: ...


class _Model(Protocol):
    def __call__(self, **kwargs: object) -> _ModelOutput: ...
    def eval(self) -> None: ...


_tokenizer: _Tokenizer | None = None
_model: _Model | None = None


def _segment(text: str) -> str:
    """Vietnamese word-segmentation hook (RDRSegmenter/VnCoreNLP).

    Falls back to identity only when the tokenizer module itself is missing;
    a configured segmenter that crashes at runtime must fail loudly.
    """
    try:
        from file_process.tokenizer import segment_vietnamese
    except ImportError:
        return text
    return segment_vietnamese(text)


def prepare_text(text: str) -> str:
    return _segment(text)


def _load() -> None:
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        import torch  # noqa: F401
        from transformers import AutoModel, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModel.from_pretrained(_MODEL_NAME)
        _model.eval()


def _ready() -> tuple[_Tokenizer, _Model]:
    _load()
    if _tokenizer is None or _model is None:
        raise ModelUnavailableError("PhoBERT model failed to initialize")
    return _tokenizer, _model


def _mean_pool(last_hidden_state: _Tensor, attention_mask: _Tensor) -> _Tensor:
    # Design: attention-mask-aware mean pooling (not CLS). A learned attention
    # layer (v = sum w_i h_i) is parked until query-doc training pairs exist.
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = (last_hidden_state * mask).sum(1)
    counts = mask.sum(1).clamp(min=1e-9)
    return summed / counts


def _to_float_list(raw: object) -> list[float]:
    if not isinstance(raw, list):
        raise ModelUnavailableError(
            "PhoBERT returned an unexpected embedding shape",
            details=type(raw).__name__,
        )
    return [float(v) for v in raw]


def encode(text: str, max_length: int | None = None) -> list[float]:
    import torch

    tokenizer, model = _ready()
    budget = settings.max_tokens() if max_length is None else max_length
    inputs = tokenizer(
        prepare_text(text),
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=budget,
    )
    with torch.no_grad():
        outputs = model(**inputs)
    pooled = _mean_pool(outputs.last_hidden_state, inputs["attention_mask"])
    return _to_float_list(pooled.squeeze().cpu().numpy().tolist())


def batch_encode(
    texts: list[str],
    batch_size: int | None = None,
    max_length: int | None = None,
) -> list[list[float]]:
    import torch

    tokenizer, model = _ready()
    size = settings.batch_size() if batch_size is None else batch_size
    budget = settings.max_tokens() if max_length is None else max_length
    results: list[list[float]] = []
    prepared = [prepare_text(t) for t in texts]
    for i in range(0, len(prepared), size):
        batch = prepared[i : i + size]
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=budget,
        )
        with torch.no_grad():
            outputs = model(**inputs)
        pooled = _mean_pool(outputs.last_hidden_state, inputs["attention_mask"])
        results.extend(_to_float_list(v.cpu().numpy().tolist()) for v in pooled)
    return results
