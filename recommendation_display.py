from datetime import date,datetime
from zoneinfo import ZoneInfo

def display_fields(row):
 try: entered=date.fromisoformat(row.get('analysis_date',''))
 except (ValueError,TypeError): entered=datetime.now(ZoneInfo('Asia/Kolkata')).date()
 previous=date(entered.year-(entered.month==1),(entered.month-2)%12+1,1)
 target=date(entered.year+(entered.month==12),entered.month%12+1,1)
 target_label=row.get('target_month') or target.strftime('%B %Y')
 city=row['city']
 general=f"{city} | {previous:%B %Y}: Past-month ASIN sales data unavailable. Sales-based recommendation and priority cannot be calculated."
 badge=row.get('purchase_badge')
 if badge:
  general=f"{city} | Amazon signal: {badge}. Recent product-level purchases support considering a limited stock test alongside price, margin and competition. This is an approximate marketplace-wide badge, not this city's sales; '+' is a lower-bound indication, not an exact count."
 else:
  general=f"{city} | Amazon past-month purchase badge unavailable. No recent-purchase recommendation inferred; city-specific sales are unavailable."
 if row.get('ai_general_reason'):
  purchase_signal=(f"Amazon signal: {badge}. Approximate product-level recent purchases, not this city's sales; '+' is a lower bound." if badge else 'Amazon past-month purchase badge unavailable; city-specific sales are unavailable.')
  general=f"{city} | {purchase_signal} {row['ai_general_reason']}"
 status=row.get('ai_status') or 'AI assessment was not recorded; run a new check'
 if status in ('Gemini complete', 'OpenAI complete', 'GroqCloud complete') and not row.get('ai_seasonal_reason'): status='No accepted AI assessment for this product/city; run a new check'
 assessment=row.get('ai_seasonal_reason') or ('Next-month seasonal assessment unavailable. Status: '+status+'.')
 seasonal=f"{city} | {target_label} | Seasonal fit: {row.get('seasonal_priority') or 'Not ranked'}. {assessment} Selling chance: Unavailable — a reliable percentage requires historical sales and a validated prediction model."
 if row.get('seasonal_suitability_score') is not None:
  seasonal=f"{city} | {target_label} | Priority: {row.get('seasonal_priority')} | AI seasonal suitability: {row['seasonal_suitability_score']}/100 (subjective fit score, not selling probability). {assessment}"
 return dict(general_recommendation=general,seasonal_recommendation=seasonal)
