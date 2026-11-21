# Minimap2 integration provenance

The reviewable patch targets Minimap2 2.30-r1287 commit
`79c9cc186b95f50bd899f69b48eba995ced810c6`. Patch SHA-256 is
`84ef84315357c7754180ff2c2b4a006877146dfa22986131aebcb842529e49e2`.
It calls public context and inline-plan initialization, destruction, and
status APIs. The hot loop includes the public always-inline mapper and does not
embed table construction or a private mapping implementation.

Each Minimap2 index owns one context and one borrowed inline plan. Workers share them read-only after
initialization, and destruction occurs after worker completion. Fixture tests
confirmed index and alignment thread consistency, ambiguous-base reset, HPC
mode, and explicit index-format compatibility checks. The integrated format
uses versioned magic `KSA1` and is intentionally not claimed to be compatible
with the upstream `MMI2` format.

Only the patch, scripts, and small fixtures are committed. Upstream source,
executables, indexes, and alignment outputs are excluded.
