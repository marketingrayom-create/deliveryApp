from datetime import datetime
from zoneinfo import ZoneInfo
import requests,re
CATEGORIES=('auto','fan','air_purifier','heater','humidifier','dehumidifier','power_bank','water_bottle','cleaning','kitchen','textiles','sports','general')
def category_for(title,override='auto'):
 if override!='auto': return override
 title=(title or '').lower()
 if re.search(r'\bfan\b',title): return 'fan'
 for category,words in [('air_purifier',('air purifier',)),('dehumidifier',('dehumidifier',)),('humidifier',('humidifier',)),('heater',('room heater','space heater')),('power_bank',('power bank','wireless charg','charging station')),('water_bottle',('water bottle','steel bottle','bottle 1 litre')),('cleaning',('toilet brush','cleaning brush','mop','scrubber')),('kitchen',('cookware','frying pan','cooking pot','food container','lunch box','coffee mug')),('textiles',('bedsheet','bed sheet','blanket','bath mat','towel')),('sports',('cricket bat','cricket ball','football','badminton','tennis racket')),('fan',('ceiling fan','table fan','pedestal fan','tower fan','desk fan'))]:
  if any(word in title for word in words): return category
 return 'general'
def fetch_weather(city):
 try:
  latitude,longitude=city.get('latitude'),city.get('longitude')
  if latitude is None or longitude is None:
   geo=requests.get('https://geocoding-api.open-meteo.com/v1/search',params=dict(name=city['name'],count=10,language='en',format='json'),timeout=15);geo.raise_for_status()
   location=next(value for value in geo.json().get('results',[]) if value.get('country_code')=='IN')
   latitude,longitude=location['latitude'],location['longitude']
  response=requests.get('https://api.open-meteo.com/v1/forecast',params=dict(latitude=latitude,longitude=longitude,current='temperature_2m,relative_humidity_2m,precipitation,weather_code',timezone='Asia/Kolkata'),timeout=15);response.raise_for_status();current=response.json()['current']
  return dict(status='available',temperature=current['temperature_2m'],humidity=current['relative_humidity_2m'],precipitation=current['precipitation'],time=current['time'],source='Open-Meteo weather model',url='https://open-meteo.com/en/docs')
 except (requests.RequestException,KeyError,ValueError,StopIteration): return dict(status='unavailable',source='Open-Meteo',reason='Weather could not be retrieved; no seasonal conclusion generated.')
