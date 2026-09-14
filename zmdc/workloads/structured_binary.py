class StructuredBinary:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);x=w.common('binary',i,['telemetry','metric','binary_event','transaction'][i%4],progress,r,a)
        x.update(device_id=r.randrange(1,w.config.devices+1),sample_number=i,values=[round(r.gauss(0,1),5) for _ in range(8)],
                 counters=[i//8,i%256,int(a['latency_ms'])],flags=i%8,payload=w.uid('binary-payload',i,64),description='independent compact edge observation')
        # Binary telemetry is a separate logical sample family, not copied JSON telemetry.
        return [('binary/records.bin',x)]
