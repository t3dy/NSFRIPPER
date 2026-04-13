# Wizards & Warriors Title Release IR Report

## Summary

- This artifact classifies frame-level triangle body behavior in the disputed title phrase.
- Window: `920-980`.
- Audio offset: `0` frames.

## Class Counts

- `fresh_attack_damped_body`: `1` frame(s).
- `fresh_full_body`: `2` frame(s).
- `ringing_decay`: `36` frame(s).
- `sustain_body`: `22` frame(s).

## Key Frames

- Frame `928`: class=`fresh_full_body`, tri_hidden=`False`, pulse1_hidden=`True`, composite=`False`, low_norm=`0.94`, high_norm=`0.81`.
- Frame `960`: class=`fresh_attack_damped_body`, tri_hidden=`True`, pulse1_hidden=`True`, composite=`True`, low_norm=`0.48`, high_norm=`1.00`.
- Frame `961`: class=`ringing_decay`, tri_hidden=`False`, pulse1_hidden=`False`, composite=`False`, low_norm=`0.45`, high_norm=`0.99`.
- Frame `976`: class=`fresh_full_body`, tri_hidden=`False`, pulse1_hidden=`False`, composite=`False`, low_norm=`0.89`, high_norm=`0.73`.

## Interpretation

- Frame `928` should read as a strong bass-body onset.
- Frame `960` should read as a fresh attack with reduced body, not as a continuing full sustain.
- Frame `976` should read as the next full-bodied bass onset.

This is the release-side evidence for adding a damping/release field to the middle layer.