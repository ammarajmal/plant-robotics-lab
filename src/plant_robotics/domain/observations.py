"""Hardware-independent target observation contracts."""

from dataclasses import dataclass
from enum import StrEnum


class TrackState(StrEnum):
    VISIBLE = "visible"
    PARTIALLY_OCCLUDED = "partially_occluded"
    PREDICTED = "predicted"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class TargetObservation:
    target_id: str
    camera_id: str
    frame_index: int
    state: TrackState
    x_px: float | None = None
    y_px: float | None = None
    identity_valid: bool = False

    @property
    def safe_to_act(self) -> bool:
        # This is only an identity/observation gate, NOT comprehensive robot safety.
        return (
            self.state is TrackState.VISIBLE
            and self.identity_valid
            and self.x_px is not None
            and self.y_px is not None
        )
