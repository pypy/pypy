from pypy.jit.tl.spli.serializer import serialize, deserialize
from pypy.jit.tl.spli import execution, pycode, objects

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

    def test_nested_code_objects(self):
        mod = """
def f(): return 1
f()"""
        data = serialize(compile(mod, "spli", "exec"))
        spli_code = deserialize(data)
        assert len(spli_code.co_consts_w) == 2
        assert isinstance(spli_code.co_consts_w[0], pycode.Code)
        assert spli_code.co_consts_w[0].co_consts_w[0] is objects.spli_None
        assert spli_code.co_consts_w[0].co_consts_w[1].as_int() == 1
