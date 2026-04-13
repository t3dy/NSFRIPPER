# Wizards & Warriors Title Hidden APU State IR Report

## Summary

- This artifact preserves hidden-state interpretations that the current export path flattens.
- Pulse channels retain constant-volume-vs-envelope mode separately from the low nibble.
- Triangle retains linear reload and control bit separately from any claimed live gate/counter state.

## Key Frames

- Frame `928`: pulse1=`hardware_envelope` nibble `5` effvol `15` duty `1`, pulse2=`hardware_envelope` nibble `3` effvol `15` duty `1`, triangle reload=`1` control=`1` modeled_counter=`1`.
- Frame `960`: pulse1=`hardware_envelope` nibble `5` effvol `15` duty `1`, pulse2=`hardware_envelope` nibble `3` effvol `15` duty `1`, triangle reload=`1` control=`1` modeled_counter=`1`.
- Frame `976`: pulse1=`hardware_envelope` nibble `5` effvol `15` duty `1`, pulse2=`hardware_envelope` nibble `3` effvol `15` duty `1`, triangle reload=`1` control=`1` modeled_counter=`1`.

## Consequence

- A pulse byte like `0x45` should not be read as steady volume `5` when `const_vol=0`.
- Under a standard APU envelope model, the pulse effective volume falls over time after each timer-high retrigger.
- A triangle byte like `0x81` should not be read as live linear counter `1`; it is only the reload/control register.
- Under a standard linear-counter model with control bit `1`, the triangle counter remains armed, so pulse envelope behavior may be the stronger immediate missing hardware layer.

These hidden-state fields need to exist before we can model true harpsichord-like pulse decay or muted plucked-bass triangle behavior.