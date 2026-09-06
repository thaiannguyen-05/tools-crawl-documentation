from __future__ import annotations

from collections.abc import Callable

from . import settings

FIELD_SEP = " </s> "
META_SEP = " | "
HEADING_SEP = " > "
SPECIAL_TOKENS = 2

# Injectable Vietnamese word-segmenter (e.g. RDRSegmenter/VnCoreNLP wrapper).
# When None, `segment_vietnamese` is a documented identity fallback.
_segmenter_fn: Callable[[str], str] | None = None


def set_segmenter(fn: Callable[[str], str] | None) -> None:
    global _segmenter_fn
    _segmenter_fn = fn


def segment_vietnamese(text: str) -> str:
    """Word-segment Vietnamese before PhoBERT BPE (hoc_sinh, not hoc sinh).

    Falls back to identity when no RDRSegmenter/VnCoreNLP is configured;
    call `set_segmenter` in production to plug the real segmenter.
    """
    if _segmenter_fn is not None:
        return _segmenter_fn(text)
    return text


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(len(text) // 4 + 1, 1)


def build_phobert_input(
    metadata_str: str,
    headings: list[str],
    content: str,
    token_len_fn: Callable[[str], int] | None = None,
    max_tokens: int | None = None,
    reserved_metadata_tokens: int | None = None,
) -> str:
    counter = token_len_fn or estimate_tokens
    budget = settings.max_tokens() if max_tokens is None else max_tokens
    reserved = (
        settings.reserved_tokens()
        if reserved_metadata_tokens is None
        else reserved_metadata_tokens
    )

    heading_part = HEADING_SEP.join(h for h in headings if h)
    prefix = metadata_str
    if heading_part:
        prefix = f"{prefix}{FIELD_SEP}{heading_part}" if prefix else heading_part

    # Reserve budget: metadata/headings never exceed their reservation.
    if counter(prefix) > reserved:
        prefix = _truncate_by_tokens(prefix, reserved, counter)

    prefix_tokens = counter(prefix) if prefix else 0
    content_budget = budget - SPECIAL_TOKENS - prefix_tokens
    if content_budget <= 0:
        return prefix

    truncated = _truncate_by_tokens(content, content_budget, counter) if content else ""
    if prefix and truncated:
        return f"{prefix}{FIELD_SEP}{truncated}"
    return prefix or truncated


def _truncate_by_tokens(
    text: str, budget: int, counter: Callable[[str], int]
) -> str:
    if budget <= 0 or not text:
        return ""
    if counter(text) <= budget:
        return text
    words = text.split()
    if not words:
        return ""
    lo, hi, best = 1, len(words), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if counter(" ".join(words[:mid])) <= budget:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return " ".join(words[:best])


def mean_pool_vectors(vectors: list[list[float]], mask: list[int]) -> list[float]:
    if not vectors or not mask or len(vectors) != len(mask):
        raise ValueError("vectors and mask must be non-empty and same length")
    dim = len(vectors[0])
    total = sum(mask)
    if total == 0:
        return [0.0] * dim
    acc = [0.0] * dim
    for vec, m in zip(vectors, mask):
        if m:
            for i, v in enumerate(vec):
                acc[i] += v
    return [a / total for a in acc]
