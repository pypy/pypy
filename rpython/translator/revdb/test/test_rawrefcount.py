from rpython.rlib import objectmodel, rgc, revdb
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.revdb.test.test_basic import InteractiveTests
from rpython.translator.revdb.test.test_basic import compile, fetch_rdb, run
from rpython.translator.revdb.message import *

from rpython.rlib import rawrefcount


class TestRawRefcount(InteractiveTests):
    expected_stop_points = 27

    def setup_class(cls):
        class W_Root(object):
            def __init__(self, n):
                self.n = n
        PyObjectS = lltype.Struct('PyObjectS',
                                  ('c_ob_refcnt', lltype.Signed),
                                  ('c_ob_pypy_link', lltype.Signed))
        PyObject = lltype.Ptr(PyObjectS)
        w1 = W_Root(-42)
        ob1 = lltype.malloc(PyObjectS, flavor='raw', zero=True,
                            immortal=True)
        ob1.c_ob_refcnt = rawrefcount.REFCNT_FROM_PYPY

        def main(argv):
            rawrefcount.create_link_pypy(w1, ob1)
            w = None
            ob = lltype.nullptr(PyObjectS)
            oblist = []
            for op in argv[1:]:
                revdb.stop_point()
                w = W_Root(42)
                ob = lltype.malloc(PyObjectS, flavor='raw', zero=True)
                ob.c_ob_refcnt = rawrefcount.REFCNT_FROM_PYPY
                rawrefcount.create_link_pypy(w, ob)
                oblist.append(ob)
            del oblist[-1]
            #
            rgc.collect()
            assert rawrefcount.from_obj(PyObject, w) == ob
            assert rawrefcount.to_obj(W_Root, ob) == w
            while True:
                ob = rawrefcount.next_dead(PyObject)
                if not ob:
                    break
                assert ob in oblist
                oblist.remove(ob)
            objectmodel.keepalive_until_here(w)
            revdb.stop_point()
            return 9
        compile(cls, main, backendopt=False)
        ARGS26 = 'a b c d e f g h i j k l m n o p q r s t u v w x y z'
        run(cls, ARGS26)
        rdb = fetch_rdb(cls, [cls.exename] + ARGS26.split())
        assert rdb.number_of_stop_points() == cls.expected_stop_points

    def test_go(self):
        child = self.replay()
        child.send(Message(CMD_FORWARD, 50))
        child.expect(ANSWER_AT_END)
