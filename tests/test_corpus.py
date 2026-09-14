import unittest,tempfile,json,sqlite3
from pathlib import Path
from zmdc.config import Config
from zmdc.generation import generate
from zmdc.validation import validate,ValidationError
from zmdc.encoders import canonical
from zmdc.encoders.binary import pack,unpack,read_records
from zmdc.encoders.variants import convert
from zmdc.manifest import global_hash,file_hash,save

class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.a=cls.root/'a';cls.b=cls.root/'b';cls.c=cls.root/'c';cls.config=Config(size=1_000_000)
        cls.ma=generate(cls.config,cls.a);generate(cls.config,cls.b);generate(Config(size=1_000_000,seed=9),cls.c)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_determinism_byte_for_byte(self):
        paths=lambda root:sorted(p.relative_to(root) for p in root.rglob('*') if p.is_file())
        self.assertEqual(paths(self.a),paths(self.b))
        for path in paths(self.a):self.assertEqual((self.a/path).read_bytes(),(self.b/path).read_bytes(),str(path))
        self.assertNotEqual(self.ma['global_sha256'],json.loads((self.c/'manifest.json').read_text())['global_sha256'])
    def test_v1_frozen_golden(self):
        fixture=json.loads((Path(__file__).parent/'v1_golden.json').read_text())
        for key in ['global_sha256','primary_bytes','records']:self.assertEqual(self.ma[key],fixture[key])
    def test_full_validation_and_stats(self):
        v=validate(self.a);self.assertTrue(v['valid']);self.assertEqual(v['records'],self.ma['records']);self.assertEqual(len(v['workloads']),9)
    def test_alternative_logical_identity(self):
        for fmt in ['csv','binary']:self.assertTrue(convert(self.a/'telemetry/telemetry.jsonl',self.root/('variant.'+fmt),fmt)['logical_roundtrip_verified'])
    def test_binary_nested_roundtrip_and_corruption(self):
        value={'a':[None,False,True,123,-9,1.25,'héllo',b'\x00\xff'],'z':{}}
        self.assertEqual(unpack(pack(value)),value)
        with self.assertRaises(ValueError):unpack(pack(value)[:-1])
        import io
        payload=bytearray((self.a/'binary/records.bin').read_bytes());payload[-1]^=1
        with self.assertRaises(ValueError):list(read_records(io.BytesIO(payload)))
    def test_no_overwrite(self):
        with self.assertRaises(ValueError):generate(self.config,self.a)
    def test_select_workload_support_and_validation(self):
        dest=self.root/'selected';m=generate(Config(size=1_000_000),dest,['telemetry'])
        self.assertEqual(m['selected_workloads'],['telemetry']);self.assertTrue((dest/'_support/api/events.jsonl').exists());self.assertTrue(validate(dest)['valid'])
    def test_payload_checksum_detects_change(self):
        import shutil
        dest=self.root/'corrupt';shutil.copytree(self.a,dest)
        with (dest/'api/events.jsonl').open('ab') as fp:fp.write(b'{}\n')
        with self.assertRaises((ValidationError,KeyError)):validate(dest)
    def _mutate_record_and_rehash(self,label,path,mutate):
        import shutil
        dest=self.root/label;shutil.copytree(self.a,dest);p=dest/path
        lines=p.read_bytes().splitlines();r=json.loads(lines[0]);mutate(r);lines[0]=canonical(r);p.write_bytes(b'\n'.join(lines)+b'\n')
        m=json.loads((dest/'manifest.json').read_text());entry=next(e for e in m['files'] if e['path']==path);diff=p.stat().st_size-entry['bytes'];entry['bytes']+=diff;entry['sha256']=file_hash(p)
        m['total_bytes']+=diff;m['primary_bytes']+=diff;m['workloads'][entry['workload']]['bytes']+=diff;m['global_sha256']=global_hash(m['files']);save(dest/'manifest.json',m)
        return dest
    def test_broken_reference_with_valid_hash(self):
        dest=self._mutate_record_and_rehash('reference','telemetry/telemetry.jsonl',lambda r:r.update(api_request_id='does-not-exist'))
        with self.assertRaisesRegex(ValidationError,'relationship'):validate(dest)
    def test_schema_error_with_valid_hash(self):
        dest=self._mutate_record_and_rehash('schema','telemetry/telemetry.jsonl',lambda r:r.update(schema_version='9.9'))
        with self.assertRaisesRegex(ValidationError,'schema'):validate(dest)
    def test_wrong_cdc_before_image(self):
        from zmdc.validation import check_cdc
        with self.assertRaisesRegex(ValidationError,'before image'):check_cdc({'sequence':1,'table':'users','primary_key':'x','operation':'UPDATE','before':{},'after':{'revision':2}}, {},{})
    def test_rate_configuration_and_order(self):
        from zmdc.config import RATES
        a=self.root/'rates-a';b=self.root/'rates-b'
        rates={k:0. for k in RATES};reverse=dict(reversed(list(rates.items())))
        ma=generate(Config(size=1_000_000,rates=rates),a)
        mb=generate(Config(size=1_000_000,rates=reverse),b)
        self.assertEqual(ma['global_sha256'],mb['global_sha256'])
        result=validate(a)
        for workload in result['workloads'].values():
            self.assertEqual(workload['duplicate_rate'],0)
            self.assertEqual(workload['missing_metadata_rate'],0)
            self.assertEqual(workload['quality_counts'],{})
    def test_cross_process_hash_seed_independence(self):
        import subprocess,sys,os
        target=self.root/'subprocess'
        env=dict(os.environ,PYTHONHASHSEED='937')
        subprocess.run([sys.executable,'-m','zmdc','generate','--size','1MB','--output',str(target)],env=env,capture_output=True,check=True)
        for p in self.a.rglob('*'):
            if p.is_file():self.assertEqual(p.read_bytes(),(target/p.relative_to(self.a)).read_bytes())
    def test_wrong_trace_parent(self):
        from zmdc.validation import check_observability
        db=sqlite3.connect(':memory:');db.execute('CREATE TABLE spans(id TEXT PRIMARY KEY,trace TEXT,start INTEGER,end INTEGER)')
        with self.assertRaisesRegex(ValidationError,'parent'):check_observability({'kind':'span','parent_span_id':'unknown','trace_id':'t'},db)
        db.close()

if __name__=='__main__':unittest.main()
