from pathlib import Path
from collections import Counter
import json,hashlib,sqlite3,tempfile,math
from .config import Config,START_MS,DAY_MS,WEIGHTS
from .world import REGIONS,SERVICES,schema,day_of
from .encoders import canonical
from .encoders.binary import read_records,pack
from .manifest import global_hash
from .statistics import Stats,byte_entropy

class ValidationError(ValueError):pass

def require(ok,message):
    if not ok:raise ValidationError(message)

def records(path,fmt):
    with open(path,'rb') as fp:
        if fmt=='binary':yield from read_records(fp);return
        for line in fp:
            require(len(line)<=16*1024*1024 and line.endswith(b'\n'),'Invalid or unterminated record')
            body=line.split(b'\t',1)[1] if fmt=='log' else line
            record=json.loads(body,parse_constant=lambda s:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            require(isinstance(record,dict),'Record must be an object')
            require(canonical(record)+b'\n'==body,'JSON serialization is not canonical')
            if fmt=='log':
                expected=f"{record['observed_timestamp_ms']} {record['severity']} {record['service']} ".encode()
                require(line.split(b'\t',1)[0]==expected,'Log header disagrees with payload')
            yield record,len(line)

def validate(root):
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text());config=Config(**manifest['configuration']).check()
    require(manifest['version']==config.version and manifest['seed']==config.seed,'Manifest config disagreement')
    selected=manifest['selected_workloads']
    require(bool(selected) and len(selected)==len(set(selected)) and set(selected)<=set(WEIGHTS),'Invalid selected workloads')
    entries=manifest['files'];paths=[e['path'] for e in entries]
    for e in entries:
        if e['role']=='metadata':require(e['path']=='README.txt' and e['format']=='text','Unexpected metadata entry')
        else:
            require(e['workload'] in WEIGHTS and e['format'] in ['jsonl','binary','log'],'Invalid workload/format')
            require(e['role']==('primary' if e['workload'] in selected else 'support'),'Incorrect workload role')
    require(len(paths)==len(set(paths)),'Duplicate file paths')
    actual=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'manifest.json')
    require(sorted(paths)==actual,'Unexpected or missing files')
    for p in paths:require(not Path(p).is_absolute() and '..' not in Path(p).parts and not (root/p).is_symlink(),'Unsafe manifest path')
    require(manifest['global_sha256']==global_hash(entries),'Global manifest hash mismatch')
    require(manifest['number_of_files']==len(entries),'File count mismatch')
    require(manifest['total_bytes']==sum(e['bytes'] for e in entries),'Total bytes mismatch')
    require(manifest['primary_bytes']==sum(e['bytes'] for e in entries if e['role']=='primary'),'Primary bytes mismatch')
    require(manifest['records']==sum(e['records'] for e in entries if e['role']=='primary'),'Total records mismatch')
    result={'valid':False,'global_sha256':manifest['global_sha256'],'files':{},'workloads':{},'warnings':[]};stats={};counts=Counter()
    with tempfile.TemporaryDirectory(prefix='zmdc-validate-') as td:
        db=sqlite3.connect(str(Path(td)/'indexes.sqlite'));db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF');db.execute('PRAGMA cache_size=-8192');db.execute('PRAGMA temp_store=FILE')
        db.executescript('CREATE TABLE seen(id TEXT PRIMARY KEY, hash BLOB, workload TEXT); CREATE TABLE requests(id TEXT PRIMARY KEY,user INTEGER,org INTEGER,region TEXT,service TEXT,instance INTEGER,trace TEXT); CREATE TABLE spans(id TEXT PRIMARY KEY,trace TEXT,start INTEGER,end INTEGER); CREATE TABLE charges(id TEXT PRIMARY KEY,account INTEGER,currency TEXT,amount INTEGER); CREATE TABLE cardinality(workload TEXT, field TEXT, value TEXT, PRIMARY KEY(workload,field,value)) WITHOUT ROWID;')
        api=next(e for e in entries if e['workload']=='api')
        for r,_ in records(root/api['path'],'jsonl'):
            fields=(r['request_id'],r['user_id'],r['organization_id'],r['region'],r['service'],r['instance_id'],r['trace_id'])
            old=db.execute('SELECT user,org,region,service,instance,trace FROM requests WHERE id=?',(r['request_id'],)).fetchone()
            if old:require(r['is_duplicate'] and old==fields[1:],'Request ID collision')
            else:db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?)',fields)
        db.commit();db_state={};sequences={};last_obs={}
        for e in sorted(entries,key=lambda e:(0 if e['path'].endswith('traces.jsonl') else 1,e['path'])):
            path=root/e['path'];hist=Counter();h=hashlib.sha256();size=0
            with path.open('rb') as fp:
                for chunk in iter(lambda:fp.read(1024*1024),b''):size+=len(chunk);h.update(chunk);hist.update(chunk)
            require(size==e['bytes'] and h.hexdigest()==e['sha256'],f"Size/hash mismatch: {e['path']}")
            if e['role']=='metadata':continue
            family=e['workload'];st=stats.setdefault(family,Stats());n=0;schemas=Counter();obs_min=None;obs_max=None
            for r,length in records(path,e['format']):
                n+=1;counts[family]+=1
                try:
                    check_common(r,config)
                    if family!='api':
                        ref=db.execute('SELECT user,org,region,service,instance,trace FROM requests WHERE id=?',(r['api_request_id'],)).fetchone()
                        require(ref==tuple(r[k] for k in ['user_id','organization_id','region','service','instance_id','linked_trace_id']),'Broken API/world relationship')
                    normalized=dict(r);normalized['is_duplicate']=False;fingerprint=hashlib.sha256(pack(normalized) if e['format']=='binary' else canonical(normalized)).digest()
                    if r['is_duplicate']:
                        old=db.execute('SELECT hash FROM seen WHERE id=?',(r['record_id'],)).fetchone()
                        require(old is not None and old[0]==fingerprint,'Invalid duplicate payload or unknown original')
                    else:
                        try:db.execute('INSERT INTO seen VALUES (?,?,?)',(r['record_id'],fingerprint,family))
                        except sqlite3.IntegrityError:raise ValidationError('Undeclared duplicate record ID')
                        require(r['observed_timestamp_ms']>=last_obs.get(e['path'],0),'Observation order violation')
                        last_obs[e['path']]=r['observed_timestamp_ms']
                        if family=='observability':check_observability(r,db)
                        if family=='database':check_cdc(r,db_state,sequences)
                        if family=='transactions':check_transaction(r,db)
                        if family=='telemetry':check_telemetry(r)
                        high=[(family,k,str(r[k])) for k in ['request_id','trace_id','session_id','message_id','transaction_id','api_request_id'] if r.get(k) is not None]
                        db.executemany('INSERT OR IGNORE INTO cardinality VALUES (?,?,?)',high)
                    schemas[r['schema_version']]+=1;st.add(r,length,e['path'])
                    obs=r['observed_timestamp_ms'];obs_min=obs if obs_min is None else min(obs_min,obs);obs_max=obs if obs_max is None else max(obs_max,obs)
                except (KeyError,TypeError,ValueError,sqlite3.Error) as exc:
                    raise ValidationError(f"{e['path']} record {n}: {exc}") from exc
                if n%10000==0:db.commit()
            db.commit();require(n==e['records'],f"Record count mismatch: {e['path']}");require(dict(schemas)==e['schemas'],'Schema counts mismatch')
            require((obs_min,obs_max)==(e['min_observed_ms'],e['max_observed_ms']),'Logical range mismatch')
            result['files'][e['path']]={'bytes':size,'records':n,'sha256':h.hexdigest(),'zero_order_byte_entropy_bits':byte_entropy(hist)}
        for family,st in stats.items():
            unique=db.execute('SELECT COUNT(*) FROM seen WHERE workload=?',(family,)).fetchone()[0]
            result['workloads'][family]=st.result(unique)
            result['workloads'][family]['cardinality'].update(dict(db.execute('SELECT field,COUNT(*) FROM cardinality WHERE workload=? GROUP BY field',(family,))))
            summary=manifest['workloads'][family]
            entries_f=[e for e in entries if e['workload']==family]
            require(summary['records']==counts[family] and summary['bytes']==sum(e['bytes'] for e in entries_f),'Workload totals mismatch')
            target=config.size*WEIGHTS[family]//1000
            require(summary['target_bytes']==target and target<=summary['bytes']<=target+summary['max_emission_unit_bytes']+8,'Workload budget mismatch')
            # Duplicates are sampled per emission bundle; trace bundles induce dependence.
            # Wide tolerances flag gross defects rather than treating records as independent trials.
            rate=st.duplicates/st.n
            if st.n>100 and abs(rate-config.rates['duplicate'])>max(.04,8*math.sqrt(max(.001,config.rates['duplicate'])/st.n)):
                result['warnings'].append(f'{family}: observed duplicate rate {rate:.4f} differs materially from configured rate')
        db.close()
    result['valid']=True;result['records']=manifest['records'];result['primary_bytes']=manifest['primary_bytes'];return result

