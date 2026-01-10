"""Wait time constants in seconds for sleep operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WaitTimes:
    """
    Wait times in seconds for various operations.

    These are used for time.sleep() operations between actions.
    """

    # Very short pause (UI animations)
    VERY_SHORT: float = 2.0
    VERY_SHORT_WAIT: float = 2.0

    # Short pause (between actions)
    SHORT: float = 5.0
    SHORT_WAIT: float = 5.0

    # Medium pause (page loads)
    MEDIUM: float = 10.0
    MEDIUM_WAIT: float = 10.0

    # Activity cycle (audio playback)
    ACTIVITY_CYCLE: float = 50.0
