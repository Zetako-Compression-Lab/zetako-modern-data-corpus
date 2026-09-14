from ..rng import opaque
class EntropyControl:
    def __init__(self,world,rng,anchors):self.w=world;self.r=rng;self.a=anchors
    def make(self,i,progress):
        w,r=self.w,self.r;a=self.a.at(progress,r);x=w.common('entropy-control',i,'control',progress,r,a)
        x.update(control_type=['opaque_blob','nonce_bundle','hash_material','token_material'][i%4],
                 nonce=w.uid('nonce',i,32),token=w.uid('token',i,64),payload=opaque(w.config.seed,'entropy',i,32768))
        return [('entropy-control/control.bin',x)]
