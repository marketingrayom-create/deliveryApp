import re,html,time
from pathlib import Path
from datetime import date,timedelta
from zoneinfo import ZoneInfo
from datetime import datetime
from urllib.parse import urlparse

def parse_purchase_badge(text):
 text=re.sub(r'\s+',' ',text or '').strip()
 match=re.search(r'(?<![\w.])(\d[\d,]*(?:\.\d+)?\s*[KkMm]?\+?)\s*bought\s+in\s+(?:the\s+)?past\s+month',text or '',re.I)
 if not match: return None,None
 raw=match.group(1).replace(' ','');amount=raw.rstrip('+');factor=1000 if amount[-1:].lower()=='k' else 1000000 if amount[-1:].lower()=='m' else 1
 numeric=amount[:-1] if factor!=1 else amount
 return raw+' bought in past month',int(float(numeric.replace(',',''))*factor)

def read_purchase_badge(page):
 # Inspect every primary-product badge; do not scan recommended products.
 matches=page.locator('#social-proofing-faceout, #social-proofing-faceout_feature_div, #socialProofingAsinFaceout_feature_div, .social-proofing-faceout, #title_feature_div [id*="social-proof"]')
 for index in range(min(matches.count(),20)):
  element=matches.nth(index)
  try:
   if element.is_visible():
    badge,count=parse_purchase_badge(element.inner_text(timeout=3000))
    if badge: return badge,count
  except Exception:
   continue
 # Amazon also renders the badge in ordinary spans without stable social-proof IDs.
 # Restrict fallback to visible text immediately below the main product title.
 title=page.locator('#productTitle:visible').first
 try: title_box=title.bounding_box()
 except Exception: title_box=None
 if isinstance(title_box,dict):
  matches=page.locator('#centerCol, #titleBlock').get_by_text(re.compile(r'\d[\d,.]*\s*[KkMm]?\+?\s*bought\s+in\s+(?:the\s+)?past\s+month',re.I))
  for index in range(min(matches.count(),20)):
   element=matches.nth(index)
   try:
    box=element.bounding_box()
    if box and element.is_visible() and title_box['y']<=box['y']<=title_box['y']+title_box['height']+400:
     badge,count=parse_purchase_badge(element.inner_text(timeout=3000))
     if badge: return badge,count
   except Exception:
    continue
 return None,None

def parse_delivery_date(text,base=None):
 base=base or datetime.now(ZoneInfo('Asia/Kolkata')).date();text=(text or '').lower()
 if re.search(r'\btoday\b',text): return base.isoformat(),0
 if re.search(r'\btomorrow\b',text): return (base+timedelta(days=1)).isoformat(),1
 months={name:i for i,names in enumerate([('jan','january'),('feb','february'),('mar','march'),('apr','april'),('may',),('jun','june'),('jul','july'),('aug','august'),('sep','sept','september'),('oct','october'),('nov','november'),('dec','december')],1) for name in names}
 match=re.search(r'(\d{1,2})\s+([a-z]+)',text)
 if not match: return None,None
 try:
  day,month=int(match[1]),months[match[2]];target=date(base.year,month,day)
  if target<base and (base-target).days>180: target=date(base.year+1,month,day)
  if target<base: return None,None
  return target.isoformat(),(target-base).days
 except (KeyError,ValueError): return None,None

def wait_for_verification(page,cancel,interactive):
 deadline=time.monotonic()+(120 if interactive else 0)
 while True:
  text=stable_content(page,cancel)
  blocked='validateCaptcha' in text or 'Robot Check' in text or 'captcha' in page.url.lower()
  if not blocked: return
  if cancel.is_set() or time.monotonic()>=deadline: raise RuntimeError('Amazon verification required. Retry with Show Amazon browser enabled and complete verification on the server computer.')
  page.wait_for_timeout(1500)

def stable_content(page,cancel=None):
 # Amazon can replace the document after DOMContentLoaded or a location update.
 for attempt in range(4):
  if cancel is not None and cancel.is_set(): raise RuntimeError('Check cancelled')
  try: return page.content()
  except Exception as exc:
   if 'navigating' not in str(exc).lower() and 'execution context was destroyed' not in str(exc).lower(): raise
   if attempt==3: raise RuntimeError('Amazon page did not settle after navigation. Please retry this city.') from exc
   try: page.wait_for_load_state('domcontentloaded',timeout=10000)
   except Exception: pass
   page.wait_for_timeout(400)

