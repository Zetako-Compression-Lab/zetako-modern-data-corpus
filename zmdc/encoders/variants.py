import csv,json
from pathlib import Path
from .jsonlines import canonical
from .binary import MAGIC,encode,read_records

def convert(source,target,fmt):
    source=Path(source);target=Path(target)
    if target.exists():raise ValueError('Variant target already exists')
    target.parent.mkdir(parents=True,exist_ok=True)
    if fmt=='binary':
        with source.open('rb') as inp,target.open('wb') as out:
            out.write(MAGIC)
            for line in inp:out.write(encode(json.loads(line)))
    elif fmt=='csv':
        fields=set()
        with source.open('rb') as inp:
            for line in inp:fields.update(json.loads(line))
        fields=sorted(fields)
        with target.open('w',newline='',encoding='utf-8') as out,source.open('rb') as inp:
            writer=csv.writer(out,lineterminator='\n');writer.writerow(fields)
            for line in inp:
                r=json.loads(line);writer.writerow([canonical(r[k]).decode() if k in r else '' for k in fields])
    else:raise ValueError('Supported alternatives: csv, binary')
    from itertools import zip_longest
    with source.open('rb') as inp:
        for original,variant in zip_longest((json.loads(l) for l in inp),decode_variant(target,fmt)):
            if original!=variant:raise ValueError('Alternative encoding changed logical data')
    return {'format':fmt,'source':str(source),'target':str(target),'bytes':target.stat().st_size,'logical_roundtrip_verified':True}

def decode_variant(path,fmt):
    if fmt=='binary':
        with open(path,'rb') as fp:
            for r,_ in read_records(fp):yield r
    else:
        with open(path,newline='',encoding='utf-8') as fp:
            for row in csv.DictReader(fp):yield {k:json.loads(v) for k,v in row.items() if v!=''}
