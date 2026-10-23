"""Optional Gemini advice using only explicitly authorized destination data."""
import json,os,re
from datetime import date,datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import requests

from analysis_prompt import ANALYSIS_PROMPT

def settings():
 values={}
 path=Path(__file__).with_name('.env')
 if path.exists():
  for line in path.read_text(encoding='utf-8-sig').splitlines():
   key,sep,value=line.strip().partition('=')
   if sep and not key.startswith('#'): values[key.strip()]=value.strip().strip('"').strip("'")
 return {k:os.environ.get(k,values.get(k,d)) for k,d in [('GEMINI_API_KEY',''),('GEMINI_MODEL','gemini-3.5-flash-lite')]}

def enrich(rows,cancel=None):
 config=settings();key=config['GEMINI_API_KEY'];model=config['GEMINI_MODEL']
 status='Key not configured'
 for r in rows: r['ai_engine']='Local rules'
 if not key: return status
 if not re.fullmatch(r'[a-zA-Z0-9.-]+',model): return 'Invalid model configuration'
 prompt=ANALYSIS_PROMPT
 entered=datetime.now(ZoneInfo('Asia/Kolkata')).date()
 target=date(entered.year+(entered.month==12),entered.month%12+1,1)
 status='Gemini complete'
 for start in range(0,len(rows),3):
  if cancel and cancel.is_set(): return 'Cancelled'
  batch=rows[start:start+3]
  data=[]
  for i,r in enumerate(batch):
   data.append(dict(id=i,asin=r['asin'],title=r.get('title'),category=r.get('category'),city=r['city'],pincode=r.get('pincode'),execution_date=entered.isoformat(),analysis_date=entered.isoformat(),target_month=target.strftime('%B'),target_year=target.year,temperature=r.get('temperature'),humidity=r.get('humidity'),precipitation=r.get('precipitation'),weather_time=r.get('weather_time'),weather_source=r.get('weather_source'),weather_url=r.get('weather_url'),weather_scope='City-level weather model; not PIN-code measurements',aqi_status='Unavailable',sales_status='Unavailable',purchase_badge=r.get('purchase_badge'),purchase_count_floor=r.get('purchase_count_floor'),purchase_scope='Approximate Amazon product-level recent purchases; not city sales'))
  schema={'type':'ARRAY','items':{'type':'OBJECT','properties':{k:{'type':'STRING'} for k in ['priority','suggestion','reason','season','general']}|{'id':{'type':'INTEGER'},'suitability_score':{'type':'INTEGER'}},'required':['id','priority','suggestion','reason','season','general','suitability_score']}}
  try:
   response=requests.post('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',headers={'x-goog-api-key':key},json={'contents':[{'parts':[{'text':prompt+json.dumps(data)}]}],'generationConfig':{'responseMimeType':'application/json','responseSchema':schema,'temperature':0,'maxOutputTokens':4096}},timeout=40)
   if response.status_code==429: return 'Gemini quota reached; local rules retained'
   if response.status_code in (400,401,403,404): return 'Gemini HTTP '+str(response.status_code)+' configuration/model access error; local rules retained'
   response.raise_for_status();candidate=response.json()['candidates'][0]
   if candidate.get('finishReason')!='STOP': return 'Gemini incomplete response; local rules retained'
   items=json.loads(''.join(part.get('text','') for part in candidate['content']['parts']))
   if not isinstance(items,list): return 'Gemini invalid response; local rules retained'
   seen=set()
   for item in items:
    i=item.get('id')
    if type(i) is not int or not 0<=i<len(batch) or i in seen: continue
    if item.get('priority') not in ('High','Medium','Low','Not ranked'): continue
    if any(not isinstance(item.get(k),str) or not item[k].strip() or len(item[k])>2500 for k in ('suggestion','reason','season','general')): continue
    score=item.get('suitability_score')
    if type(score) is not int or not 0<=score<=100: continue
    r=batch[i]
    if not r.get('title'): continue
    seen.add(i)
    r.update(ai_general_reason=item['general'],seasonal_suitability_score=score,seasonal_priority=item['priority'],target_month=target.strftime('%B %Y'),target_year=target.year,sell_advice=item['suggestion'],ai_seasonal_reason=item['reason']+' Typical season (AI hypothesis): '+item['season'],ai_engine='Gemini '+model,basis='AI next-month typical-climate assessment; separate from measured current weather; no sales data or weather forecast')
  except (requests.RequestException,ValueError,KeyError,IndexError,TypeError,AttributeError):
   return 'Gemini unavailable; local rules retained'
 accepted=sum(r.get('ai_engine','').startswith('Gemini ') for r in rows)
 if accepted<len(rows): return f'Gemini partial: {accepted}/{len(rows)} recommendations accepted; missing or invalid product assessments retained local rules'
 return status
