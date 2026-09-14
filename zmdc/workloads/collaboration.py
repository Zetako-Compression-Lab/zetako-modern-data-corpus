class Collaboration:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);x=w.common('collaboration',i,'collaboration',progress,r,a)
        event=r.choices(['message','reaction','presence','notification','file_metadata','meeting','channel','access'],[38,15,12,12,10,6,4,3])[0]
        subjects=['The deployment','Our review','The storage migration','This draft','The support ticket','The next release','The schedule','The background job']
        actions=['needs another check','is ready for review','has moved to the next stage','will run after the backup','is waiting for confirmation','now includes the latest changes','can proceed this afternoon']
        clauses=['Please review the attached notes.','I will post a summary after the checks.','The owner has been notified.','We can discuss the remaining questions tomorrow.','No additional input is needed yet.']
        text=r.choice(subjects)+' '+r.choice(actions)+'. '+r.choice(clauses)
        if r.random()<.45:text+=' '+r.choice(subjects).lower()+' '+r.choice(actions)+f' (item {i%10000}).'
        x.update(event_type=event,message_id=w.uid('message',i),workspace_id=x['organization_id'],channel_id=x['organization_id']*100+i%17,
                 text=text if event in ('message','notification') else None,mentions=[r.randrange(1,w.config.users+1) for _ in range(r.choices([0,1,2,3],[65,25,8,2])[0])],
                 reaction=r.choice(['ack','thanks','review','question']) if event=='reaction' else None,
                 file={'name':f'project-{i%719}-revision-{i%9}.dat','bytes':int(r.lognormvariate(10,2)),'content_hash':w.uid('content',i,64)} if event=='file_metadata' else None,
                 presence=r.choice(['available','busy','away','offline']),meeting_duration_minutes=r.choice([15,25,30,45,60]) if event=='meeting' else None)
        return [('collaboration/events.jsonl',x)]
