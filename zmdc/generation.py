from pathlib import Path
from collections import Counter,deque
import copy,hashlib
from .config import WEIGHTS,START_MS,DAY_MS
from .rng import stream
from .world import World,Anchors,REGIONS,SERVICES
from .encoders import encode_line,canonical
from .encoders.jsonlines import encode_log
from .encoders.binary import MAGIC,encode as encode_binary
from .manifest import save,global_hash,implementation_metadata
from .workloads.api import API
from .workloads.telemetry import Telemetry
from .workloads.observability import Observability
from .workloads.logs import Logs
from .workloads.database import Database
from .workloads.transactions import Transactions
from .workloads.collaboration import Collaboration
from .workloads.structured_binary import StructuredBinary
from .workloads.entropy_control import EntropyControl

CLASSES={'api':API,'telemetry':Telemetry,'observability':Observability,'logs':Logs,'database':Database,
         'transactions':Transactions,'collaboration':Collaboration,'binary':StructuredBinary,'entropy-control':EntropyControl}

class Writer:
    def __init__(self,root,workload,role):self.root=root;self.workload=workload;self.role=role;self.open={};self.bytes=0;self.largest_unit=0
    def emit(self,unit):
        unit_bytes=0
        for path,record in unit:
            path=('_support/'+path) if self.role=='support' else path
            if path not in self.open:
                target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);fp=target.open('wb',buffering=1024*1024)
                entry={'path':path,'workload':self.workload,'role':self.role,'format':'binary' if path.endswith('.bin') else 'log' if path.endswith('.log') else 'jsonl',
                       'bytes':0,'records':0,'schemas':Counter(),'min_observed_ms':None,'max_observed_ms':None}
                self.open[path]=(fp,hashlib.sha256(),entry)
                if path.endswith('.bin'):fp.write(MAGIC);self.open[path][1].update(MAGIC);entry['bytes']+=len(MAGIC);self.bytes+=len(MAGIC)
            fp,h,e=self.open[path]
            raw=encode_binary(record) if e['format']=='binary' else encode_log(record) if e['format']=='log' else encode_line(record)
            fp.write(raw);h.update(raw);e['bytes']+=len(raw);e['records']+=1;self.bytes+=len(raw);unit_bytes+=len(raw);e['schemas'][record['schema_version']]+=1
            observed=record['observed_timestamp_ms'];e['min_observed_ms']=observed if e['min_observed_ms'] is None else min(e['min_observed_ms'],observed)
            e['max_observed_ms']=observed if e['max_observed_ms'] is None else max(e['max_observed_ms'],observed)
        self.largest_unit=max(self.largest_unit,unit_bytes)
    def finish(self):
        result=[]
        for fp,h,e in self.open.values():
            fp.close();e['sha256']=h.hexdigest();e['schemas']=dict(sorted(e['schemas'].items()));result.append(e)
        return sorted(result,key=lambda e:e['path'])

def generate(config,output,workloads=None,progress=None):
    config.check();root=Path(output)
    if root.exists() and any(root.iterdir()):raise ValueError('Output must be absent or empty; existing corpora are never overwritten')
    selected=list(WEIGHTS) if workloads is None else [w for w in WEIGHTS if w in workloads]
    if not selected or any(w not in WEIGHTS for w in (workloads or [])):raise ValueError('Unknown workload')
    root.mkdir(parents=True,exist_ok=True);world=World(config);files=[];summaries={}
    order=['api']+[w for w in selected if w!='api']
    for family in order:
        role='primary' if family in selected else 'support';budget=config.size*WEIGHTS[family]//1000
        rng=stream(config.seed,family);duplicate_rng=stream(config.seed,family+'/duplicates')
        anchors=None if family=='api' else Anchors(root/('api/events.jsonl' if 'api' in selected else '_support/api/events.jsonl'))
        generator=CLASSES[family](world,rng,anchors);writer=Writer(root,family,role);history=deque(maxlen=16);i=0
        try:
            while writer.bytes<budget:
                if history and duplicate_rng.random()<config.rates['duplicate']:
                    unit=copy.deepcopy(history[duplicate_rng.randrange(len(history))])
                    for _,r in unit:r['is_duplicate']=True
                else:
                    unit=generator.make(i,writer.bytes/budget);i+=1;history.append(unit)
                writer.emit(unit)
        finally:
            if anchors:anchors.close()
        entries=writer.finish();files.extend(entries)
        summaries[family]={'role':role,'target_bytes':budget,'bytes':writer.bytes,'records':sum(e['records'] for e in entries),
                           'files':len(entries),'max_emission_unit_bytes':writer.largest_unit,'overshoot_bytes':writer.bytes-budget}
        if progress:progress(family,summaries[family])
    readme=("ZMDC — Zetako Modern Data Corpus\nA deterministic synthetic corpus for benchmarking compression on contemporary structured and machine-generated data.\n"
            "Synthetic; independent of all compression engines. Specification version 1.0.\nOne primary representation per workload. Optional re-encodings do not belong to the official corpus.\n"
            "manifest.json lists exact sizes and hashes; total_bytes excludes manifest.json itself.\n")
    raw=readme.encode();(root/'README.txt').write_bytes(raw)
    files.append({'path':'README.txt','workload':'metadata','role':'metadata','format':'text','bytes':len(raw),'records':0,'schemas':{},'sha256':hashlib.sha256(raw).hexdigest()})
    files.sort(key=lambda e:e['path'])
    manifest={'name':'ZMDC-1G' if config.size==1_000_000_000 else 'ZMDC-development','version':config.version,'seed':config.seed,
              **implementation_metadata(),'configuration':config.to_dict(),'selected_workloads':selected,'logical_time_range':{'start_ms':START_MS,'end_exclusive_ms':START_MS+config.days*DAY_MS},
              'world':{'regions':REGIONS,'services':SERVICES,'organization_rule':'(user_id-1) % organizations + 1','instance_service_rule':'services[(instance_id-1) % 20]'},
              'target_primary_bytes':sum(config.size*WEIGHTS[w]//1000 for w in selected),
              'primary_bytes':sum(e['bytes'] for e in files if e['role']=='primary'),'total_bytes':sum(e['bytes'] for e in files),
              'records':sum(e['records'] for e in files if e['role']=='primary'),'number_of_files':len(files),'workloads':summaries,'files':files,'global_sha256':global_hash(files)}
    save(root/'manifest.json',manifest);return manifest
