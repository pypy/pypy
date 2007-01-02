import py
from pypy.rlib.rctypes.rctypesobject import *
from pypy.rpython.test.test_llinterp import interpret, get_interpreter
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.policy import AnnotatorPolicy
from pypy.objspace.flow.model import mkentrymap


class TestBasic:

    def do(self, func):
        return func()

    def test_primitive(self):
        def func():
            x = rc_int.allocate()
            assert x.get_value() == 0
            x.set_value(17)
            return x.get_value()
        res = self.do(func)
        assert res == 17

    def test_ptr(self):
        def func():
            x = rc_int.allocate()
            p1 = pointer(x)
            p2 = pointer(x)
            x.set_value(17)
            assert p1.get_contents().get_value() == 17
            p2.get_contents().set_value(18)
            assert x.get_value() == 18
            del x
            return p1.get_contents().get_value()
        res = self.do(func)
        assert res == 18

    def test_struct(self):
        S1 = RStruct('S1', [('x', rc_int),
                            ('y', RPointer(rc_int))])
        def func():
            x = rc_int.allocate()
            x.set_value(42)
            s = S1.allocate()
            s.ref_x().set_value(12)
            s.ref_y().set_contents(x)
            assert s.ref_x().get_value() == 12
            return s.ref_y().get_contents().get_value()
        res = self.do(func)
        assert res == 42

    def test_copyfrom(self):
        def func():
            x1 = rc_int.allocate()
            x1.set_value(101)
            p1 = pointer(x1)
            x2 = rc_int.allocate()
            x2.set_value(202)
            p2 = pointer(x2)
            del x1, x2
            p1.copyfrom(p2)
            assert p1.get_contents().sameaddr(p2.get_contents())
            p1.get_contents().set_value(303)
            assert p2.get_contents().get_value() == 303
            del p2
            return p1.get_contents().get_value()
        res = self.do(func)
        assert res == 303

    def test_copyfrom_2(self):
        def func():
            x1 = rc_int.allocate()
            x1.set_value(11)
            x2 = rc_int.allocate()
            x2.set_value(7)
            p1 = pointer(x1)
            p1.get_contents().copyfrom(x2)
            return x1.get_value()
        res = self.do(func)
        assert res == 7

    def test_fixedarray(self):
        def func():
            a = RFixedArray(rc_int, 10).allocate()
            for i in range(10):
                a.ref(i).set_value(5 * i)
            for i in range(10):
                assert a.ref(i).get_value() == 5 * i
            return a.length
        res = self.do(func)
        assert res == 10

    def test_vararray(self):
        def func():
            a = RVarArray(rc_int).allocate(10)
            for i in range(10):
                a.ref(i).set_value(5 * i)
            for i in range(10):
                assert a.ref(i).get_value() == 5 * i
            return a.length
        res = self.do(func)
        assert res == 10

    def test_vararray_cast(self):
        def func():
            a = RVarArray(rc_int).allocate(10)
            for i in range(10):
                a.ref(i).set_value(100 + 5 * i)
            p = pointer(a.ref(0))
            del a
            assert p.get_contents().get_value() == 100
            a1 = RVarArray(rc_int).fromitem(p.get_contents(), 8)
            del p
            for i in range(8):
                assert a1.ref(i).get_value() == 100 + 5 * i
            return a1.length
        res = self.do(func)
        assert res == 8

    def test_varstructarray_cast(self):
        S1 = RStruct('S1', [('x', rc_int),
                            ('y', rc_int)])
        def func():
            a = RVarArray(S1).allocate(10)
            for i in range(10):
                a.ref(i).ref_x().set_value(100 + 5 * i)
                a.ref(i).ref_y().set_value(200 + 2 * i)
            p = pointer(a.ref(0))
            del a
            a1 = RVarArray(S1).fromitem(p.get_contents(), 8)
            del p
            return a1.ref(4).ref_y().get_value()
        res = self.do(func)
        assert res == 208

    def test_char_p(self):
        def func():
            p = rc_char_p.allocate()
            s = ''
            for i in range(65, 91):
                s += chr(i)
            p.set_value(s)
            del s
            s = p.get_value()
            for i in range(26):
                assert ord(s[i]) == 65 + i
            return len(s)
        res = self.do(func)
        assert res == 26

    def test_char_p_in_struct(self):
        S2 = RStruct('S2', [('p', rc_char_p)])
        def func():
            s = S2.allocate()
            for test in ["abc", "hello world"]:
                s.ref_p().set_value(test)
            assert s.ref_p().get_value() == "hello world"
            return 1
        res = self.do(func)
        assert res == 1

    def test_char_p_None(self):
        def func():
            p = rc_char_p.allocate()
            assert p.get_value() is None
            p.set_value("")
            assert p.get_value() == ""
            p.set_value("abc")
            assert p.get_value() == "abc"
            p.set_value(None)
            assert p.get_value() is None
        self.do(func)

    def test_char_array(self):
        def func():
            a = RFixedArray(rc_char, 10).allocate()
            for i in range(6):
                a.ref(i).set_value("hello!"[i])
            assert a.get_value() == "hello!"
            a.set_value("foo")
            assert a.get_value() == "foo"
            raw = ''.join([a.ref(i).get_value() for i in range(10)])
            assert raw == "foo\x00o!\x00\x00\x00\x00"
            assert raw == a.get_raw()
            a.set_value("0123456789")
            assert a.get_raw() == "0123456789"
            assert a.get_value() == "0123456789"
            assert a.get_substring(2, 5) == "23456"
            return 1
        res = self.do(func)
        assert res == 1

    def test_string_buffer(self):
        def func():
            a = create_string_buffer(10)
            for i in range(6):
                a.ref(i).set_value("hello!"[i])
            assert a.get_value() == "hello!"
            a.set_value("foo")
            assert a.get_value() == "foo"
            raw = ''.join([a.ref(i).get_value() for i in range(10)])
            assert raw == "foo\x00o!\x00\x00\x00\x00"
            assert raw == a.get_raw()
            a.set_value("0123456789")
            assert a.get_raw() == "0123456789"
            assert a.get_value() == "0123456789"
            assert a.get_substring(2, 5) == "23456"
            return 1
        res = self.do(func)
        assert res == 1

    def test_func(self):
        def g(x, y):
            return x - y
        def func():
            a = RFuncType((rc_int, rc_int), rc_int).fromrpython(g)
            return a.call(50, 8)
        res = self.do(func)
        assert res == 42

    def test_labs(self):
        def ll_labs(n):
            return abs(n)
        labs = RFuncType((rc_int,), rc_int).fromlib(LIBC, 'labs', ll_labs)
        def func():
            return labs.call(-7)
        res = self.do(func)
        assert res == 7

    def test_pointer_indexing(self):
        def func():
            a = RFixedArray(rc_int, 10).allocate()
            for i in range(10):
                a.ref(i).set_value(100 + 5 * i)
            p = pointer(a.ref(0))
            del a
            return p.ref(7).get_value()
        res = self.do(func)
        assert res == 135

    def test_structpointer_indexing(self):
        S1 = RStruct('S1', [('x', rc_int),
                            ('y', rc_int)])
        def func():
            a = RFixedArray(S1, 10).allocate()
            for i in range(10):
                a.ref(i).ref_x().set_value(100 + 5 * i)
                a.ref(i).ref_y().set_value(200 + 2 * i)
            p = pointer(a.ref(0))
            del a
            s1 = p.ref(3)
            return s1.ref_x().get_value() + s1.ref_y().get_value()
        res = self.do(func)
        assert res == 115 + 206

    def test_null_pointer(self):
        P = RPointer(rc_int)
        def func():
            x = rc_int.allocate()
            p = P.allocate()
            res1 = p.is_null()
            p.set_contents(x)
            res2 = p.is_null()
            p.set_null()
            res3 = p.is_null()
            return res1 * 100 + res2 * 10 + res3
        res = self.do(func)
        assert res == 101

POLICY = AnnotatorPolicy()
POLICY.allow_someobjects = False

class TestLLInterpreted(TestBasic):

    def do(self, func):
        return interpret(func, [], policy=POLICY, backendopt=True)

    def test_simple_struct(self):
        S0 = RStruct('S0', [('x', rc_int)])
        def func():
            s = S0.allocate()
            s.ref_x().set_value(12)
            return s.ref_x().get_value()

        interp, graph = get_interpreter(func, [], policy=POLICY,
                                        backendopt=True)
        res = interp.eval_graph(graph, [])
        assert res == 12
        # after inlining the get_value() call, there is a getarrayitem
        # at the end of the main graph.  However, the memory it accesses
        # must be protected by a following keepalive...
        entrymap = mkentrymap(graph)
        [link] = entrymap[graph.returnblock]
        assert link.prevblock.operations[-1].opname == 'keepalive'


class TestCompiled(TestBasic):

    def do(self, func):
        fn = compile(func, [], annotatorpolicy=POLICY)
        return fn()