def recommend(result,city,weather,origin,category_override='auto',analysis_context=None):
 category=category_for(result.get('title'),category_override);climate=city.get('climate','mild')
 general={'fan':('Good climate fit' if climate in ('hot','humid') else 'Selective fit','Fans suit warm conditions; verify price, competition and historical city sales before allocating stock.'),'air_purifier':('Evaluate air-quality demand','Check local measured AQI, room size and filter availability. Weather alone cannot establish air-purifier demand.'),'heater':('Good climate fit' if climate=='cool' else 'Season-dependent fit','Prioritize cool climates and winter periods; validate local household demand.'),'humidifier':('Evaluate indoor humidity','Recommend only where measured indoor humidity is low; outdoor humidity is an indirect proxy.'),'dehumidifier':('Potential climate fit' if climate=='humid' else 'Selective fit','Humid climates can support a use case; verify indoor humidity and demand.'),'power_bank':('Year-round use case','Travel and mobile charging are year-round uses; weather is not a reliable demand predictor.'),'water_bottle':('Year-round use case','Reusable bottles support daily hydration across cities. Match capacity, material and price to the local customer segment.'),'cleaning':('Year-round household use','Cleaning tools are household-use products across regions. Validate local competition, material durability and price.'),'kitchen':('Year-round household use','Kitchen products have household-use applications; evaluate household preferences, price and competition in this city.'),'textiles':('Match local use and material','Material and intended use matter more than a tier label. Validate fabric, season, care needs and local customer preferences.'),'sports':('Outdoor recreation use case','Validate local sports participation, competition and actual sales before allocating stock.'),'general':('Market validation needed','Use verified delivery reliability, local competition and historical sales to assess this city. A category-specific climate conclusion is unavailable.')}
 rating,reason=general[category];season='Weather unavailable';season_reason=weather.get('reason','');temp=weather.get('temperature');humidity=weather.get('humidity');rain=weather.get('precipitation')
 if weather['status']=='available':
  if category=='fan': season='Favourable now' if temp>=28 else 'Moderate fit now' if temp>=24 else 'Lower immediate need';season_reason=f'Destination temperature is {temp} °C. Heat increases the cooling use case; this is not a sales forecast.'
  elif category=='heater': season='Favourable now' if temp<=18 else 'Lower immediate need';season_reason=f'Destination temperature is {temp} °C; heating need is stronger in cool conditions.'
  elif category=='humidifier': season='Potential use case' if humidity<40 else 'No outdoor-humidity signal';season_reason=f'Outdoor humidity is {humidity}%; measure indoor conditions before deciding.'
  elif category=='dehumidifier': season='Potential use case' if humidity>=70 else 'No outdoor-humidity signal';season_reason=f'Outdoor humidity is {humidity}%; indoor humidity and dampness still need confirmation.'
  elif category=='air_purifier': season='AQI data needed';season_reason='Temperature and rain cannot substitute for measured AQI. No seasonal demand claim generated.'
  elif category=='water_bottle': season='Warm-weather use case' if temp>=28 else 'Year-round use case';season_reason=f'At {temp} °C, hydration remains relevant; warmer conditions strengthen the use case, not a quantified sales forecast.'
  elif category in ('cleaning','kitchen'): season='Year-round use case';season_reason='No direct weather-to-demand rule is assumed for this household category.'
  elif category=='sports': season='Rain data needed' if rain is None else 'Outdoor conditions suitable' if temp<32 and rain<1 else 'Outdoor conditions less suitable';season_reason=f'Temperature {temp} °C; precipitation '+('unavailable' if rain is None else str(rain)+' mm')+'. Comfortable dry conditions can support outdoor use; heat/rain can limit use. This does not establish sports-product sales.'
  elif category=='textiles': season='Material details needed';season_reason=f'Temperature is {temp} °C and humidity {humidity}%. Fabric and intended use are needed for a seasonal conclusion.'
  elif category=='power_bank': season='Weather-neutral';season_reason='No established direct temperature-to-demand rule is used for charging products.'
  else: season='No category-specific rule';season_reason='Product-specific seasonal fit cannot be established from the available title/category; no weather-based demand claim generated.'
 priority='Not ranked';sell_advice='No weather-based decision available'
 if weather['status']=='available':
  if category=='fan': priority='High' if temp>=28 else 'Medium' if temp>=24 else 'Low';sell_advice='Prioritize a limited fan stock test' if priority=='High' else 'Maintain selective fan stock' if priority=='Medium' else 'Avoid expanding fan stock on weather alone'
  elif category=='heater': priority='High' if temp<=18 else 'Low';sell_advice='Prioritize a limited heater stock test' if priority=='High' else 'Avoid expanding heater stock on weather alone'
  elif category=='dehumidifier': priority='Medium' if humidity>=70 else 'Low';sell_advice='Check indoor humidity before stocking'
  elif category=='humidifier': priority='Medium' if humidity<40 else 'Low';sell_advice='Check indoor humidity before stocking'
  elif category=='sports': priority='Not ranked' if rain is None else 'Medium' if temp<32 and rain<1 else 'Low';sell_advice='Test limited stock against local sports demand; use cooler/dry playing conditions'
  elif category=='water_bottle': priority='Medium' if temp>=28 else 'Low';sell_advice='Consider hydration use case; validate demand with sales'
  else: sell_advice='Weather alone cannot rank this product'
 context=analysis_context or {};source_weather=context.get('source_weather',{});source_temp=source_weather.get('temperature');comparison='Source weather unavailable; priority uses destination weather only.'
 if source_temp is not None and temp is not None:
  difference=round(temp-source_temp,1)
  comparison=f"{city['name']} is {abs(difference)} °C {'warmer' if difference>=0 else 'cooler'} than {context.get('source_location',origin)} (source {source_temp} °C; destination {temp} °C)."
  if category=='fan': comparison+=' Warmer destination can strengthen cooling need, but it does not establish higher fan sales.'
 rating='Sales unavailable';reason='City-wise ASIN sales have not been supplied. Actual sales level and sales priority cannot be determined; use weather priority only as a product-use signal.'
 now=datetime.now(ZoneInfo('Asia/Kolkata'))
 return dict(asin=result['asin'],title=result.get('title'),category=category,origin=origin,city=city['name'],pincode=city['pincode'],region=city['region'],tier=city['tier'],analysis_date=context.get('analysis_date',now.date().isoformat()),month=context.get('month',now.strftime('%B')),source_location=context.get('source_location',origin),source_temperature=source_temp,source_weather_time=source_weather.get('time'),weather_priority=priority,sell_advice=sell_advice,source_comparison=comparison,sales_status='Unavailable',sales_priority='Not ranked',general_rating=rating,general_reason=reason,seasonal_rating=season,seasonal_reason=season_reason,temperature=temp,humidity=humidity,precipitation=rain,weather_time=weather.get('time'),weather_source=weather['source'],weather_url=weather.get('url'),basis='Rule-based product/climate fit; not a sales or demand forecast',delivery_note='Destination-pincode promise only; source location is analysis context, not Amazon dispatch origin.')
