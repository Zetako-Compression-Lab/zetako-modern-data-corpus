"""ZMDCBIN v1: documented framing + typed payload, without compression."""
import struct,zlib,math
MAGIC=b'ZMDCBIN\x01'
HEADER=struct.Struct('<IBQQII')
TYPES={'telemetry':1,'metric':2,'binary_event':3,'transaction':4,'control':5}
MAX_PAYLOAD=16*1024*1024

def pack(value):
    if value is None:return b'\x00'
    if value is False:return b'\x01'
    if value is True:return b'\x02'
    if isinstance(value,int):return b'\x03'+struct.pack('<q',value)
    if isinstance(value,float):
        if not math.isfinite(value):raise ValueError('Non-finite float')
        return b'\x04'+struct.pack('<d',value)
    if isinstance(value,(str,bytes)):
        data=value.encode('utf-8') if isinstance(value,str) else value
        return (b'\x05' if isinstance(value,str) else b'\x06')+struct.pack('<I',len(data))+data
    if isinstance(value,list):return b'\x07'+struct.pack('<I',len(value))+b''.join(pack(v) for v in value)
    if isinstance(value,dict):
        return b'\x08'+struct.pack('<I',len(value))+b''.join(pack(k)+pack(value[k]) for k in sorted(value))
    raise TypeError(type(value))

def unpack(data):
    view=memoryview(data);pos=0
    def read(n):
        nonlocal pos
        if n<0 or pos+n>len(view):raise ValueError('Truncated typed payload')
        b=view[pos:pos+n];pos+=n;return b
    def u32():return struct.unpack('<I',read(4))[0]
    def value(depth=0):
        if depth>32:raise ValueError('Excessive nesting')
        tag=read(1)[0]
        if tag==0:return None
        if tag==1:return False
        if tag==2:return True
        if tag==3:return struct.unpack('<q',read(8))[0]
        if tag==4:
            x=struct.unpack('<d',read(8))[0]
            if not math.isfinite(x):raise ValueError('Non-finite float')
            return x
        if tag in (5,6):
            raw=bytes(read(u32()));return raw.decode('utf-8') if tag==5 else raw
        if tag in (7,8):
            count=u32()
            if count>len(view):raise ValueError('Impossible item count')
            if tag==7:return [value(depth+1) for _ in range(count)]
            result={};previous=None
            for _ in range(count):
                key=value(depth+1)
                if not isinstance(key,str) or (previous is not None and key<=previous):raise ValueError('Map keys must be unique sorted strings')
                result[key]=value(depth+1);previous=key
            return result
        raise ValueError('Unknown type tag')
    result=value()
    if pos!=len(data):raise ValueError('Trailing payload bytes')
    return result

def encode(record):
    body=pack(record)
    if len(body)>MAX_PAYLOAD:raise ValueError('Payload too large')
    return HEADER.pack(len(body),TYPES.get(record['kind'],255),record['timestamp_ms'],record.get('device_id',record['user_id']),int(record.get('is_duplicate',False)),zlib.crc32(body))+body

def read_records(fp):
    if fp.read(len(MAGIC))!=MAGIC:raise ValueError('Invalid binary magic')
    while True:
        header=fp.read(HEADER.size)
        if not header:return
        if len(header)!=HEADER.size:raise ValueError('Truncated header')
        size,kind,ts,entity,flags,crc=HEADER.unpack(header)
        if size>MAX_PAYLOAD:raise ValueError('Oversize binary record')
        body=fp.read(size)
        if len(body)!=size or zlib.crc32(body)!=crc:raise ValueError('Invalid payload length or CRC')
        record=unpack(body)
        if not isinstance(record,dict):raise ValueError('Record must be a map')
        if (kind,ts,entity,flags)!=(TYPES.get(record['kind'],255),record['timestamp_ms'],record.get('device_id',record['user_id']),int(record.get('is_duplicate',False))):raise ValueError('Header/payload mismatch')
        yield record,HEADER.size+size
