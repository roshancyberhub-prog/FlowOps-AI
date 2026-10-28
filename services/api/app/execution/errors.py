import random
import traceback
from dataclasses import dataclass
from pathlib import Path


class NodeFailure(Exception):
    def __init__(
        self, code: str, message: str, *, transient: bool = False, uncertain: bool = False
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.transient = transient
        self.uncertain = uncertain


@dataclass(frozen=True)
class FailureInfo:
    code: str
    summary: str
    retryable: bool
    uncertain: bool = False
    frames: tuple[str, ...] = ()


def classify_error(error: Exception, side_effect: str) -> FailureInfo:
    frames = tuple(
        f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"
        for frame in traceback.extract_tb(error.__traceback__)
    )
    if isinstance(error, NodeFailure):
        return FailureInfo(
            error.code,
            error.message[:500],
            error.transient and not error.uncertain,
            error.uncertain,
            frames,
        )
    if isinstance(error, TimeoutError):
        uncertain = side_effect == "external"
        return FailureInfo(
            "UNCERTAIN_EXTERNAL_RESULT" if uncertain else "NODE_TIMEOUT",
            "The external result is uncertain; reconcile it before any new send."
            if uncertain
            else "The node exceeded its time limit.",
            not uncertain,
            uncertain,
            frames,
        )
    return FailureInfo(
        "NODE_ERROR",
        "The node could not complete. Review its configuration and details.",
        False,
        False,
        frames,
    )


def should_retry(failure: FailureInfo, attempt: int, max_attempts: int = 3) -> bool:
    return failure.retryable and not failure.uncertain and attempt < max_attempts


def retry_delay(attempt: int) -> float:
    return min(60.0, 2 ** min(max(attempt - 1, 0), 5) * 2 + random.random())
