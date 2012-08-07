from pypy.translator.c.test.test_typed import CompilationTestCase
from pypy.translator.tool.staticsizereport import group_static_size, guess_size
from pypy.rpython.lltypesystem import llmemory, lltype, rffi

class TestStaticSizeReport(CompilationTestCase):
    def test_simple(self):
        class A:
            def __init__(self, n):
                if n:
                    self.next = A(n - 1)
                else:
                    self.next = None
                self.key = repr(self)
        a = A(100)
        def f(x):
            if x:
                return a.key
            return a.next.key
        func = self.getcompiled(f, [int])
        size, num = group_static_size(self.builder.db, self.builder.db.globalcontainers())
        for key, value in num.iteritems():
            if "staticsizereport.A" in str(key) and "vtable" not in str(key):
                assert value == 101

    def test_large_dict(self):
        d = {}
        d_small = {1:2}
        fixlist = [x for x in range(100)]
        dynlist = [x for x in range(100)]
        test_dict = dict(map(lambda x: (x, hex(x)), range(256, 4096)))
        reverse_dict = dict(map(lambda (x,y): (y,x), test_dict.items()))
        class wrap:
            pass
        for x in xrange(100):
            i = wrap()
            i.x = x
            d[x] = i
        def f(x):
            if x > 42:
                dynlist.append(x)
            return d[x].x + fixlist[x] + d_small[x] + reverse_dict[test_dict[x]]
        func = self.getcompiled(f, [int])
        db = self.builder.db
        gcontainers = list(db.globalcontainers())
        t = db.translator
        rtyper = t.rtyper
        get_container = lambda x: rtyper.getrepr(t.annotator.bookkeeper.immutablevalue(x)).convert_const(x)._obj
        dictvalnode = db.getcontainernode(get_container(d))
        dictvalnode2 = db.getcontainernode(get_container(d_small))
        fixarrayvalnode = db.getcontainernode(get_container(fixlist))
        dynarrayvalnode = db.getcontainernode(get_container(dynlist))
        test_dictnode = db.getcontainernode(get_container(test_dict))
        reverse_dictnode = db.getcontainernode(get_container(reverse_dict))

        S = rffi.sizeof(lltype.Signed)
        P = rffi.sizeof(rffi.VOIDP)
        B = 1 # bool
        assert guess_size(self.builder.db, dictvalnode, set()) > 100
        assert guess_size(self.builder.db, dictvalnode2, set()) == 2 * S + 1 * P + 1 * S + 8 * (2*S + 1 * B)
        r_set = set()
        dictnode_size = guess_size(db, test_dictnode, r_set)
        assert dictnode_size == 2 * S + 1 * P + 1 * S + (4096-256) * (1*S+1*P + (1 * S + 1*P + 5)) + (8192-4096+256) * (1*S+1*P)
        assert guess_size(self.builder.db, fixarrayvalnode, set()) == 100 * rffi.sizeof(lltype.Signed) + 1 * rffi.sizeof(lltype.Signed)
        assert guess_size(self.builder.db, dynarrayvalnode, set()) == 100 * rffi.sizeof(lltype.Signed) + 2 * rffi.sizeof(lltype.Signed) + 1 * rffi.sizeof(rffi.VOIDP)

