import weakref
from rpython.rlib import rawrefcount, objectmodel, rgc
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY, REFCNT_FROM_PYPY_LIGHT
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.annlowlevel import llhelper
from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.config.translationoption import get_combined_translation_config


class W_Root(object):
    def __init__(self, intval=0):
        self.intval = intval
    def __nonzero__(self):
        raise Exception("you cannot do that, you must use space.is_true()")

PyObjectS = lltype.Struct('PyObjectS',
                          ('c_ob_refcnt', lltype.Signed),
                          ('c_ob_pypy_link', lltype.Signed))
PyObject = lltype.Ptr(PyObjectS)


class TestRawRefCount:

    def setup_method(self, meth):
        rawrefcount.init()

    def test_create_link_pypy(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        assert rawrefcount.from_obj(PyObject, p) == lltype.nullptr(PyObjectS)
        assert rawrefcount.to_obj(W_Root, ob) == None
        rawrefcount.create_link_pypy(p, ob)
        assert ob.c_ob_refcnt == 0
        ob.c_ob_refcnt += REFCNT_FROM_PYPY_LIGHT
        assert rawrefcount.from_obj(PyObject, p) == ob
        assert rawrefcount.to_obj(W_Root, ob) == p
        lltype.free(ob, flavor='raw')

    def test_create_link_pyobj(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        assert rawrefcount.from_obj(PyObject, p) == lltype.nullptr(PyObjectS)
        assert rawrefcount.to_obj(W_Root, ob) == None
        rawrefcount.create_link_pyobj(p, ob)
        assert ob.c_ob_refcnt == 0
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount.from_obj(PyObject, p) == lltype.nullptr(PyObjectS)
        assert rawrefcount.to_obj(W_Root, ob) == p
        lltype.free(ob, flavor='raw')

    def test_collect_p_dies(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        rawrefcount.create_link_pypy(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY_LIGHT
        assert rawrefcount._p_list == [ob]
        wr_ob = weakref.ref(ob)
        wr_p = weakref.ref(p)
        del ob, p
        rawrefcount._collect()
        assert rawrefcount._p_list == []
        assert wr_ob() is None
        assert wr_p() is None

    def test_collect_p_keepalive_pyobject(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        rawrefcount.create_link_pypy(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY_LIGHT
        assert rawrefcount._p_list == [ob]
        wr_ob = weakref.ref(ob)
        wr_p = weakref.ref(p)
        ob.c_ob_refcnt += 1      # <=
        del ob, p
        rawrefcount._collect()
        ob = wr_ob()
        p = wr_p()
        assert ob is not None and p is not None
        assert rawrefcount._p_list == [ob]
        assert rawrefcount.to_obj(W_Root, ob) == p
        assert rawrefcount.from_obj(PyObject, p) == ob
        lltype.free(ob, flavor='raw')

    def test_collect_p_keepalive_w_root(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        rawrefcount.create_link_pypy(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY_LIGHT
        assert rawrefcount._p_list == [ob]
        wr_ob = weakref.ref(ob)
        del ob       # p remains
        rawrefcount._collect()
        ob = wr_ob()
        assert ob is not None
        assert rawrefcount._p_list == [ob]
        assert rawrefcount.to_obj(W_Root, ob) == p
        assert rawrefcount.from_obj(PyObject, p) == ob
        lltype.free(ob, flavor='raw')

    def test_collect_o_dies(self):
        trigger = []; rawrefcount.init(lambda: trigger.append(1))
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        rawrefcount.create_link_pyobj(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount._o_list == [ob]
        wr_ob = weakref.ref(ob)
        wr_p = weakref.ref(p)
        del ob, p
        rawrefcount._collect()
        ob = wr_ob()
        assert ob is not None
        assert trigger == [1]
        assert rawrefcount.next_dead(PyObject) == ob
        assert rawrefcount.next_dead(PyObject) == lltype.nullptr(PyObjectS)
        assert rawrefcount.next_dead(PyObject) == lltype.nullptr(PyObjectS)
        assert rawrefcount._o_list == []
        assert wr_p() is None
        assert ob.c_ob_refcnt == 1       # from the pending list
        assert ob.c_ob_pypy_link == 0
        lltype.free(ob, flavor='raw')

    def test_collect_o_keepalive_pyobject(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        p.pyobj = ob
        rawrefcount.create_link_pyobj(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount._o_list == [ob]
        wr_ob = weakref.ref(ob)
        wr_p = weakref.ref(p)
        ob.c_ob_refcnt += 1      # <=
        del p
        rawrefcount._collect()
        p = wr_p()
        assert p is None            # was unlinked
        assert ob.c_ob_refcnt == 1    # != REFCNT_FROM_PYPY_OBJECT + 1
        assert rawrefcount._o_list == []
        assert rawrefcount.to_obj(W_Root, ob) == None
        lltype.free(ob, flavor='raw')

    def test_collect_o_keepalive_w_root(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        p.pyobj = ob
        rawrefcount.create_link_pyobj(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount._o_list == [ob]
        wr_ob = weakref.ref(ob)
        del ob       # p remains
        rawrefcount._collect()
        ob = wr_ob()
        assert ob is not None
        assert rawrefcount._o_list == [ob]
        assert rawrefcount.to_obj(W_Root, ob) == p
        assert p.pyobj == ob
        lltype.free(ob, flavor='raw')

    def test_collect_s_dies(self):
        trigger = []; rawrefcount.init(lambda: trigger.append(1))
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        rawrefcount.create_link_pypy(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount._p_list == [ob]
        wr_ob = weakref.ref(ob)
        wr_p = weakref.ref(p)
        del ob, p
        rawrefcount._collect()
        ob = wr_ob()
        assert ob is not None
        assert trigger == [1]
        assert rawrefcount._d_list == [ob]
        assert rawrefcount._p_list == []
        assert wr_p() is None
        assert ob.c_ob_refcnt == 1       # from _d_list
        assert ob.c_ob_pypy_link == 0
        lltype.free(ob, flavor='raw')

    def test_collect_s_keepalive_pyobject(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        p.pyobj = ob
        rawrefcount.create_link_pypy(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount._p_list == [ob]
        wr_ob = weakref.ref(ob)
        wr_p = weakref.ref(p)
        ob.c_ob_refcnt += 1      # <=
        del ob, p
        rawrefcount._collect()
        ob = wr_ob()
        p = wr_p()
        assert ob is not None and p is not None
        assert rawrefcount._p_list == [ob]
        assert rawrefcount.to_obj(W_Root, ob) == p
        lltype.free(ob, flavor='raw')

    def test_collect_s_keepalive_w_root(self):
        p = W_Root(42)
        ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
        p.pyobj = ob
        rawrefcount.create_link_pypy(p, ob)
        ob.c_ob_refcnt += REFCNT_FROM_PYPY
        assert rawrefcount._p_list == [ob]
        wr_ob = weakref.ref(ob)
        del ob       # p remains
        rawrefcount._collect()
        ob = wr_ob()
        assert ob is not None
        assert rawrefcount._p_list == [ob]
        assert rawrefcount.to_obj(W_Root, ob) == p
        lltype.free(ob, flavor='raw')


class TestTranslated(StandaloneTests):

    def test_full_translation(self):
        class State:
            pass
        state = State()
        state.seen = []
        def dealloc_trigger():
            state.seen.append(1)

        def make_p():
            p = W_Root(42)
            ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
            rawrefcount.create_link_pypy(p, ob)
            ob.c_ob_refcnt += REFCNT_FROM_PYPY
            assert rawrefcount.from_obj(PyObject, p) == ob
            assert rawrefcount.to_obj(W_Root, ob) == p
            return ob, p

        FTYPE = rawrefcount.RAWREFCOUNT_DEALLOC_TRIGGER

        def entry_point(argv):
            ll_dealloc_trigger_callback = llhelper(FTYPE, dealloc_trigger)
            rawrefcount.init(ll_dealloc_trigger_callback)
            ob, p = make_p()
            if state.seen != []:
                print "OB COLLECTED REALLY TOO SOON"
                return 1
            rgc.collect()
            if state.seen != []:
                print "OB COLLECTED TOO SOON"
                return 1
            objectmodel.keepalive_until_here(p)
            p = None
            rgc.collect()
            if state.seen != [1]:
                print "OB NOT COLLECTED"
                return 1
            if rawrefcount.next_dead(PyObject) != ob:
                print "NEXT_DEAD != OB"
                return 1
            if rawrefcount.next_dead(PyObject) != lltype.nullptr(PyObjectS):
                print "NEXT_DEAD second time != NULL"
                return 1
            print "OK!"
            lltype.free(ob, flavor='raw')
            return 0

        self.config = get_combined_translation_config(translating=True)
        self.config.translation.gc = "incminimark"
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        assert data.startswith('OK!\n')


class TestBoehmTranslated(StandaloneTests):

    def test_full_translation(self):

        def make_ob():
            p = W_Root(42)
            ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
            rawrefcount.create_link_pypy(p, ob)
            ob.c_ob_refcnt += REFCNT_FROM_PYPY
            assert rawrefcount.from_obj(PyObject, p) == ob
            assert rawrefcount.to_obj(W_Root, ob) == p
            return ob

        def entry_point(argv):
            oblist = [make_ob() for i in range(50)]
            rgc.collect()
            deadlist = []
            while True:
                ob = rawrefcount.next_dead(PyObject)
                if not ob: break
                deadlist.append(ob)
            if len(deadlist) == 0:
                print "no dead object"
                return 1
            if len(deadlist) < 30:
                print "not enough dead objects"
                return 1
            for ob in deadlist:
                if ob not in oblist:
                    print "unexpected value for dead pointer"
                    return 1
                oblist.remove(ob)
            print "OK!"
            lltype.free(ob, flavor='raw')
            return 0

        self.config = get_combined_translation_config(translating=True)
        self.config.translation.gc = "boehm"
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        assert data.startswith('OK!\n')
