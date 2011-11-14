from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import app2interp
from pypy.conftest import gettestobjspace

class TestW_StdObjSpace:

    def test_wrap_wrap(self):
        raises(TypeError,
                          self.space.wrap,
                          self.space.wrap(0))

    def test_str_w_non_str(self):
        raises(OperationError,self.space.str_w,self.space.wrap(None))
        raises(OperationError,self.space.str_w,self.space.wrap(0))

    def test_int_w_non_int(self):
        raises(OperationError,self.space.int_w,self.space.wrap(None))
        raises(OperationError,self.space.int_w,self.space.wrap(""))

    def test_uint_w_non_int(self):
        raises(OperationError,self.space.uint_w,self.space.wrap(None))
        raises(OperationError,self.space.uint_w,self.space.wrap(""))

    def test_multimethods_defined_on(self):
        from pypy.objspace.std.stdtypedef import multimethods_defined_on
        from pypy.objspace.std.listobject import W_ListObject
        res = multimethods_defined_on(W_ListObject)
        res = [(m.name, local) for (m, local) in res]
        assert ('add', False) in res
        assert ('lt', False) in res
        assert ('setitem', False) in res
        assert ('mod', False) not in res
        assert ('pop', True) in res
        assert ('reverse', True) in res
        assert ('popitem', True) not in res

    def test_sliceindices(self):
        space = self.space
        w_obj = space.appexec([], """():
            class Stuff(object):
                def indices(self, l):
                    return 1,2,3
            return Stuff()
        """)
        w = space.wrap
        w_slice = space.newslice(w(1), w(2), w(1))
        assert space.sliceindices(w_slice, w(3)) == (1,2,1)
        assert space.sliceindices(w_obj, w(3)) == (1,2,3)

    def test_fastpath_isinstance(self):
        from pypy.objspace.std.stringobject import W_StringObject
        from pypy.objspace.std.intobject import W_IntObject
        from pypy.objspace.std.iterobject import W_AbstractSeqIterObject
        from pypy.objspace.std.iterobject import W_SeqIterObject

        space = self.space
        assert space._get_interplevel_cls(space.w_str) is W_StringObject
        assert space._get_interplevel_cls(space.w_int) is W_IntObject
        class X(W_StringObject):
            def __init__(self):
                pass

            typedef = None

        assert space.isinstance_w(X(), space.w_str)

        w_sequenceiterator = space.gettypefor(W_SeqIterObject)
        cls = space._get_interplevel_cls(w_sequenceiterator)
        assert cls is W_AbstractSeqIterObject

    def test_withstrbuf_fastpath_isinstance(self):
        from pypy.objspace.std.stringobject import W_AbstractStringObject

        space = gettestobjspace(withstrbuf=True)
        cls = space._get_interplevel_cls(space.w_str)
        assert cls is W_AbstractStringObject
