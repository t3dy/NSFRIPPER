"""Hardware state-machine simulation, lifted from the stems renderer.

The stems renderer (scripts/render_channel_stems.py) has the correct
per-frame HW state machine but runs it at *render* time to decide what
to synthesize.  This module runs the same simulation at *middle-layer*
time so MIDI projection, JSFX, and audio rendering all share the same
liveness decisions.

Rule alignment:
  * Rule 29 -- phase_reset / linear_reload / sweep events captured per-frame
  * Rule 32 -- noise length counter simulation (already in frames_to_channel_data)
  * Rule 34 -- triangle hold on gate-off (synthesis-layer, not here)
  * Rule 36 -- $4015=$0F before INIT (extractor-layer, not here)

Contract: mutates the `channels` dict from frames_to_channel_data in place,
adding per-frame scalar fields to each `notes[i]`:

  pulse1 / pulse2:
    hw_decay        int  -- simulated HW envelope decay counter 0..15
    effective_vol   int  -- const_vol ? env_period : hw_decay
    sweep_period    int  -- sweep-unit-modulated period
    sweep_muted     bool -- sweep target > 0x7FF or period < 8

  triangle:
    linear_live     int  -- live linear counter 0..127

  noise:
    (length_counter already present from frames_to_channel_data)
"""
from __future__ import annotations


def simulate_hw_state(channels: dict) -> None:
    """Run HW state machines forward, augmenting channels in place.

    This is a line-for-line lift of the per-frame simulation in
    scripts/render_channel_stems.py::render_stem (lines 241-327),
    minus the synthesis (waveform generation).
    """
    _simulate_pulse_envelope_and_sweep(channels, "pulse1", negate_offset=1)
    _simulate_pulse_envelope_and_sweep(channels, "pulse2", negate_offset=0)
    _simulate_triangle_linear(channels)


def _simulate_pulse_envelope_and_sweep(channels: dict, ch_name: str,
                                       negate_offset: int) -> None:
    """HW envelope (240 Hz quarter-frame) + sweep (120 Hz half-frame).

    Mirrors render_channel_stems.py lines 241-327 for pulse channels.
    """
    frames = channels[ch_name]["notes"]
    if not frames:
        return

    env_decay = 15
    env_divider = 0
    env_start_flag = False

    sw_divider = 0
    sw_muted = False
    sw_period = 0

    for fd in frames:
        # --- HW envelope: 4 quarter-frame ticks per 60 Hz frame ---
        if fd.get("phase_reset", False):
            env_start_flag = True
        period = fd["env_period"]
        loop = fd["env_loop"]
        for _ in range(4):
            if env_start_flag:
                env_decay = 15
                env_divider = period
                env_start_flag = False
            else:
                if env_divider == 0:
                    if env_decay > 0:
                        env_decay -= 1
                    elif loop:
                        env_decay = 15
                    env_divider = period
                else:
                    env_divider -= 1

        # --- Sweep unit: 2 half-frame ticks per 60 Hz frame ---
        sw_period = fd["period"]  # driver may have written new period
        for _ in range(2):
            if sw_divider == 0:
                if (fd["sweep_en"] and fd["sweep_shift"] > 0 and not sw_muted):
                    change = sw_period >> fd["sweep_shift"]
                    if fd["sweep_negate"]:
                        change = -change - negate_offset
                    target = sw_period + change
                    if target > 0x7FF or sw_period < 8:
                        sw_muted = True
                    else:
                        sw_period = target
                sw_divider = fd["sweep_period"]
            else:
                sw_divider -= 1
        if not fd["sweep_en"]:
            sw_muted = False

        # --- Effective volume ---
        effective_vol = fd["env_period"] if fd["const_vol"] else env_decay

        fd["hw_decay"] = env_decay
        fd["effective_vol"] = effective_vol
        fd["sweep_period"] = sw_period
        fd["sweep_muted"] = sw_muted


def _simulate_triangle_linear(channels: dict) -> None:
    """Triangle linear counter live sim (240 Hz quarter-frame).

    Lifted from render_channel_stems.py lines 292-303.

    Quarter-frame behavior:
      * If reload_flag is set: linear_counter = reload_value
      * Else if linear_counter > 0: linear_counter -= 1
    At end of quarter-frame, reload_flag is cleared iff control_bit == 0.

    $400B write sets reload_flag (captured as phase_reset).
    $4008 latches reload_value and control_bit.
    """
    frames = channels["triangle"]["notes"]
    if not frames:
        return

    linear_live = 0
    reload_flag = False

    for fd in frames:
        if fd.get("phase_reset", False):
            reload_flag = True
        control = fd["linear_control"]
        reload_value = fd["linear_reload"]
        for _ in range(4):
            if reload_flag:
                linear_live = reload_value
            elif linear_live > 0:
                linear_live -= 1
            if control == 0:
                reload_flag = False
        fd["linear_live"] = linear_live
