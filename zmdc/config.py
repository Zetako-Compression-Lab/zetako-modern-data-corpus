from dataclasses import dataclass, field, asdict
import re

WEIGHTS = {'api':150, 'telemetry':150, 'observability':150, 'logs':125,
           'database':125, 'transactions':100, 'collaboration':75, 'binary':75,
           'entropy-control':50}
START_MS = 1767225600000
DAY_MS = 86400000
RATES = {'duplicate':.01,'delayed':.025,'missing':.025,'null':.02,
         'retry':.03,'anomaly':.005,'clock_drift':.03,'unexpected_enum':.003}

@dataclass
class Config:
    version: str = '1.0'
    seed: int = 20260914
    size: int = 1_000_000_000
    users: int = 50_000
    organizations: int = 500
    devices: int = 5_000
    instances: int = 240
    days: int = 30
    rates: dict = field(default_factory=lambda:dict(RATES))
    def check(self):
        if self.version != '1.0': raise ValueError('Only specification 1.0 is implemented')
        if self.size < 100_000: raise ValueError('Minimum development size is 100KB')
        if self.days != 30: raise ValueError('v1.0 defines a 30-day simulation')
        if min(self.users,self.organizations,self.devices,self.instances)<1: raise ValueError('World sizes must be positive')
        if self.instances < 160: raise ValueError('At least 160 instances cover 20 services in 8 regions')
        if set(self.rates)!=set(RATES) or any(not 0<=p<=.25 for p in self.rates.values()):
            raise ValueError('Every documented rate must be present and between 0 and .25')
        return self
    def to_dict(self): return asdict(self)

def parse_size(text):
    match=re.fullmatch(r'(\d+)(B|KB|MB|GB|KiB|MiB|GiB)?',text,re.I)
    if not match: raise ValueError('Use e.g. 10MB, 100MB or 1GB')
    factor={'b':1,'kb':1000,'mb':10**6,'gb':10**9,'kib':1024,'mib':2**20,'gib':2**30}
    return int(match[1])*factor[(match[2] or 'B').lower()]
