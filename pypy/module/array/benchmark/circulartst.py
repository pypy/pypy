from array import array
class Circular(array):
    def __new__(cls):
        self = array.__new__(cls, 'd', range(65536))
        return self
    def __getitem__(self, i):
        assert len(self) == 65536 
        return array.__getitem__(self, i & 65535)

import sys
def main():
    buf = Circular()
    i = 10
    sa = 0
    #         1048576
    while i < 949999:
        sa += buf[i-2] + buf[i-1] + buf[i] + buf[i+1] + buf[i+2]
        if i%100 == 0: sys.stderr.write('%d\n'%i)
        i += 1
    return sa

print main()
