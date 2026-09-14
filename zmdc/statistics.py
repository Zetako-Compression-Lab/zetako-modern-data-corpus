from collections import Counter
import math
DIMENSIONS=['kind','schema_version','user_id','organization_id','device_id','service','region','status_code','event_type','operation','firmware_version','severity']
NUMERIC=['latency_ms','duration_ms','temperature','humidity','amount_minor','cpu_percent','power','risk_score']
class Stats:
    def __init__(self):
        self.n=0;self.sizes=[];self.minimum=None;self.maximum=0;self.total=0
        self.fields={k:set() for k in DIMENSIONS};self.proportions={k:Counter() for k in ['kind','schema_version','event_type','operation','status_code']}
        self.quality=Counter();self.numeric={};self.null_fields=Counter();self.present_fields=Counter();self.duplicates=0;self.out_of_order=0;self.last_event={}
        self.sensor={};self.delta_sum=0.;self.delta_max=0.;self.delta_n=0;self.max_observed=None;self.min_observed=None
    def add(self,record,size,path):
        self.n+=1;self.total+=size;self.minimum=size if self.minimum is None else min(size,self.minimum);self.maximum=max(size,self.maximum)
        for k,values in self.fields.items():
            if k in record and record[k] is not None:values.add(record[k])
        for k,counts in self.proportions.items():
            if k in record:counts[str(record[k])]+=1
        self.quality.update(record['quality']);self.duplicates+=record['is_duplicate']
        for k,v in record.items():
            self.present_fields[k]+=1
            if v is None:self.null_fields[k]+=1
        ts=record['timestamp_ms'];last=self.last_event.get(path)
        if last is not None and ts<last:self.out_of_order+=1
        self.last_event[path]=ts;obs=record['observed_timestamp_ms']
        self.min_observed=obs if self.min_observed is None else min(self.min_observed,obs);self.max_observed=obs if self.max_observed is None else max(self.max_observed,obs)
        for k in NUMERIC:
            v=record.get(k)
            if isinstance(v,(int,float)) and not isinstance(v,bool):
                d=self.numeric.setdefault(k,{'count':0,'sum':0.,'min':v,'max':v});d['count']+=1;d['sum']+=v;d['min']=min(d['min'],v);d['max']=max(d['max'],v)
        if 'temperature' in record and not record['is_duplicate']:
            device=record['device_id'];temp=record['temperature']
            if device in self.sensor:
                delta=abs(temp-self.sensor[device]);self.delta_n+=1;self.delta_sum+=delta;self.delta_max=max(self.delta_max,delta)
            self.sensor[device]=temp
    def result(self,unique):
        return {'records':self.n,'unique_record_ids':unique,'cardinality':{k:len(v) for k,v in self.fields.items()},
                'proportions':{k:dict(sorted(c.items())) for k,c in self.proportions.items()},
                'numeric':{k:{'count':v['count'],'mean':v['sum']/v['count'],'min':v['min'],'max':v['max']} for k,v in self.numeric.items()},
                'quality_counts':dict(self.quality),'quality_rates':{k:v/self.n for k,v in self.quality.items()} if self.n else {},
                'null_rates':{k:v/self.present_fields[k] for k,v in self.null_fields.items()},
                'missing_metadata_rate':1-self.present_fields['metadata']/self.n if self.n else 0,
                'duplicate_rate':self.duplicates/self.n if self.n else 0,'out_of_order_event_rate':self.out_of_order/self.n if self.n else 0,
                'record_size_bytes':{'min':self.minimum,'max':self.maximum,'mean':self.total/self.n if self.n else 0},
                'observed_time_range_ms':[self.min_observed,self.max_observed],
                'telemetry_continuity':{'consecutive_device_pairs':self.delta_n,'mean_absolute_temperature_step':self.delta_sum/self.delta_n if self.delta_n else None,'max_absolute_temperature_step':self.delta_max}}

def byte_entropy(counts):
    total=sum(counts.values())
    return -sum((v/total)*math.log2(v/total) for v in counts.values()) if total else 0.
