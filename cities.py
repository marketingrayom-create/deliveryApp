import json
from pathlib import Path
from runtime_paths import DATA_ROOT
PATH=DATA_ROOT/'data'/'cities.json'
# Editable business shortlist. Tiers are market groupings, not RBI population tiers.
REGIONS={
'North':[('Delhi',1,'110001',28.61,77.21,'hot'),('Jaipur',2,'302001',26.91,75.79,'hot'),('Lucknow',2,'226001',26.85,80.95,'hot'),('Chandigarh',2,'160017',30.73,76.78,'hot'),('Gurugram',2,'122001',28.46,77.03,'hot'),('Noida',2,'201301',28.54,77.39,'hot'),('Amritsar',2,'143001',31.63,74.87,'hot'),('Dehradun',2,'248001',30.32,78.03,'mild'),('Shimla',3,'171001',31.10,77.17,'cool'),('Haridwar',3,'249401',29.95,78.16,'hot')],
'South':[('Bengaluru',1,'560001',12.97,77.59,'mild'),('Chennai',1,'600001',13.08,80.27,'humid'),('Hyderabad',1,'500001',17.39,78.49,'hot'),('Kochi',2,'682001',9.97,76.27,'humid'),('Coimbatore',2,'641001',11.02,76.96,'hot'),('Thiruvananthapuram',2,'695001',8.52,76.94,'humid'),('Mysuru',2,'570001',12.30,76.64,'mild'),('Madurai',2,'625001',9.93,78.12,'hot'),('Udupi',3,'576101',13.34,74.75,'humid'),('Ooty',3,'643001',11.41,76.70,'cool')],
'West':[('Mumbai',1,'400001',19.08,72.88,'humid'),('Pune',1,'411001',18.52,73.86,'mild'),('Ahmedabad',1,'380001',23.02,72.57,'hot'),('Surat',2,'395003',21.17,72.83,'humid'),('Vadodara',2,'390001',22.31,73.18,'hot'),('Nashik',2,'422001',20.00,73.79,'mild'),('Nagpur',2,'440001',21.15,79.09,'hot'),('Rajkot',2,'360001',22.30,70.80,'hot'),('Panaji',3,'403001',15.50,73.83,'humid'),('Ratnagiri',3,'415612',16.99,73.31,'humid')],
'East':[('Kolkata',1,'700001',22.57,88.36,'humid'),('Patna',2,'800001',25.61,85.14,'hot'),('Bhubaneswar',2,'751001',20.30,85.82,'humid'),('Ranchi',2,'834001',23.34,85.31,'mild'),('Jamshedpur',2,'831001',22.80,86.20,'hot'),('Siliguri',2,'734001',26.73,88.40,'humid'),('Cuttack',2,'753001',20.46,85.88,'humid'),('Durgapur',2,'713201',23.52,87.31,'hot'),('Puri',3,'752001',19.81,85.83,'humid'),('Darjeeling',3,'734101',27.04,88.26,'cool')],
'Central':[('Indore',2,'452001',22.72,75.86,'hot'),('Bhopal',2,'462001',23.26,77.41,'hot'),('Raipur',2,'492001',21.25,81.63,'hot'),('Gwalior',2,'474001',26.22,78.18,'hot'),('Jabalpur',2,'482001',23.18,79.99,'hot'),('Bilaspur',2,'495001',22.08,82.14,'hot'),('Ujjain',3,'456001',23.18,75.79,'hot'),('Sagar',3,'470001',23.84,78.74,'hot'),('Satna',3,'485001',24.58,80.83,'hot'),('Rewa',3,'486001',24.54,81.30,'hot')],
'North East':[('Guwahati',2,'781001',26.14,91.74,'humid'),('Shillong',2,'793001',25.58,91.89,'cool'),('Agartala',2,'799001',23.83,91.28,'humid'),('Imphal',2,'795001',24.82,93.94,'mild'),('Aizawl',2,'796001',23.73,92.72,'mild'),('Kohima',3,'797001',25.68,94.11,'cool'),('Gangtok',3,'737101',27.33,88.61,'cool'),('Itanagar',3,'791111',27.10,93.62,'humid'),('Dibrugarh',3,'786001',27.47,94.91,'humid'),('Silchar',3,'788001',24.83,92.78,'humid')]
}
def defaults():
 old={n:dict(latitude=lat,longitude=lon,climate=climate) for values in REGIONS.values() for n,t,p,lat,lon,climate in values}
 groups=json.loads((Path(__file__).parent/'regional_shortlist.json').read_text(encoding='utf-8'));output=[]
 for region,tiers in groups.items():
  for tier,values in enumerate(tiers,1):
   for rank,value in enumerate(values,1):
    name,pincode=value.rsplit(':',1);meta=old.get(name,dict(latitude=None,longitude=None,climate='mild'))
    output.append(dict(id=region.lower().replace(' ','-')+'-t'+str(tier)+'-'+str(rank),region=region,name=name,tier=tier,pincode=pincode,rank=rank,**meta,gdp=None,gdp_year=None,gdp_source=None,ranking_basis='User-supplied regional e-commerce market tiers; not an official classification',pincode_basis='Suggested representative PIN; verify exact delivery area'))
 return output

def load_cities():
 if not PATH.exists(): return defaults()
 values=json.loads(PATH.read_text(encoding='utf-8'))
 # Keep edited cities and add the new Tier 4 shortlist without duplicating pins.
 existing={city['pincode'] for city in values};ids={city['id'] for city in values}
 return values+[city for city in defaults() if city['tier']==4 and city['pincode'] not in existing and city['id'] not in ids]
def save_cities(values):
 import re
 if not isinstance(values,list) or not 1<=len(values)<=300: raise ValueError('Choose 1–300 cities.')
 ids=set();pins=set()
 for city in values:
  if not isinstance(city,dict) or not re.fullmatch(r'[a-z0-9-]{1,80}',str(city.get('id',''))) or city['id'] in ids: raise ValueError('City IDs must be unique.')
  ids.add(city['id'])
  if city.get('region') not in REGIONS or city.get('tier') not in (1,2,3,4): raise ValueError('Choose a valid region and tier.')
  if not 1<=len(str(city.get('name','')).strip())<=80 or not re.fullmatch(r'[1-9][0-9]{5}',str(city.get('pincode',''))): raise ValueError('Enter a city name and six-digit pincode.')
  if city['pincode'] in pins: raise ValueError('Each shortlisted city must have a distinct representative pincode.')
  pins.add(city['pincode'])
  if (city.get('latitude') is None)!=(city.get('longitude') is None): raise ValueError('Supply both weather coordinates or leave both blank.')
  if city.get('latitude') is not None and (not -90<=float(city['latitude'])<=90 or not -180<=float(city['longitude'])<=180): raise ValueError('Enter valid weather coordinates.')
  if city.get('climate') not in ('hot','humid','mild','cool'): raise ValueError('Choose a climate grouping.')
 PATH.parent.mkdir(exist_ok=True);temp=PATH.with_suffix('.tmp');temp.write_text(json.dumps(values,indent=2),encoding='utf-8');temp.replace(PATH)
