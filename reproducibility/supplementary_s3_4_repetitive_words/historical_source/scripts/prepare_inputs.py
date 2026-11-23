from pathlib import Path
import json,gzip,hashlib,sys
R=Path(__file__).resolve().parents[1];D=Path(sys.argv[1]);(R/'cache').mkdir(exist_ok=True)
for d in json.loads((R/'input_manifest.json').read_text()):
 p=D/d['file'];h=hashlib.sha256()
 with p.open('rb')as f:
  while b:=f.read(1<<20):h.update(b)
 if h.hexdigest()!=d['gzip_sha256']:raise ValueError('Input differs from tested bytes: '+str(p))
 h=hashlib.sha256()
 with gzip.open(p,'rb')as f,(R/'cache'/f"{d['label']}.fna").open('wb')as g:
  while b:=f.read(1<<20):h.update(b);g.write(b)
 if h.hexdigest()!=d['fasta_sha256']:raise ValueError('Decompressed input mismatch')
 print('verified',d['label'])
