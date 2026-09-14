from collections import deque
class Transactions:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors;self.settled=deque(maxlen=1024)
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);x=w.common('transactions',i,'transaction',progress,r,a)
        refund=bool(self.settled) and r.random()<.035
        amount=min(5_000_000,max(1,int(r.lognormvariate(7.4,1.05))))
        fraud='anomaly' in x['quality'];amount*=10 if fraud else 1
        currency=r.choices(['USD','EUR','GBP','JPY','SGD'],[48,28,10,8,6])[0];account=x['organization_id']
        original=None
        recurring=i%5==0 and not refund
        if recurring:
            amount=[990,1990,4900,9900][x['user_id']%4];currency='USD'
        if refund:
            charge=r.choice(self.settled);amount=-max(1,int(charge['amount_minor']*r.uniform(.1,1)));currency=charge['currency'];account=charge['account_id'];original=charge['transaction_id']
        status='refunded' if refund else r.choices(['settled','failed','pending'],[88,8,4])[0]
        x.update(transaction_id=w.uid('transaction',i),account_id=account,customer_id=x['user_id'],currency=currency,amount_minor=amount,
                 merchant_id=min(2000,int(r.paretovariate(1.3)*10)),category='subscription' if recurring else r.choice(['storage','compute','services','marketplace']),status=status,
                 payment_method=r.choices(['card','bank_transfer','wallet','invoice'],[55,20,15,10])[0],risk_score=round(r.uniform(.8,1) if fraud else min(.99,r.betavariate(1,12)),4),
                 original_transaction_id=original,recurring_plan_id=w.uid('plan',x['user_id']) if recurring else None,retry_attempt=r.randint(1,3) if 'retry' in x['quality'] else 0)
        if status=='settled':self.settled.append({k:x[k] for k in ['transaction_id','amount_minor','currency','account_id']})
        return [('transactions/transactions.jsonl',x)]
