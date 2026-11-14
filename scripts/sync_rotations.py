"""Compile the audited YAML source into frontend fixtures. Raises on unsourced claims."""
from pathlib import Path
import json
import yaml
ROOT=Path(__file__).resolve().parents[1]
data=yaml.safe_load((ROOT/'api/rules/rotations.yaml').read_text(encoding='utf-8'))
verified={s['id'] for s in data['source_documents'] if s['verification']=='verified' and s['approved_for_recommendation']}
out=[]
for r in data['rotations']:
 for line in r.get('risk_lines',[]):
  assert isinstance(line,dict),f'Risk line must be structured: {r["id"]}'
  assert all(line.get(k) for k in ('text_vi','source_id','document_page','quote')),'Unsourced risk claim'
  assert line['source_id'] in verified,f'Unverified source for risk: {r["id"]}'
 assert r['status']=='illustrative_unverified' or all(x in verified for x in r['evidence_refs'])
 out.append(dict(id=r['id'],name=r['title'].replace(' - ',' · '),seasons=r['seasons_vi'],months=r['calendar_months'],kind='Cơ cấu tham khảo',status=r['status'],risk_lines=r.get('risk_lines',[])))
(ROOT/'web/src/rotations.generated.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Generated',len(out),'rotations from single audited YAML source')
