from pypy.rpython.memory.gctransform2.refcounting import \
     RefcountingGCTransformer
from pypy.rpython.memory.gctransform2.boehm import \
     BoehmGCTransformer
from pypy.rpython.memory.gctransform2.test.test_transform import \
     rtype, rtype_and_transform, getops
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import lltype
from pypy.translator.translator import graphof

# ____________________________________________________________________
# testing the protection magic

def test_protect_unprotect():
    def p():    llop.gc_protect(lltype.Void, 'this is an object')
    def u():    llop.gc_unprotect(lltype.Void, 'this is an object')

    rgc = RefcountingGCTransformer
    bgc = BoehmGCTransformer
    expected = [1, 1, 0, 0]
    gcs = [rgc, rgc, bgc, bgc]
    fs = [p, u, p, u]
    for ex, f, gc in zip(expected, fs, gcs):
        t, transformer = rtype_and_transform(f, [], gc, check=False)
        ops = getops(graphof(t, f))
        assert len(ops.get('direct_call', [])) == ex
