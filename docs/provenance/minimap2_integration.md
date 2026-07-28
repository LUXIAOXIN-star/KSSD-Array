# Minimap2 integration provenance

The reviewable patch targets Minimap2 2.30-r1287 commit
`79c9cc186b95f50bd899f69b48eba995ced810c6`. Patch SHA-256 is
`89610194db47197c3eeb4ddee4c38c9233f00251246dd9210b597616791ba572`.
It calls the public initialization, unchecked mapping, destruction, and status
APIs; it does not embed table construction or mapping code.

Each Minimap2 index owns one context. Workers share it read-only after
initialization, and destruction occurs after worker completion. Fixture tests
confirmed index and alignment thread consistency, ambiguous-base reset, HPC
mode, and explicit index-format compatibility checks. The integrated format
uses versioned magic `KSA1` and is intentionally not claimed to be compatible
with the upstream `MMI2` format.

Only the patch, scripts, and small fixtures are committed. Upstream source,
executables, indexes, and alignment outputs are excluded.
