import copy
TABLES=['users','messages','files','sessions','devices','subscriptions']
class Database:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors;self.live={t:{} for t in TABLES}
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);x=w.common('database',i,'cdc',progress,r,a)
        table=r.choices(TABLES,[10,30,15,20,15,10])[0];live=self.live[table]
        op=r.choices(['INSERT','UPDATE','DELETE'],[75 if table=='messages' else 35,15 if table=='messages' else 55,10])[0]
        if not live:op='INSERT'
        if len(live)>=512:op='DELETE'
        if op=='INSERT':
            key=w.uid('db-key',f'{table}/{i}');before=None
            after={'owner_user_id':x['user_id'],'organization_id':x['organization_id'],'revision':1,'state':'active','value':r.randint(0,10000),'updated_at_ms':x['timestamp_ms']}
            if table=='devices':after['device_id']=r.randrange(1,w.config.devices+1)
            live[key]=after
        else:
            key=r.choice(tuple(live));before=copy.deepcopy(live[key])
            if op=='DELETE':after=None;del live[key]
            else:
                after={**before,'revision':before['revision']+1,'value':before['value']+r.randint(-10,20),'updated_at_ms':x['timestamp_ms']};live[key]=after
        x.update(table=table,primary_key=key,operation=op,before=before,after=after,transaction_id=w.uid('db-tx',i//3),sequence=i+1)
        return [('database/cdc.jsonl',x)]
