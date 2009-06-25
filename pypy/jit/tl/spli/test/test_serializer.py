
from pypy.jit.tl.spli.serializer import serialize, deserialize
from pypy.jit.tl.spli import execution

class TestSerializer(object):

    def eval(self, code, args=[]):
        return execution.run(code, args)
    
    def test_basic(self):
        def f():
            return 1

        coderepr = serialize(f.func_code)
        code = deserialize(coderepr)
        assert code.co_nlocals == f.func_code.co_nlocals
        assert code.co_argcount == 0
        assert code.co_stacksize == f.func_code.co_stacksize
        assert code.co_names == []
        assert self.eval(code).value == 1
        
