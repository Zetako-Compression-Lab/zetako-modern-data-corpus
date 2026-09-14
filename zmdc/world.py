from collections import deque
import math,json
from .config import START_MS,DAY_MS
from .rng import identifier

REGIONS=['us-east','us-west','eu-west','eu-central','ap-south','ap-east','ap-southeast','sa-east']
OFFSETS=[-5,-8,0,1,5.5,9,8,-3]
SERVICES=['gateway','auth','messages','files','workspaces','search','users','notifications','billing','payments','database','storage','metrics','scheduler','presence','meetings','audit','devices','edge','security']
ENDPOINTS=['/api/messages','/api/files','/api/auth','/api/workspaces','/api/search','/api/users','/api/notifications','/api/transactions','/api/devices']
ENDPOINT_SERVICE=[2,3,1,4,5,6,7,9,17]
ENDPOINT_WEIGHTS=[30,21,15,11,8,6,4,3,2]
# Quantile/time knots: more observations per hour during working hours.
TIME_KNOTS=[(0,0),(.08,6),(.20,9),(.55,15),(.80,19),(1,24)]

def clock(progress,days=30):
    phase=min(max(progress,0),.999999999)*days;day=int(phase);q=phase-day
    for (q0,h0),(q1,h1) in zip(TIME_KNOTS,TIME_KNOTS[1:]):
        if q<=q1:
            hour=h0+(q-q0)/(q1-q0)*(h1-h0);break
    return START_MS+int((day*24+hour)*3600000)

def day_of(ts):return max(1,min(30,(ts-START_MS)//DAY_MS+1))

def schema(ts,instance):
    day=day_of(ts)
    if day<8:return '1.0'
    if day<15:return '1.1'
    if day<20:return '1.2'
    if day<24:return '1.3'
    if day<27 or instance%10==0:return '1.4'
    return '2.0'

class World:
    def __init__(self,config):self.config=config
    def uid(self,namespace,value,length=24):return identifier(self.config.seed,namespace,value,length)
    def organization(self,user):return (user-1)%self.config.organizations+1
    def heavy_user(self,rng):
        # Heavy head plus a uniform long tail; bounded Pareto, not uniform IDs.
        if rng.random()<.20:return rng.randrange(1,self.config.users+1)
        return min(self.config.users,max(1,int((rng.paretovariate(1.15)-1)*120)+1))
    def instance(self,service,index=0,region=None):
        s=SERVICES.index(service);choices=list(range(s+1,self.config.instances+1,len(SERVICES)))
        if region is not None:choices=[v for v in choices if REGIONS[((v-1)//20)%8]==region]
        return choices[index%len(choices)]
    def load(self,ts,region):
        day=day_of(ts);hour=((ts-START_MS)/3600000+OFFSETS[REGIONS.index(region)])%24
        daily=.18+.82*max(0,math.cos((hour-14)/24*2*math.pi))
        burst=2.6 if day in (6,12,19,25) and 10<=hour<13 else 1
        return daily*burst
    def common(self,family,i,kind,progress,rng,anchor=None,service_override=None):
        observed=clock(progress,self.config.days);quality=[k for k,p in sorted(self.config.rates.items()) if k!='duplicate' and rng.random()<p]
        lag=rng.randint(1000,900000) if 'delayed' in quality else rng.randint(0,80)
        drift=rng.randint(-1500,1500) if 'clock_drift' in quality else 0
        user=anchor['user_id'] if anchor else self.heavy_user(rng)
        service=anchor['service'] if anchor else service_override or rng.choice(SERVICES)
        region=anchor['region'] if anchor else rng.choices(REGIONS,weights=[.3+self.load(observed,r) for r in REGIONS])[0]
        instance=anchor['instance_id'] if anchor else self.instance(service,i,region)
        record={'record_id':self.uid(family,i),'event_id':self.uid(family+'/event',i),'kind':kind,
                'timestamp_ms':observed-lag+drift,'observed_timestamp_ms':observed,'clock_drift_ms':drift,'delivery_delay_ms':lag,
                'schema_version':schema(observed,instance),'user_id':user,'organization_id':self.organization(user),
                'service':service,'instance_id':instance,'region':region,'quality':quality,'is_duplicate':False,
                'metadata':{'tenant_tier':['free','team','enterprise'][user%3],'environment':'production','sampling_weight':1}}
        if anchor:record.update(api_request_id=anchor['request_id'],linked_trace_id=anchor['trace_id'])
        if 'missing' in quality:record.pop('metadata')
        if 'null' in quality:record['optional_context']=None
        else:record['optional_context']={'zone':f'{region}-{instance%3+1}'}
        if 'unexpected_enum' in quality:record['processing_class']='experimental_unknown'
        day=day_of(observed)
        if day>=8:record['deployment_context']={'release':f'2026.01.{1+(day//7)}','canary':instance%11==0}
        if day<24:record['legacy_collector']='collector-v1'
        elif day<27 and instance%4==0:record['legacy_collector']='collector-v1'
        return record

class Anchors:
    """Sequential API cursor, 128 recent records; no corpus-sized in-memory index."""
    def __init__(self,path):
        self.fp=open(path,'rb');self.recent=deque(maxlen=128);self.next=self._read()
    def _read(self):
        for line in self.fp:
            r=json.loads(line)
            if not r['is_duplicate']:return r
        return None
    def at(self,progress,rng):
        ts=clock(progress)
        while self.next is not None and (not self.recent or self.next['observed_timestamp_ms']<=ts):
            self.recent.append(self.next);self.next=self._read()
        return self.recent[rng.randrange(len(self.recent))]
    def close(self):self.fp.close()
