from pypy.module.pypyjit.test_pypy_c.model import Log

class TestLog(object):

    def test_find_chunks_range(self):
        def f():
            a = 0 # ID: myline
            return a
        #
        start_lineno = f.func_code.co_firstlineno
        ids = Log.find_chunks_range(f)
        assert len(ids) == 1
        myline_range = ids['myline']
        assert list(myline_range) == range(start_lineno+1, start_lineno+2)

    def test_find_chunks(self):
        def f():
            i = 0
            x = 0
            z = x + 3 # ID: myline
            return z
        #
        chunks = Log.find_chunks(f)
        assert len(chunks) == 1
        myline = chunks['myline']
        opcodes_names = [opcode.__class__.__name__ for opcode in myline]
        assert opcodes_names == ['LOAD_FAST', 'LOAD_CONST', 'BINARY_ADD', 'STORE_FAST']
