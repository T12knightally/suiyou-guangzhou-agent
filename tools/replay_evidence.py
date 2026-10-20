"""Restore historical evidence for local playback; no API calls."""
import json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
summary=json.loads((ROOT/'evidence/repairs/latest.json').read_text(encoding='utf-8'))
source=ROOT/summary['evidence_dir'];target=ROOT/'runs';target.mkdir(exist_ok=True)
for path in source.glob('*.json'):
 r=json.loads(path.read_text(encoding='utf-8'));rid=r.get('run_id','')
 if re.fullmatch('[a-f0-9]{16}',rid) and not (target/(rid+'.json')).exists():shutil.copyfile(path,target/(rid+'.json'))
print('Historical results ready, no API calls. Main run: 85fb96702ab84d8d')
