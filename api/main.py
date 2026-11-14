"""MIAUDOW data-first API. No synthetic climate series and no unsupported crop recommendation."""
from __future__ import annotations
import json
import os
import calendar
import datetime as dt
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

BASE=Path(__file__).resolve().parent
POWER_ENDPOINT='https://power.larc.nasa.gov/api/temporal/daily/point'
APP=FastAPI(title='MIAUDOW Evidence API',version='0.1.0')
origins=[x.strip() for x in os.getenv('MIAUDOW_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]
APP.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type'])

class Source(BaseModel):
    id:str
    title:str
    url:str
class CopilotRequest(BaseModel):
    question:str=Field(min_length=2,max_length=1200)
class CopilotResponse(BaseModel):
    answer:str
    evidence:list[Source]
    status:Literal['grounded','reference_only','insufficient_evidence']

@lru_cache(maxsize=1)
def facts()->list[dict]:
    return json.loads((BASE/'knowledge'/'facts.json').read_text(encoding='utf-8'))

def retrieve(question:str,limit:int=3)->list[dict]:
    q=question.lower()
    scored=[]
    for row in facts():
        score=sum(1 for term in row['keywords'] if term.lower() in q)
        if score:scored.append((score,row))
    return [x for _,x in sorted(scored,key=lambda a:-a[0])[:limit]]

def source_of(row:dict)->Source:
    return Source(id=row['source_id'],title=row['title'],url=row['url'])

def valid_value(v)->float|None:
    if v is None:return None
    try:
        v=float(v)
        if v<=-990 or v>=1e6:return None
        return v
    except (ValueError,TypeError):return None

def monthly_aggregation(parameters:dict,year:int)->list[dict]:
    """Daily NASA POWER PRECTOTCORR totals; daily T2M_MAX arithmetic mean. Missing remains null."""
    groups=defaultdict(lambda:{'rains':[],'temps':[]})
    rain=parameters.get('PRECTOTCORR',{})
    tmax=parameters.get('T2M_MAX',{})
    for mon in range(1,13):
        for day in range(1,calendar.monthrange(year,mon)[1]+1):
            k=f'{year}{mon:02}{day:02}'
            r=valid_value(rain.get(k));t=valid_value(tmax.get(k))
            if r is not None:groups[mon]['rains'].append(r)
            if t is not None:groups[mon]['temps'].append(t)
    out=[]
    for mon in range(1,13):
        row=groups[mon];total_days=calendar.monthrange(year,mon)[1]
        out.append(dict(month=mon,precipitation_mm=round(sum(row['rains']),1) if len(row['rains'])==total_days else None,
                        temp_max_c=round(sum(row['temps'])/len(row['temps']),1) if len(row['temps'])==total_days else None,
                        day_count=len(row['rains'])))
    return out

@APP.get('/api/health')
def health():return dict(status='ok',climate='on-demand API only',copilot='configured' if os.getenv('ANTHROPIC_API_KEY') and os.getenv('ANTHROPIC_MODEL') else 'not configured')

@APP.get('/api/sources')
def get_sources():return [{k:r[k] for k in ['id','title','url','claim_vi']} for r in facts()]

@APP.get('/api/climate')
async def climate(lat:float=Query(18.97,ge=-90,le=90),lon:float=Query(105.35,ge=-180,le=180),year:int=Query(2024,ge=1981,le=2025)):
    # Coordinates are explicitly samples; replace with verified AOI before any site-level interpretation.
    if year>dt.date.today().year:
        raise HTTPException(status_code=422,detail='Future years are not historical observations.')
    q=dict(parameters='PRECTOTCORR,T2M_MAX',community='AG',longitude=lon,latitude=lat,
           start=f'{year}0101',end=f'{year}1231',format='JSON',time_standard='LST')
    q['time-standard']=q.pop('time_standard')
    try:
        async with httpx.AsyncClient(timeout=40.0,follow_redirects=True) as client:
            r=await client.get(POWER_ENDPOINT,params=q)
            r.raise_for_status()
            payload=r.json()
    except (httpx.HTTPError,ValueError) as e:
        raise HTTPException(status_code=503,detail='Source NASA POWER unavailable; no substitute data generated.') from e
    params=payload.get('properties',{}).get('parameter',{})
    if not params or 'PRECTOTCORR' not in params or 'T2M_MAX' not in params:
        raise HTTPException(status_code=502,detail='NASA POWER response is missing requested variables.')
    return dict(provider='NASA POWER',year=year,lat=lat,lon=lon,source_type='model_assimilation_gridded',
                source_url='https://power.larc.nasa.gov/docs/services/api/temporal/daily/',months=monthly_aggregation(params,year),
                caveat_vi='Giá trị trên ô lưới mô hình, không phải đo trực tiếp trên thửa ruộng. Tổng mưa theo tháng không công bố khi thiếu ngày.')

@APP.post('/api/copilot',response_model=CopilotResponse)
async def copilot(payload:CopilotRequest):
    rows=retrieve(payload.question)
    if not rows:
        return CopilotResponse(answer='Kho bằng chứng hiện chưa có tài liệu đủ liên quan để trả lời chắc chắn câu hỏi này. Bạn có thể hỏi cán bộ khuyến nông hoặc bổ sung tài liệu đã được xác minh.',evidence=[],status='insufficient_evidence')
    refs=[source_of(r) for r in rows]
    key=os.getenv('ANTHROPIC_API_KEY')
    model=os.getenv('ANTHROPIC_MODEL')
    if not key or not model:
        claims='\n'.join(f'• {r["claim_vi"]}' for r in rows)
        return CopilotResponse(answer=f'Thông tin đã đối chiếu từ nguồn:\n{claims}\n\nChưa kết nối Claude API. Đây là các thông tin đã xác minh ở mức mô tả nguồn, không phải khuyến nghị canh tác cho một thửa ruộng.',evidence=refs,status='reference_only')
    context='\n'.join(f'ID: {r["id"]}\nClaim: {r["claim_vi"]}\nSource: {r["url"]}' for r in rows)
    system=('Bạn là trợ lý giải thích tài liệu nông nghiệp bằng tiếng Việt dễ hiểu. '
            'Chỉ được dùng các thông tin trong EVIDENCE dưới đây; không viện dẫn kiến thức ngoài hoặc đưa ra số liệu cụ thể không có nguồn. '
            'Nếu câu hỏi yêu cầu khuyến nghị canh tác, dự báo khí hậu, năng suất, giá bán hoặc tiền lãi tại ruộng mà dữ liệu không đủ, phải nói rõ chưa thể kết luận. '
            'Không nói giá trị NASA POWER là quan trắc trực tiếp tại ruộng. '
            'Phân biệt dữ liệu lịch sử và dự báo. Tối đa 180 từ, viết câu ngắn. '
            'Không tạo đường dẫn mới. Không tự ý trích dẫn nguồn chưa được cấp.')
    body={'model':model,'max_tokens':600,'system':system+'\n\nEVIDENCE:\n'+context,
          'messages':[{'role':'user','content':payload.question}]}
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            res=await client.post('https://api.anthropic.com/v1/messages',headers={
                'x-api-key':key,'anthropic-version':'2023-06-01','content-type':'application/json'},json=body)
            res.raise_for_status()
            content=res.json().get('content',[])
            answer=' '.join(c.get('text','') for c in content if c.get('type')=='text').strip()
    except (httpx.HTTPError,ValueError) as e:
        raise HTTPException(status_code=503,detail='Claude provider unavailable; no fabricated answer returned.') from e
    if not answer:
        raise HTTPException(status_code=502,detail='Empty provider response.')
    return CopilotResponse(answer=answer,evidence=refs,status='grounded')

app=APP
