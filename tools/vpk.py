import struct, sys, os, zlib
class VPK:
    def __init__(self, path):
        self.path=path; self.f=open(path,'rb'); d=self.f.read
        sig,ver=struct.unpack('<II',d(8)); assert sig==0x55aa1234, hex(sig)
        self.ver=ver
        if ver==1: (self.tree_size,)=struct.unpack('<I',d(4)); hdr=12
        else: self.tree_size,a,b,c,e=struct.unpack('<IIIII',d(20)); hdr=28
        self.hdr=hdr; self.entries={}
        rs=self._rs
        while True:
            ext=rs()
            if ext=='': break
            while True:
                p=rs()
                if p=='': break
                while True:
                    n=rs()
                    if n=='': break
                    crc,pre,ai,off,ln,term=struct.unpack('<IHHIIH',d(18))
                    pdata=d(pre)
                    full=(p+'/' if p and p!=' ' else '')+n+'.'+ext
                    self.entries[full]=(crc,ai,off,ln,pdata)
    def _rs(self):
        b=bytearray()
        while True:
            c=self.f.read(1)
            if c==b'\x00' or not c: return b.decode('utf-8','replace')
            b+=c
    def read(self,name):
        crc,ai,off,ln,pdata=self.entries[name]
        if ai==0x7fff:
            self.f.seek(self.hdr+self.tree_size+off); return pdata+self.f.read(ln)
        arch=self.path.replace('_dir.vpk','_%03d.vpk'%ai)
        with open(arch,'rb') as a: a.seek(off); return pdata+a.read(ln)
if __name__=='__main__':
    v=VPK(sys.argv[1]); pat=sys.argv[2] if len(sys.argv)>2 else ''
    for k in sorted(v.entries):
        if pat.lower() in k.lower(): print(k, v.entries[k][3])
