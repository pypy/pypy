# this file contains the definitions and most extremely faked
# implementations of things relating to the description of the layout
# of objects in memeory.

# sizeof, offsetof

from pypy.rpython.objectmodel import Symbolic
from pypy.rpython.lltypesystem import lltype

class OffsetOf(Symbolic):

    def __init__(self, TYPE, *fldnames):
        self.TYPE = TYPE
        self.fldnames = fldnames

    def annotation(self):
        from pypy.annotation import model
        return model.SomeOffset()

    def lltype(self):
        return lltype.Signed

    def __repr__(self):
        return "<OffsetOf %r %r>" % (self.TYPE, self.fldnames)

    def __add__(self, other):
        if not isinstance(other, OffsetOf):
            return NotImplemented
        t = self.TYPE
        for f in self.fldnames:
            t = t._flds[f]
        assert t == other.TYPE
        return OffsetOf(self.TYPE, *(self.fldnames + other.fldnames))

def sizeof(TYPE, n=None):
    pass

def offsetof(TYPE, fldname):
    assert fldname in TYPE._flds
    return OffsetOf(TYPE, fldname)

def itemoffsetof(TYPE, n=None):
    pass

class fakeaddress(object):
    def __init__(self, ob, offset=None):
        self.ob = ob
        if offset is None:
            self.offset = OffsetOf(lltype.typeOf(self.ob))
        else:
            self.offset = offset

    def __add__(self, other):
        if not isinstance(other, OffsetOf):
            return NotImplemented
        return fakeaddress(self.ob, self.offset + other)
    
class _fakeaccessor(object):
    def __init__(self, addr):
        self.addr = addr
    def __getitem__(self, index):
        assert index == 0
        ob = self.addr.ob
        for n in self.addr.offset.fldnames:
            ob = getattr(ob, n)
        # XXX will need to do pointers differently!
        assert lltype.typeOf(ob) == self.TYPE 
        return ob
        
class _signed_fakeaccessor(_fakeaccessor):
    TYPE = lltype.Signed

fakeaddress.signed = property(_signed_fakeaccessor)

Address = lltype.Primitive("Address", fakeaddress(None))

fakeaddress._TYPE = Address
