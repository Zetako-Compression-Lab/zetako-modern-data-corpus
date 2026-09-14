import json

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def encode_line(record): return canonical(record)+b'\n'

def encode_log(record):
    header=f"{record['observed_timestamp_ms']} {record['severity']} {record['service']} "
    return header.encode()+b'\t'+encode_line(record)
