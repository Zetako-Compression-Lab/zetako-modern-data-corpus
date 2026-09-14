class Logs:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);x=w.common('logs',i,'log',progress,r,a)
        category=r.choices(['application','system','audit','container','network','security'],[45,15,15,10,10,5])[0]
        if a['endpoint']=='/api/auth' and a['status_code'] in (401,403):category='security'
        failed=a['status_code']>=400
        messages=['worker reconciled pending tasks','file upload completed','database checkpoint finished','replica connection recovered','workspace permissions refreshed','request scheduled for retry','container health probe returned an unexpected status']
        text=r.choice(messages)+f"; resource=/org/{x['organization_id']}/items/{i%4096}; correlation={a['request_id']}"
        if category=='security':text=f"authentication {'failed' if failed else 'succeeded'} for synthetic user {x['user_id']}"
        if r.random()<.06:text+='\nTraceback (synthetic):\n  at worker.dispatch(worker.py:128)\n  at storage.fetch(storage.py:64)\nTimeoutError: upstream deadline exceeded'
        if r.random()<.25:text+='; '+r.choice(['the queued operation was deferred until the next lease window','a peer reported a stale revision while applying the update','the background task completed after two incremental batches'])
        x.update(log_category=category,severity='ERROR' if failed else r.choices(['INFO','DEBUG','WARN'],[80,15,5])[0],
                 message=text,pid=1000+x['instance_id'],source_ip=f"192.0.2.{x['user_id']%254+1}",destination_ip=f"198.51.100.{x['instance_id']%254+1}",
                 status_code=a['status_code'],path=f"/var/lib/service-{x['instance_id']}/segments/{i%1024:04d}",request_id=a['request_id'])
        path='logs/audit.jsonl' if category in ('audit','security') else 'logs/system.log' if category in ('system','container','network') else 'logs/application.log'
        return [(path,x)]