def check_common(r,c):
    require(isinstance(r['record_id'],str) and len(r['record_id'])==24,'Invalid record ID')
    require(isinstance(r['is_duplicate'],bool),'Duplicate marker must be boolean')
    require(isinstance(r['quality'],list) and len(set(r['quality']))==len(r['quality']) and set(r['quality'])<=set(c.rates)-{'duplicate'},'Invalid quality flags')
    for field,bound in [('user_id',c.users),('organization_id',c.organizations),('instance_id',c.instances)]:require(type(r[field]) is int and 1<=r[field]<=bound,'Invalid '+field)
    require(r['organization_id']==(r['user_id']-1)%c.organizations+1,'Invalid user organization')
    require(r['region'] in REGIONS and r['service'] in SERVICES,'Unknown world entity')
    require(SERVICES[(r['instance_id']-1)%20]==r['service'],'Instance/service mismatch')
    require(REGIONS[((r['instance_id']-1)//20)%8]==r['region'],'Instance/region mismatch')
    if 'device_id' in r:require(type(r['device_id']) is int and 1<=r['device_id']<=c.devices,'Device reference invalid')
    observed=r['observed_timestamp_ms'];require(type(observed) is int and START_MS<=observed<START_MS+c.days*DAY_MS,'Observation outside time range')
    require(type(r['timestamp_ms']) is int,'Timestamp must be integer milliseconds')
    require(0<=r['delivery_delay_ms']<=900000 and abs(r['clock_drift_ms'])<=1500,'Timing bounds violated')
    require(r['timestamp_ms']==observed-r['delivery_delay_ms']+r['clock_drift_ms'],'Timing fields disagree')
    require(('delayed' in r['quality'])==(r['delivery_delay_ms']>=1000),'Delay marker mismatch')
    require(r['schema_version']==schema(observed,r['instance_id']),'Ineligible schema version')
    day=day_of(observed)
    require(('deployment_context' in r)==(day>=8),'Deployment field evolution mismatch')
    require(('legacy_collector' in r)==(day<24 or (day<27 and r['instance_id']%4==0)),'Deprecated field evolution mismatch')
    require(('missing' in r['quality'])==('metadata' not in r),'Missing marker mismatch')
    require(('null' in r['quality'])==(r.get('optional_context') is None),'Null marker mismatch')
    require(('unexpected_enum' in r['quality'])==('processing_class' in r),'Enum marker mismatch')
    if r['kind']=='api_request':
        key='client_type' if day_of(observed)<15 else 'client_family';other='client_family' if key=='client_type' else 'client_type'
        require(key in r and other not in r,'Client field evolution mismatch')
        require(r['status_code'] in [200,201,204,400,401,403,404,429,500,503],'Invalid API status')

def check_observability(r,db):
    if r['kind']=='span':
        if r['parent_span_id'] is not None:
            parent=db.execute('SELECT trace,start,end FROM spans WHERE id=?',(r['parent_span_id'],)).fetchone()
            require(parent is not None and parent[0]==r['trace_id'],'Invalid trace parent')
            require(parent[1]<=r['span_start_ns']<=r['span_end_ns']<=parent[2],'Child span lies outside its parent')
        require(r['duration_ms']>=0 and r['span_end_ns']-r['span_start_ns']==int(r['duration_ms']*1_000_000),'Invalid span duration')
        db.execute('INSERT INTO spans VALUES (?,?,?,?)',(r['span_id'],r['trace_id'],r['span_start_ns'],r['span_end_ns']))
    elif r['kind']=='otel_log':require(db.execute('SELECT trace FROM spans WHERE id=?',(r['span_id'],)).fetchone()==(r['trace_id'],),'Log has invalid span reference')

def check_cdc(r,state,sequences):
    require(r['sequence']>sequences.get('last',0),'Nonmonotonic CDC sequence');sequences['last']=r['sequence']
    key=(r['table'],r['primary_key']);op=r['operation'];before=r['before'];after=r['after']
    if op=='INSERT':require(key not in state and before is None and isinstance(after,dict),'Invalid insert');state[key]=after
    elif op in ('UPDATE','DELETE'):
        require(key in state and state[key]==before,'CDC before image mismatch')
        if op=='DELETE':require(after is None,'Delete after must be null');del state[key]
        else:require(after['revision']==before['revision']+1,'Revision must increase');state[key]=after
    else:raise ValidationError('Unknown CDC operation')
    require(len(state)<=6*512,'CDC state exceeds specified bound')

def check_transaction(r,db):
    if r['status']=='refunded':
        original=db.execute('SELECT account,currency,amount FROM charges WHERE id=?',(r['original_transaction_id'],)).fetchone()
        require(original is not None and original[:2]==(r['account_id'],r['currency']) and -original[2]<=r['amount_minor']<0,'Invalid refund')
    elif r['status']=='settled':db.execute('INSERT INTO charges VALUES (?,?,?,?)',(r['transaction_id'],r['account_id'],r['currency'],r['amount_minor']))
    require(r['customer_id']==r['user_id'] and 0<=r['risk_score']<=1,'Invalid transaction customer/risk')

def check_telemetry(r):
    require(-20<=r['temperature']<=95 and 0<=r['battery_level']<=100,'Invalid sensor range')
    require(abs(r['power']-r['current']*r['voltage'])<.001,'Correlated power/current mismatch')
    expected='2.4.0' if day_of(r['observed_timestamp_ms'])>=10+r['device_id']%10 else '2.3.1'
    require(r['firmware_version']==expected,'Firmware rollout mismatch')
