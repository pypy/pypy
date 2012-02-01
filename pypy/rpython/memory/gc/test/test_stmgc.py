from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gc.stmgc import StmGC


class FakeStmOperations:
    def set_tls(self, tls):
        assert lltype.typeOf(tls) == llmemory.Address
        self._tls = tls

    def get_tls(self):
        return self._tls


class TestBasic:
    GCClass = StmGC

    def setup_method(self, meth):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True).translation
        self.gc = self.GCClass(config, FakeStmOperations(),
                               translated_to_c=False)
        self.gc.DEBUG = True
        self.gc.setup()

    def test_gc_creation_works(self):
        pass

    def test_allocate_bump_pointer(self):
        a3 = self.gc.allocate_bump_pointer(3)
        a4 = self.gc.allocate_bump_pointer(4)
        a5 = self.gc.allocate_bump_pointer(5)
        a6 = self.gc.allocate_bump_pointer(6)
        assert a4 - a3 == 3
        assert a5 - a4 == 4
        assert a6 - a5 == 5
