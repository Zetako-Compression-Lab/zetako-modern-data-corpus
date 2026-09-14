from ..world import ENDPOINTS,ENDPOINT_SERVICE,ENDPOINT_WEIGHTS,SERVICES,day_of

class API:
    def __init__(self,world,rng,anchors=None):self.w=world;self.r=rng
    def make(self,i,progress):
        w,r=self.w,self.r
        e=r.choices(range(len(ENDPOINTS)),weights=ENDPOINT_WEIGHTS)[0];service=SERVICES[ENDPOINT_SERVICE[e]]
        x=w.common('api',i,'api_request',progress,r,service_override=service)
        load=w.load(x['observed_timestamp_ms'],x['region']);incident=day_of(x['observed_timestamp_ms'])==12 and service in ('files','auth','messages')
        retry='retry' in x['quality'];anomaly='anomaly' in x['quality']
        status=r.choices([200,201,204,400,401,403,404,429,500,503],[62,12,10,2,3,1,3,3,1+(8 if incident else 0),1+(10 if incident else 0)])[0]
        latency=r.lognormvariate(3.25,.65)*(1+.6*load)*(4 if status>=500 else 1)
        if anomaly:latency*=7
        client=r.choices(['web','ios','android','service'],[50,20,20,10])[0]
        if day_of(x['observed_timestamp_ms'])>=20 and r.random()<.08:client='edge_proxy'
        key='client_type' if day_of(x['observed_timestamp_ms'])<15 else 'client_family'
        x.update(request_id=w.uid('request',i,32),trace_id=w.uid('trace',i,32),
                 session_id=w.uid('session',f"{x['user_id']}/{day_of(x['observed_timestamp_ms'])}/{i%3}"),
                 endpoint=ENDPOINTS[e],method=r.choices(['GET','POST','PUT','DELETE'],[58,30,9,3])[0],
                 status_code=status,latency_ms=round(latency,3),api_version='v2' if x['schema_version']=='2.0' else 'v1',
                 payload_size=min(8_000_000,int(r.lognormvariate(6.2,1.7))),response_size=min(20_000_000,int(r.lognormvariate(7,1.7))),
                 authentication_method=r.choices(['session_cookie','oauth2','api_key','mTLS'],[55,30,12,3])[0],
                 error_type=None if status<400 else ('authentication_failed' if status in (401,403) else 'backend_timeout' if status>=500 else 'request_rejected'),
                 retry_attempt=r.randint(1,3) if retry else 0,load_index=round(load,4),
                 idempotency_key=w.uid('request-operation',f"{x['user_id']}/{i//3}"),**{key:client})
        return [('api/events.jsonl',x)]
