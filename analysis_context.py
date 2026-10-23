from datetime import datetime
from zoneinfo import ZoneInfo
from recommendations import fetch_weather

def capture_context(data,cities):
 now=datetime.now(ZoneInfo('Asia/Kolkata'))
 try:
  entered=datetime.fromisoformat(str(data.get('entered_at')).replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Kolkata')) if data.get('entered_at') else now
  if entered>now: entered=now
 except (ValueError,TypeError): entered=now
 source=next((city for city in cities if city['id']==data.get('source_city_id')),None)
 return dict(entered_at=entered.isoformat(),analysis_date=entered.date().isoformat(),month=entered.strftime('%B'),source_city=source,source_location=source['name'] if source else 'Unavailable — browser location not granted or no nearby listed city',location_basis='Nearest listed city matched locally in browser; precise coordinates are not transmitted',source_weather=dict(status='unavailable',source='Open-Meteo',reason='Source city unavailable'))

def resolve_context(context):
 if context.get('source_city'): context['source_weather']=fetch_weather(context['source_city'])
 return context
