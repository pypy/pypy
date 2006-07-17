from pypy.translator.cli.test.runtest import CliTest

# used in tests below
class A:
    pass


class TestConstant(CliTest):
    def test_char(self):
        const = 'a'
        def fn():
            return const
        assert self.interpret(fn, []) == 'a'

    def test_void(self):
        def fn():
            pass
        assert self.interpret(fn, []) is None
        
    def test_tuple(self):
        const = 1, 2
        def fn():
            return const
        res = self.interpret(fn, [])
        assert res.item0 == 1
        assert res.item1 == 2

    def test_list(self):
        const = [1, 2]
        def fn():
            return const
        res = self.ll_to_list(self.interpret(fn, []))
        assert res == [1, 2]

    def test_compound_const(self):
        const = ([1, 2], [3, 4])
        def fn():
            return const
        res = self.interpret(fn, [])
        assert self.ll_to_list(res.item0) == [1, 2]
        assert self.ll_to_list(res.item1) == [3, 4]
        
    def test_instance(self):
        const = A()
        def fn():
            return const
        res = self.interpret(fn, [])
        assert self.class_name(res) == 'A'

    def test_list_of_instances(self):
        const = [A()]
        def fn():
            return const
        res = self.ll_to_list(self.interpret(fn, []))
        assert self.class_name(res[0]) == 'A'

    def test_mix_string_and_char(self):
        def fn(x):
            if x < 0:
                return 'a'
            else:
                return 'aa'
        assert self.ll_to_string(self.interpret(fn, [-1])) == 'a'
        assert self.ll_to_string(self.interpret(fn, [0])) == 'aa'

    def test_string_literal(self):
        def fn():
            return 'hello "world"'
        assert self.ll_to_string(self.interpret(fn, [])) == 'hello "world"'

    def test_string_literal2(self):
        s = '\001\002\003'
        def fn():
            return ord(s[0]) + ord(s[1])
        assert self.interpret(fn, []) == 3

    def test_float_special(self):
        inf = float("inf")
        nan = float("nan")
        def fn():
            return inf*2 == inf and not (nan == nan)
        assert self.interpret(fn, []) == True
