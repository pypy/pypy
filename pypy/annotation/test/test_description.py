from pypy.annotation.description import ClassDesc

class FakeBookkeeper:
    def __init__(self):
        self.seen = {}
    def getdesc(self, cls):
        if cls not in self.seen:
            self.seen[cls] = ClassDesc(self, cls)
        return self.seen[cls]

def test_getcommonbase():
    class Base(object): pass
    class A(Base):      pass
    class B(A):         pass
    class C(B):         pass
    class D(A):         pass
    bk = FakeBookkeeper()
    dA = bk.getdesc(A)
    dB = bk.getdesc(B)
    dC = bk.getdesc(C)
    dD = bk.getdesc(D)
    assert ClassDesc.getcommonbase([dC, dD]) is dA
