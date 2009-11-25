
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.tl.spli import execution, objects
from pypy.jit.tl.spli.serializer import serialize, deserialize

class TestSPLITranslated(object):

    def test_one(self):
        def f(a, b):
            return a + b
        data = serialize(f.func_code)
        space = objects.DumbObjSpace()
        def run(a, b):
            co = deserialize(data)
            args = []
            args.append(space.wrap(a))
            args.append(space.wrap(b))
            w_res = execution.run(co, args)
            assert isinstance(w_res, objects.Int)
            return w_res.value

        assert run(2, 3) == 5
        res = interpret(run, [2, 3])
        assert res == 5
