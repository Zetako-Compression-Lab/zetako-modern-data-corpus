"""Read-only descriptive audit; no compressor imports or calls."""
from pathlib import Path
from collections import Counter
import json,math
ROOT=Path(__file__).resolve().parents[1];data=ROOT/'outputs/ZMDC-1G-v1'
endpoints=Counter();users=Counter();hours=Counter();statuses=Counter();n=0
for line in (data/'api/events.jsonl').open('rb'):
    r=json.loads(line)
    if r['is_duplicate']:continue
    n+=1;endpoints[r['endpoint']]+=1;users[r['user_id']]+=1;statuses[r['status_code']]+=1
    hours[str((r['observed_timestamp_ms']//3600000)%24)]+=1
pairs={'temperature_fan':[0,0.,0.,0.,0.,0.],'current_power':[0,0.,0.,0.,0.,0.],'request_rate_cpu':[0,0.,0.,0.,0.,0.]}
def add(name,x,y):
    p=pairs[name];p[0]+=1;p[1]+=x;p[2]+=y;p[3]+=x*x;p[4]+=y*y;p[5]+=x*y
firmware=Counter();states=Counter()
for line in (data/'telemetry/telemetry.jsonl').open('rb'):
    r=json.loads(line)
    if r['is_duplicate']:continue
    add('temperature_fan',r['temperature'],r['fan_rpm']);add('current_power',r['current'],r['power']);firmware[r['firmware_version']]+=1;states[r['operating_state']]+=1
for line in (data/'observability/metrics.jsonl').open('rb'):
    r=json.loads(line)
    if not r['is_duplicate']:add('request_rate_cpu',r['request_rate'],r['cpu_percent'])
correlation={}
for k,(count,sx,sy,sxx,syy,sxy) in pairs.items():
    denominator=math.sqrt((count*sxx-sx*sx)*(count*syy-sy*sy));correlation[k]={'pairs':count,'pearson_r':(count*sxy-sx*sy)/denominator if denominator else None}
result={'api_unique_records':n,'endpoint_counts':dict(endpoints),'endpoint_shares':{k:v/n for k,v in endpoints.items()},'active_users':len(users),'top_100_user_share':sum(v for _,v in users.most_common(100))/n,'observation_hour_utc_counts':dict(hours),'status_counts':dict(statuses),'firmware_counts':dict(firmware),'device_state_counts':dict(states),'correlations':correlation,'interpretation':'Descriptive synthetic mechanisms, not external calibration or proof of representativeness.'}
(ROOT/'reports/plausibility-1GB.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2))
