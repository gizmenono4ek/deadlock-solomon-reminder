import struct, sys
sys.path.insert(0,'scratch'); from vpk import VPK
def blocks(data):
    fsz,hv,ver,boff,bcnt=struct.unpack('<IHHII',data[:16]); p=8+boff; out=[]
    for i in range(bcnt):
        typ=data[p:p+4].decode(); off,sz=struct.unpack('<II',data[p+4:p+12]); out.append((typ,p+4+off,sz)); p+=12
    return out
def text(data):
    for typ,off,sz in blocks(data):
        if typ=='DATA':
            crc,cnt=struct.unpack('<IH',data[off:off+6]); p=off+6
            for i in range(cnt):
                e=data.index(b'\0',p); p=e+1+8
            return data[p:off+sz].decode('utf-8','replace')
if __name__=='__main__':
    v=VPK(sys.argv[1])
    for n in sys.argv[2:]:
        print('=====',n); print(text(v.read(n)))
