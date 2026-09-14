import math
from ..world import day_of,REGIONS

class Telemetry:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors;self.state={};self.samples={}
    def make(self,i,progress):
        w,r=self.w,self.r;anchor=self.a.at(progress,r);x=w.common('telemetry',i,'telemetry',progress,r,anchor)
        day=day_of(x['observed_timestamp_ms']);device=r.randrange(1,w.config.devices+1)
        # A scheduled outage removes a cohort from reporting, without inserting fake zero readings.
        if day in (11,12) and device%17==0:device=device%w.config.devices+1
        old=self.state.get(device,20+(device%180)/10);phase=(x['observed_timestamp_ms']/86400000)%1
        target=20+(device%180)/10+2*math.sin(2*math.pi*phase)
        anomaly='anomaly' in x['quality'];temp=old+.08*(target-old)+r.gauss(0,.12)+(12 if anomaly else 0)
        temp=round(max(-20,min(95,temp)),3);self.state[device]=temp
        seq=self.samples.get(device,0)+1+(r.randrange(2,8) if day in (11,12) else 0);self.samples[device]=seq
        current=round(.6+max(0,temp-15)*.028+r.gauss(0,.008),4);voltage=round(12+r.gauss(0,.03),4)
        failed=(device%83==0 and day in (18,19))
        x.update(device_id=device,device_region=REGIONS[device%8],device_type=['thermostat','gateway','pump','meter','robot'][device%5],
                 firmware_version='2.4.0' if day>=10+device%10 else '2.3.1',sample_sequence=seq,
                 temperature=temp,humidity=round(max(0,min(100,62-.5*(temp-20)+r.gauss(0,.2))),3),
                 pressure=round(1013+math.sin(phase*6.28)*3+r.gauss(0,.1),3),voltage=voltage,current=current,
                 power=round(current*voltage,4),fan_rpm=round(max(0,temp-24)*130+r.gauss(0,5),2),
                 vibration=round(abs(r.gauss(.02,.004))*(8 if anomaly else 1),5),
                 signal_strength=-40-device%35,battery_level=round(max(0,100-day*.8-device%10),2),
                 operating_state='failed' if failed else 'degraded' if anomaly else 'running',error_code='SENSOR_TIMEOUT' if failed else None)
        if failed:x['humidity']=None
        return [('telemetry/telemetry.jsonl',x)]