def read_price(page):
 # Limit extraction to the buy-box price, excluding crossed-out MRP and EMI.
 for selector in ('#corePriceDisplay_desktop_feature_div .apex-pricetopay-value', '#apex_price .apex-pricetopay-value', '#corePriceDisplay_desktop_feature_div .priceToPay', '#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price)', '#corePrice_feature_div .a-price:not(.a-text-price)', '#apex_desktop .a-price:not(.a-text-price)', '#buybox .a-price:not(.a-text-price)'):
  matches=page.locator(selector)
  for index in range(min(matches.count(),10)):
   element=matches.nth(index)
   if not element.is_visible(): continue
   offscreen=element.locator('.a-offscreen').first
   text=offscreen.text_content() if offscreen.count() else element.inner_text()
   if not re.search(r'\d',text or ''): text=element.inner_text()
   match=re.search(r'(?:₹|Rs\.?\s*)?\s*(\d[\d,]*(?:\.\d{1,2})?)',text or '')
   if match: return float(match.group(1).replace(',',''))
 for selector in ('#priceblock_ourprice','#priceblock_dealprice','#price_inside_buybox'):
  text=visible_text(page,selector)
  match=re.search(r'\d[\d,]*(?:\.\d{1,2})?',text or '')
  if match: return float(match.group().replace(',',''))
 return None

def visible_text(page,selector,required=False):
 matches=page.locator(selector)
 for index in range(min(matches.count(),10)):
  element=matches.nth(index)
  try:
   if element.is_visible():
    text=element.inner_text(timeout=3000).strip()
    if text: return text
  except Exception:
   continue
 if required: raise RuntimeError('Amazon page did not provide a readable '+selector+' element.')
 return None

def same_page(requested,actual):
 left,right=urlparse(requested),urlparse(actual)
 return right.scheme=='https' and right.hostname in ('www.amazon.in','amazon.in') and left.path.rstrip('/')==right.path.rstrip('/')

def navigate(page,url):
 responses=[]
 def record(response):
  if response.request.is_navigation_request() and response.frame==page.main_frame: responses.append(response)
 page.on('response',record)
 try:
  try: response=page.goto(url,wait_until='domcontentloaded',timeout=45000)
  except Exception as exc:
   if 'net::ERR_ABORTED' not in str(exc): raise
   page.wait_for_load_state('domcontentloaded',timeout=15000)
   matches=[response for response in responses if same_page(url,response.url)]
   if not same_page(url,page.url) or not matches: raise RuntimeError('Amazon navigation was interrupted. No delivery data accepted; retry manually.')
   response=matches[-1]
  if not same_page(url,page.url): raise RuntimeError('Amazon navigated to an unexpected page. No delivery data accepted.')
  if response and response.status in (403,429,503): raise RuntimeError('Amazon verification or request limit detected. Stop and check the visible browser before retrying.')
  return response
 finally: page.remove_listener('response',record)

def location_text(page):
 return visible_text(page,'#nav-global-location-popover-link') or visible_text(page,'#glow-ingress-block') or visible_text(page,'#glow-ingress-line2')

def set_pincode(page,city):
 location=location_text(page)
 if location and city['pincode'] in location: return
 selector='#GLUXZipUpdateInput:visible, input[name="zipCode"]:visible, input[name="zip-code"]:visible'
 postal=page.locator(selector).first
 # Navigation can finish before Amazon attaches the popover click handlers.
 # One normal page reload is allowed for a failed UI initialization.
 for attempt in range(2):
  if attempt:
   navigate(page,page.url)
  page.wait_for_timeout(1800)
  content=stable_content(page)
  if 'validateCaptcha' in content or 'Robot Check' in content or 'captcha' in page.url.lower():
   raise RuntimeError('Amazon verification required. Complete verification in the visible browser before retrying.')
  if not postal.is_visible():
   trigger=page.locator('#nav-global-location-popover-link:visible, #glow-ingress-block:visible').first
   trigger.wait_for(state='visible',timeout=15000)
   trigger.click()
  try:
   postal.wait_for(state='visible',timeout=12000)
   break
  except Exception:
   if attempt==1:
    raise RuntimeError('Amazon location dialog could not load after one retry. Check the visible browser for verification or connection problems; no delivery data accepted.') from None
 postal.fill(city['pincode']);page.locator('#GLUXZipUpdate:visible').first.click()
 page.wait_for_timeout(500)
 # Some Amazon layouts require Continue/Done before the header is updated.
 confirm=page.locator('#GLUXConfirmClose:visible, #GLUXConfirmClose-announce:visible, #GLUXConfirmClose input:visible, button[name="glowDoneButton"]:visible').first
 if confirm.count() and confirm.is_visible(): confirm.click()
 try:
  page.wait_for_function("pin=>Array.from(document.querySelectorAll('#nav-global-location-popover-link, #glow-ingress-block, #glow-ingress-line2')).some(el=>el.getClientRects().length>0&&getComputedStyle(el).visibility!=='hidden'&&new RegExp('(^|\\\\D)'+pin+'(\\\\D|$)').test(el.innerText))",arg=city['pincode'],timeout=20000)
 except Exception as exc:
  actual=location_text(page) or ''
  if not re.search(r'(?<!\d)'+re.escape(city['pincode'])+r'(?!\d)',actual):
   raise RuntimeError('Amazon did not confirm pincode '+city['pincode']+'. Complete the location dialog in the visible browser and retry this city. No delivery data accepted.') from exc
 page.keyboard.press('Escape')
 stable_content(page)

