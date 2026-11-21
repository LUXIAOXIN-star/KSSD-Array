#!/usr/bin/env python3
"""Portable SplitMix64, seed=42, one base from the low two output bits."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data"
MASK = (1 << 64) - 1
state = 42
bases = bytearray()
for _ in range(10_000_000):
    state = (state + 0x9e3779b97f4a7c15) & MASK
    z = state
    z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & MASK
    z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & MASK
    z ^= z >> 31
    bases.append(b'ACGT'[z & 3])
files = {'synthetic_10mb.dna': bytes(bases) + b'\n',
         'synthetic_10mb.fasta': b'>splitmix64_seed42_length10000000\n' + b'\n'.join(bytes(bases[i:i+80]) for i in range(0,len(bases),80)) + b'\n'}
manifest = {'generator':'SplitMix64, low 2 bits to A/C/G/T', 'seed':42,
            'bases':len(bases), 'normalized_sequence_sha256':hashlib.sha256(bases).hexdigest(),
            'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
files['MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
for name, data in files.items():
    path = ROOT / name
    if path.exists():
        if path.read_bytes() != data:
            raise SystemExit(f'Refusing to replace differing existing fixture: {path}')
    else:
        with path.open('xb') as f: f.write(data)
print('Synthetic fixture ready: exactly 10,000,000 bases; no external data downloaded.')
