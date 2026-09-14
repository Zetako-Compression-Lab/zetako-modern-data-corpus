import argparse,json,sys,time,resource
from pathlib import Path
from .config import Config,WEIGHTS,parse_size
from .generation import generate
from .validation import validate,records
from .encoders.variants import convert

def main(argv=None):
    p=argparse.ArgumentParser(prog='zmdc',description='ZMDC — Zetako Modern Data Corpus')
    sub=p.add_subparsers(dest='command',required=True)
    g=sub.add_parser('generate');g.add_argument('--version',default='1.0');g.add_argument('--seed',type=int,default=20260914);g.add_argument('--size',type=parse_size,default=1_000_000_000)
    g.add_argument('--output',type=Path,default=Path('zmdc-output'));g.add_argument('--workload',choices=list(WEIGHTS),action='append');g.add_argument('--config',type=Path)
    for cmd in ['validate','stats','manifest','inspect']:
        q=sub.add_parser(cmd);q.add_argument('corpus',type=Path)
        if cmd=='inspect':q.add_argument('--limit',type=int,default=2)
    e=sub.add_parser('encode');e.add_argument('source',type=Path);e.add_argument('--format',choices=['csv','binary'],required=True);e.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='generate':
            override=json.loads(args.config.read_text()) if args.config else {};override.update(version=args.version,seed=args.seed,size=args.size)
            cfg=Config(**override).check();start=time.perf_counter()
            m=generate(cfg,args.output,args.workload,lambda w,s:print(f"{w}: {s['bytes']} bytes, {s['records']} records",file=sys.stderr,flush=True))
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            profile={'generation_seconds':time.perf_counter()-start,'peak_rss_bytes':rss if sys.platform=='darwin' else rss*1024,'corpus':str(args.output),'global_sha256':m['global_sha256']}
            args.output.with_name(args.output.name+'.profile.json').write_text(json.dumps(profile,indent=2)+'\n')
            result={'primary_bytes':m['primary_bytes'],'total_bytes':m['total_bytes'],'records':m['records'],'global_sha256':m['global_sha256'],**profile}
        elif args.command in ['validate','stats']:result=validate(args.corpus)
        elif args.command=='manifest':result=json.loads((args.corpus/'manifest.json').read_text())
        elif args.command=='encode':result=convert(args.source,args.output,args.format)
        else:
            m=json.loads((args.corpus/'manifest.json').read_text());samples={}
            from itertools import islice
            for e in m['files']:
                if e['role']!='metadata':samples[e['path']]=[r for r,_ in islice(records(args.corpus/e['path'],e['format']),max(0,min(args.limit,20)))]
            result={'manifest':{k:m[k] for k in ['name','version','seed','primary_bytes','records','global_sha256']},'samples':samples}
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True,default=lambda v:{'bytes':len(v),'preview_hex':v[:32].hex()} if isinstance(v,bytes) else str(v)))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(f'zmdc: {exc}',file=sys.stderr);raise SystemExit(2)

if __name__=='__main__':main()