def check_city(asins,city,cancel,on_result,show_browser=True):
 from playwright.sync_api import sync_playwright
 with sync_playwright() as engine:
  profile=__import__('runtime_paths').DATA_ROOT/'data'/'browser-profiles'/'msedge'/city['id'];profile.mkdir(parents=True,exist_ok=True)
  context=engine.chromium.launch_persistent_context(str(profile),channel='msedge',headless=not show_browser,locale='en-IN',timezone_id='Asia/Kolkata',viewport={'width':1280,'height':900})
  page=context.pages[0] if context.pages else context.new_page();page.set_default_timeout(12000)
  completed=set()
  def base(product):
   return dict(asin=product['asin'],brand=product.get('brand',''),title=None,city=city['name'],pincode=city['pincode'],region=city['region'],tier=city['tier'],status='Error',delivery_date=None,delivery_days=None,price=None,location_verified=False,checked_at=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),source_url='https://www.amazon.in/dp/'+product['asin'])
  try:
   navigate(page,'https://www.amazon.in/');wait_for_verification(page,cancel,show_browser);set_pincode(page,city)
   for product in asins:
    if cancel.is_set(): break
    result=base(product)
    try:
     page.wait_for_timeout(2000);response=navigate(page,result['source_url']);page.wait_for_timeout(900);wait_for_verification(page,cancel,show_browser)
     if response and response.status==404: raise RuntimeError('Product page not found')
     location=location_text(page)
     if not location: raise RuntimeError('Amazon did not provide a readable delivery location')
     if city['pincode'] not in location: raise RuntimeError('Amazon did not confirm the selected pincode; delivery not inferred')
     result['location_verified']=True;result['title']=visible_text(page,'#productTitle')
     result['purchase_badge'],result['purchase_count_floor']=read_purchase_badge(page)
     byline=visible_text(page,'#bylineInfo')
     if byline: result['brand']=re.sub(r'^(Visit the |Brand: )| Store$','',byline,flags=re.I)
     availability=visible_text(page,'#availability') or ''
     result['price']=read_price(page)
     for price_attempt in range(6):
      if result['price'] is not None or 'currently unavailable' in availability.lower() or cancel.is_set(): break
      page.wait_for_timeout(500)
      result['price']=read_price(page)
     text=visible_text(page,'#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE') or visible_text(page,'#mir-layout-DELIVERY_BLOCK') or ''
     result['delivery_text']=text
     if 'currently unavailable' in availability.lower(): result['status']='Out of stock'
     elif any(word in text.lower() for word in ('cannot be shipped','not deliverable','not available to')): result['status']='Not deliverable'
     else:
      result['delivery_date'],result['delivery_days']=parse_delivery_date(text)
      result['status']='Available' if result['delivery_date'] else 'Delivery promise unavailable'
    except Exception as exc:
     result['error']=str(exc).split('Call log:')[0][:240]
     if 'verification' in str(exc).lower() or 'request limit' in str(exc).lower(): result['status']='Verification needed'
    on_result(result);completed.add(product['asin'])
  except Exception as exc:
   for product in asins:
    if cancel.is_set(): break
    if product['asin'] in completed: continue
    result=base(product);result['status']='Verification needed' if 'verification' in str(exc).lower() else 'Error';result['error']=str(exc).split('Call log:')[0][:240];on_result(result)
  finally: context.close()
