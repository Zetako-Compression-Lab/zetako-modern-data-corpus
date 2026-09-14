import hashlib, random

def stream(seed, name):
    digest=hashlib.sha256(f'ZMDC/1.0/{seed}/{name}'.encode()).digest()
    return random.Random(int.from_bytes(digest,'big'))

def identifier(seed, namespace, value, length=24):
    return hashlib.sha256(f'ZMDC/1.0/{seed}/{namespace}/{value}'.encode()).hexdigest()[:length]

def opaque(seed, namespace, value, size):
    return hashlib.shake_256(f'ZMDC/1.0/{seed}/{namespace}/{value}'.encode()).digest(size)
