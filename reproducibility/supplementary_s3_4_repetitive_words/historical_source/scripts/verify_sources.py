from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
expected={'include/kssd_array.h':'2a9a48b300de247017add07c729bdd9d1461b4d6','include/kssd_array_inline.h':'a99f323d318d87f809d5a79669cf09e5b161e958','src/kssd_array.c':'1668ec58b46f2c75254035859e36a8ac8eb509f2','src/permutation.c':'ed08eb7b6987285be6624ec419658049f269afe5','src/permutation.h':'afe35f89a8137e86a665c83694b5d1fd5988ddf7','LICENSE':'7cd2e60a561f54ed65164ffc2707754c2204673a'}
for name,want in expected.items():
 b=(R/'production'/name).read_bytes();got=hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
 if got!=want:raise RuntimeError(f'source mismatch: {name}')
print('PASS: five unchanged production files and MIT license')
