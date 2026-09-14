import hashlib,json,platform,subprocess
from pathlib import Path
from .encoders import canonical
from . import __version__

def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as fp:
        for chunk in iter(lambda:fp.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def global_hash(files):
    rows=[{k:f[k] for k in ['path','bytes','sha256']} for f in sorted(files,key=lambda f:f['path'])]
    return hashlib.sha256(canonical(rows)).hexdigest()

def implementation_metadata():
    root=Path(__file__).resolve().parents[1];h=hashlib.sha256()
    for p in sorted((root/'zmdc').rglob('*.py')):
        h.update(p.relative_to(root).as_posix().encode()+b'\0');h.update(p.read_bytes())
    spec=root/'SPECIFICATION.md';h.update(spec.read_bytes())
    commit=None
    if (root/'.git').exists():
        r=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True)
        if r.returncode==0:commit=r.stdout.strip()
    return {'generator_version':__version__,'implementation_sha256':h.hexdigest(),
            'specification_sha256':file_hash(spec),'python_implementation':platform.python_implementation(),
            'python_version':platform.python_version(),'git_commit':commit}

def save(path,manifest):Path(path).write_bytes(canonical(manifest)+b'\n')
