"""Per-frame per-channel audibility resolution.

Consumes the HW-sim-augmented channels dict (see hw_sim.py) and produces
a dense per-frame Audibility value for each channel.  This is the
single source of truth for "is this channel sounding at frame N",
used downstream by MIDI projection, score notation, plugin state,
and CBG gate C validation.

The key W&W claim: triangle liveness transitions (AUDIBLE -> SILENT ->
AUDIBLE) driven by linear_live dissolve both the ring-over failure
(liveness stays true too long today) and the drop-out failure
(liveness goes false too early today).  Both are captured by the same
mechanism.
"""
from __future__ import annotations

import numpy as np

from .schema import Audibility, ChannelLiveness


def resolve_liveness(channels: dict) -> dict[str, ChannelLiveness]:
    """Build ChannelLiveness for each channel in the dict.

    Returns a dict keyed by channel name.  Only standard APU channels
    for Phase 1 -- expansion chips deferred.
    """
    result: dict[str, ChannelLiveness] = {}

    for ch_name in ("pulse1", "pulse2"):
        if ch_name in channels:
            result[ch_name] = _resolve_pulse(channels[ch_name]["notes"], ch_name)

    if "triangle" in channels:
        result["triangle"] = _resolve_triangle(channels["triangle"]["notes"])

    if "noise" in channels:
        result["noise"] = _resolve_noise(channels["noise"]["notes"])

    return result


def _resolve_pulse(frames: list, ch_name: str) -> ChannelLiveness:
    n = len(frames)
    live = np.zeros(n, dtype=np.int8)
    retrig = np.zeros(n, dtype=bool)
    for i, fd in enumerate(frames):
        retrig[i] = fd.get("phase_reset", False)
        period = fd.get("sweep_period", fd["period"])   # sweep-modulated
        vol = fd.get("effective_vol", fd["vol"])         # HW decay or SW-set
        if not fd.get("enabled", 1):
            live[i] = Audibility.GATED_OUT
        elif fd.get("sweep_muted", False) or period < 8:
            live[i] = Audibility.DEGENERATE
        elif vol <= 0:
            live[i] = Audibility.SILENT
        else:
            live[i] = Audibility.AUDIBLE
    return ChannelLiveness(channel=ch_name, frames=live, retrigger=retrig)


def _resolve_triangle(frames: list) -> ChannelLiveness:
    """Triangle liveness.  This is the W&W fix.

    Today's MIDI extractor uses `linear > 0` where linear is the LATCHED
    reload value -- which stays positive as long as the driver has
    written $4008 with a non-zero reload, even frames after the driver
    stopped writing $400B.  That's why W&W bass rings.

    Here we use `linear_live` -- the quarter-frame-simulated counter.
    It decays to 0 between driver retriggers, producing the articulation
    transitions the user expects to hear.
    """
    n = len(frames)
    live = np.zeros(n, dtype=np.int8)
    retrig = np.zeros(n, dtype=bool)
    for i, fd in enumerate(frames):
        retrig[i] = fd.get("phase_reset", False)
        if not fd.get("enabled", 1):
            live[i] = Audibility.GATED_OUT
        elif fd["period"] < 2:
            live[i] = Audibility.DEGENERATE
        elif fd.get("linear_live", fd.get("linear", 0)) <= 0:
            live[i] = Audibility.SILENT
        else:
            live[i] = Audibility.AUDIBLE
    return ChannelLiveness(channel="triangle", frames=live, retrigger=retrig)


def _resolve_noise(frames: list) -> ChannelLiveness:
    """Noise liveness.  Rule 30 gate + Rule 32 length counter.

    frames_to_channel_data already simulates length_counter, so this
    is a straight gate check.
    """
    n = len(frames)
    live = np.zeros(n, dtype=np.int8)
    retrig = np.zeros(n, dtype=bool)
    for i, fd in enumerate(frames):
        retrig[i] = fd.get("length_reload_frame", False)  # re-derived from $400F
        if not fd.get("enabled", 1):
            live[i] = Audibility.GATED_OUT
        elif fd["vol"] <= 0:
            live[i] = Audibility.SILENT
        elif fd.get("length_counter", 1) <= 0:
            live[i] = Audibility.SILENT
        else:
            live[i] = Audibility.AUDIBLE
    return ChannelLiveness(channel="noise", frames=live, retrigger=retrig)


def summarize(liveness: dict[str, ChannelLiveness]) -> str:
    """One-line summary per channel -- for CLI output / sanity check."""
    lines = []
    for name, cl in liveness.items():
        n = cl.n_frames
        audible = int((cl.frames == Audibility.AUDIBLE).sum())
        silent = int((cl.frames == Audibility.SILENT).sum())
        gated = int((cl.frames == Audibility.GATED_OUT).sum())
        degen = int((cl.frames == Audibility.DEGENERATE).sum())
        transitions = int(sum(1 for _ in cl.transitions()))
        retrig = int(cl.retrigger.sum())
        lines.append(
            f"  {name:9s}  {audible:5d} audible / {silent:5d} silent / "
            f"{gated:4d} gated / {degen:4d} degen  "
            f"({transitions} transitions, {retrig} retriggers)  of {n} frames"
        )
    return "\n".join(lines)
