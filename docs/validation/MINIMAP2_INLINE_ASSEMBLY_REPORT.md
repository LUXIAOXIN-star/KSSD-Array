# Minimap2 public-inline assembly report

Date: 2026-07-31 (Asia/Shanghai)

## Build identity

- Upstream Minimap2 commit:
  `79c9cc186b95f50bd899f69b48eba995ced810c6` (`2.30-r1287`).
- Build output:
  `$KSSD_FORMAL_RESULTS/minimap2-inline-build-validation-20260731-213000`.
- Original executable SHA-256:
  `c87329169e7e2d489139ea56096c55649337e80f4a2f3abe631627620a5917c4`.
- Public-inline executable SHA-256:
  `05a58438f1d001daf8372d68d7426d4ab28d47228cf3153590fcce7c7b4f9c03`.
- Both Minimap2 source trees used `cc -g -Wall -O2 -Wc++-compat`.
- KSSD-Array was linked statically; `readelf -d` listed only `libm`, `libz`,
  `libpthread`, and `libc` as needed libraries.
- Neither the compiler/link command nor `readelf -SW` contained an LTO flag or
  GNU LTO section.  LTO was not enabled and is not relied upon.

The first development build directory,
`minimap2-inline-build-validation-20260731-210500`, is retained.  It records a
patch hunk line-count error; after correcting only that patch metadata, the
fresh build above passed for both executables.

## Final-ELF evidence

`nm -S -n` and `readelf -Ws` on the final public-inline executable showed:

```text
0000000000018b70 0000000000000d33 T mm_sketch
0000000000033690 0000000000000130 T kssd_array_inline_plan_init
00000000000337c0 0000000000000083 T kssd_array_map_unchecked
```

There is no `mm_kssd_array_map_unchecked` symbol.  The generic public symbol is
retained for ABI/API compatibility, but `objdump -dr -Mintel sketch.o` has no
relocation to it and `objdump -d -Mintel --disassemble=mm_sketch` has no call
to any KSSD mapping symbol.

The canonical-k-mer portion of final `mm_sketch` contains the small segment
count dispatch and direct table loads.  Representative instructions are:

```text
18e08: cmp    rcx,0x3
18e1e: cmp    rcx,0x1
18e24: cmp    rcx,0x2
18e3a: shr    rdi,cl
18e44: and    rcx,rdi
18e47: mov    rdi,QWORD PTR [r14+0x138]
18e4e: movzx  edi,WORD PTR [rdi+rcx*2]
18e5a: shl    rdi,cl
18e5d: or     r8,rdi
19070: cmp    rcx,0x4
1909e: movzx  r8d,WORD PTR [rdi+rcx*2]
190d5: movzx  r8d,WORD PTR [r8+rcx*2]
```

Calls visible elsewhere in `mm_sketch` are Minimap2 allocation and runtime
support calls (`krealloc`, checked memset, assertions, and stack checking),
not KSSD mapping calls.

## Result

**INLINE PATH CONFIRMED**

The final executable performs the table lookups and recombination inside
`mm_sketch`; no cross-translation-unit inlining or LTO claim is required.

## Formal S1 executable confirmation

The executable actually used by the completed three-dataset S1 run was
inspected independently after that run:

- Executable:
  `$KSSD_FORMAL_RESULTS/minimap2-indexing-s1-inline-final-20260731-214500/builds/integrated/source/minimap2`.
- SHA-256:
  `29da38889c244e97a902e476d1957172b9a0f726c5cb56285f6d49745b714b54`.
- `nm -S -n` reports `mm_sketch` at `0x18b70`,
  `kssd_array_inline_plan_init` at `0x33690`, and the compatibility
  `kssd_array_map_unchecked` symbol at `0x337c0`.
- No `mm_kssd_array_map_unchecked` symbol exists.
- Final-ELF `objdump` reports no call from `mm_sketch` to either prohibited
  mapping symbol.  The same direct `movzx ... WORD PTR` table loads and the
  one-to-four-segment dispatch shown above are present.
- `readelf -d` lists only `libm`, `libz`, `libpthread`, and `libc`; the final
  integration is statically linked to KSSD-Array and does not rely on LTO.

After the public build helper and automated checker were finalized, a fresh
build-only verification also reported `ORIGINAL_BUILD=PASS`,
`INTEGRATED_BUILD=PASS`, `PUBLIC_LIBRARY_LINK=PASS`, and
`INLINE_HOT_PATH=PASS`.  Its retained evidence is in
`$KSSD_FORMAL_RESULTS/minimap2-inline-final-build-check-20260731-234800`.
