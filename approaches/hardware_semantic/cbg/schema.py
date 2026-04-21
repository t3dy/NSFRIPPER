"""CBG schema -- Phase 1 minimum.

Deliberately narrow: only what's needed to close the W&W triangle
liveness bug + produce MIDI with correct note boundaries.  The
full event taxonomy from DESIGN.md section 2 will land in Phase 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np


class Audibility(IntEnum):
    """Per-frame per-channel audibility.

    AUDIBLE      -- channel DAC output is non-zero this frame
    SILENT       -- any soft gate false (vol=0, linear=0, LC=0, period too low)
    GATED_OUT    -- $4015 bit explicitly cleared
    DEGENERATE   -- HW-edge range (sweep mute, period < 2 on triangle)
    """
    DEGENERATE = -2
    GATED_OUT = -1
    SILENT = 0
    AUDIBLE = 1


@dataclass
class ChannelLiveness:
    """Dense per-frame audibility for one channel."""
    channel: str                       # pulse1, pulse2, triangle, noise, dmc
    frames: np.ndarray                 # int8, one Audibility per frame
    # Per-frame articulation flags (pulled up from hw_sim for MIDI projection)
    retrigger: np.ndarray              # bool, phase_reset / linear_reload / LC_reload this frame

    @property
    def n_frames(self) -> int:
        return len(self.frames)

    def is_audible(self, f: int) -> bool:
        return self.frames[f] == Audibility.AUDIBLE

    def transitions(self):
        """Yield (frame, prev_state, new_state) at each audibility transition."""
        prev = None
        for i, v in enumerate(self.frames):
            if v != prev:
                yield i, prev, int(v)
                prev = int(v)
