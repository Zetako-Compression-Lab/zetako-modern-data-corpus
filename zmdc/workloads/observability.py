import copy
from ..world import SERVICES

class Observability:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);base=w.common('observability',i,'span',progress,r,a)
        trace=w.uid('observed-trace',i,32);root=w.uid('span',f'{i}/0',16)
        services=['gateway',a['service'],'database']
        if a['endpoint']=='/api/files' or r.random()<.15:services.append('storage')
        if 'retry' in base['quality']:services.append(a['service'])
        total=round(a['latency_ms']*(.9+r.random()*.2),3);out=[]
        for j,service in enumerate(services):
            x=copy.deepcopy(base);x['record_id']=w.uid('span-record',f'{i}/{j}');x['event_id']=x['record_id']
            x.update(trace_id=trace,span_id=w.uid('span',f'{i}/{j}',16),parent_span_id=None if j==0 else root if j==1 else w.uid('span',f'{i}/1',16),
                     span_service=service,operation='HTTP '+a['endpoint'] if j==0 else service+'.execute',
                     duration_ms=total if j==0 else round(total*.85,3) if j==1 else round(total*(.1+r.random()*.25),3),status='ERROR' if a['status_code']>=500 and j<3 else 'OK',
                     resource={'host':f'node-{base["instance_id"]:03d}','container':w.uid('container',f'{service}/{base["instance_id"]}'),'datacenter':base['region']+f'-dc{base["instance_id"]%3}',
                               'version':'2.0' if base['schema_version']=='2.0' else '1.8'},
                     attributes={'attempt':2 if j==4 else 1,'db_system':'postgresql' if service=='database' else None,'retry':j==4})
            x['span_start_ns']=base['timestamp_ms']*1_000_000+int(total*(0 if j==0 else .03 if j==1 else .08)*1_000_000)
            x['span_end_ns']=x['span_start_ns']+int(x['duration_ms']*1_000_000)
            out.append(('observability/traces.jsonl',x))
        metric=copy.deepcopy(base);metric.update(record_id=w.uid('metric',i),kind='metric',metric_name='service.resource.snapshot',
                trace_id=trace,cpu_percent=round(min(100,12+27*a['load_index']+r.random()*5),3),
                queue_depth=max(0,int(a['load_index']*12+r.gauss(0,2))),request_latency_ms=a['latency_ms'],request_rate=round(100*a['load_index'],3))
        out.append(('observability/metrics.jsonl',metric))
        log=copy.deepcopy(base);log.update(record_id=w.uid('otel-log',i),kind='otel_log',trace_id=trace,span_id=root,
             severity='ERROR' if a['status_code']>=500 else 'INFO',body='request completed' if a['status_code']<400 else 'request completed with partial backend failure',attributes={'http_status':a['status_code'],'request_id':a['request_id']})
        out.append(('observability/logs.jsonl',log));return out
