"""OpenAI recommendations from verified product and destination evidence."""
import json
import os
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from analysis_prompt import ANALYSIS_PROMPT


def error_kind(response):
 try:
  error = response.json().get('error', {})
  return error.get('code') or error.get('type') or ''
 except (ValueError, TypeError, AttributeError):
  return ''


def post_with_retry(cancel=None, **kwargs):
 for attempt in range(3):
  response = requests.post('https://api.openai.com/v1/responses', **kwargs)
  if response.status_code != 429 or error_kind(response) not in ('rate_limit_exceeded', 'rate_limit_error', 'slow_down') or attempt == 2:
   return response
  delay = 2 ** (attempt + 1)
  try:
   delay = max(delay, float(response.headers.get('Retry-After', delay)))
   if delay > 30:
    return response
  except (ValueError, TypeError, AttributeError):
   pass
  if cancel:
   if cancel.wait(delay):
    return response
  else:
   time.sleep(delay)
 return response


def settings():
 values = {}
 path = Path(__file__).with_name('.env')
 if path.exists():
  for line in path.read_text(encoding='utf-8-sig').splitlines():
   key, sep, value = line.strip().partition('=')
   if sep and not key.startswith('#'):
    values[key.strip()] = value.strip().strip('"').strip("'")
 return {key: os.environ.get(key, values.get(key, default)) for key, default in
         [('OPENAI_API_KEY', ''), ('OPENAI_MODEL', 'gpt-4.1-mini')]}


def enrich(rows, cancel=None):
 config = settings()
 for row in rows:
  row['ai_engine'] = 'Local rules'
 if not config['OPENAI_API_KEY']:
  return 'OpenAI API key not configured; local rules retained'
 today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
 target = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
 fields = ('suggestion', 'reason', 'season', 'general')
 properties = {field: {'type': 'string'} for field in fields}
 properties.update(id={'type': 'integer'}, priority={'type': 'string', 'enum': ['High', 'Medium', 'Low', 'Not ranked']}, suitability_score={'type': 'integer', 'minimum': 0, 'maximum': 100})
 schema = {'type': 'object', 'properties': {'recommendations': {'type': 'array', 'items': {
  'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}}},
  'required': ['recommendations'], 'additionalProperties': False}
 instructions = ANALYSIS_PROMPT + '\nFor this API, wrap the requested JSON array in an object with the key recommendations, as specified in the output schema.'
 for start in range(0, len(rows), 3):
  if cancel and cancel.is_set():
   return 'Cancelled'
  batch = rows[start:start + 3]
  data = []
  for index, row in enumerate(batch):
   evidence = {key: row.get(key) for key in ('asin', 'title', 'brand', 'category', 'city', 'pincode', 'temperature', 'humidity', 'precipitation', 'weather_time', 'weather_source', 'weather_url', 'purchase_badge', 'purchase_count_floor')}
   evidence.update(id=index, execution_date=today.isoformat(), target_month=target.strftime('%B'), target_year=target.year,
                   weather_scope='City-level model; not PIN-code measurements', aqi_status='Unavailable',
                   sales_status='Unavailable', purchase_scope='Approximate Amazon product-level recent purchases; not city sales')
   data.append(evidence)
  try:
   response = post_with_retry(cancel,
    headers={'Authorization': 'Bearer ' + config['OPENAI_API_KEY']},
    json={'model': config['OPENAI_MODEL'], 'instructions': instructions, 'input': json.dumps(data),
          'store': False, 'max_output_tokens': 6000,
          'text': {'format': {'type': 'json_schema', 'name': 'seasonal_recommendations', 'strict': True, 'schema': schema}}},
    timeout=60)
   if response.status_code == 429:
    if cancel and cancel.is_set():
     return 'Cancelled'
    kind = error_kind(response)
    if kind in ('insufficient_quota', 'billing_hard_limit_reached', 'credit_balance_exhausted', 'organization_spend_limit_exceeded', 'project_spend_limit_exceeded', 'organization_usage_limit_exceeded'):
     return 'OpenAI API billing/credits quota unavailable; check API project billing and usage limits, then run a new check; local rules retained'
    if kind in ('rate_limit_exceeded', 'rate_limit_error', 'slow_down'):
     return 'OpenAI temporary rate limit; automatic retry limit or long server wait reached; wait and run a new check; local rules retained'
    return 'OpenAI quota/rate limit reached; local rules retained'
   if response.status_code in (400, 401, 403, 404):
    return f'OpenAI HTTP {response.status_code} configuration/model access error; local rules retained'
   response.raise_for_status()
   result = response.json()
   if result.get('status') != 'completed':
    return 'OpenAI incomplete response; local rules retained'
   content = [part for output in result.get('output', []) if output.get('type') == 'message' for part in output.get('content', [])]
   if any(part.get('type') == 'refusal' for part in content):
    return 'OpenAI declined assessment; local rules retained'
   items = json.loads(''.join(part.get('text', '') for part in content if part.get('type') == 'output_text'))['recommendations']
   if not isinstance(items, list):
    return 'OpenAI invalid response; local rules retained'
   seen = set()
   for item in items:
    if not isinstance(item, dict):
     continue
    index = item.get('id')
    if type(index) is not int or not 0 <= index < len(batch) or index in seen:
     continue
    if item.get('priority') not in ('High', 'Medium', 'Low', 'Not ranked'):
     continue
    if any(not isinstance(item.get(field), str) or not item[field].strip() or len(item[field]) > 2500 for field in fields):
     continue
    score = item.get('suitability_score')
    if type(score) is not int or not 0 <= score <= 100 or not batch[index].get('title'):
     continue
    seen.add(index)
    batch[index].update(ai_engine='OpenAI ' + config['OPENAI_MODEL'], ai_general_reason=item['general'],
     seasonal_suitability_score=score, seasonal_priority=item['priority'], target_month=target.strftime('%B %Y'),
     target_year=target.year, sell_advice=item['suggestion'],
     ai_seasonal_reason=item['reason'] + ' Typical season (AI hypothesis): ' + item['season'],
     basis='AI next-month seasonal assessment using supplied evidence; no verified sales forecast')
  except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
   return 'OpenAI unavailable or invalid response; local rules retained'
 accepted = sum(row.get('ai_engine', '').startswith('OpenAI ') for row in rows)
 return 'OpenAI complete' if accepted == len(rows) else f'OpenAI partial: {accepted}/{len(rows)} recommendations accepted; local rules retained for remaining rows'
