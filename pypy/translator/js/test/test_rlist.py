
import py
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.translator.js.test.runtest import JsTest

class Foo:
    pass

class Bar(Foo):
    pass

# ====> ../../../rpython/test/test_rlist.py

class TestJsList(JsTest, BaseTestRlist):
    def test_append(self):
        def dummyfn():
            l = []
            l.append(50)
            l.append(60)
            l.append(70)
            l.append(80)
            l.append(90)
            return len(l), l[0], l[-1]
        res = self.interpret(dummyfn, [])
        assert res == [5, 50, 90]

    def test_slice(self):
        py.test.skip("Imperfect testing machinery")
        def dummyfn():
            l = [5, 6, 7, 8, 9]
            return l[:2], l[1:4], l[3:]
        res = self.interpret(dummyfn, [])

        def dummyfn():
            l = [5, 6, 7, 8]
            l.append(9)
            return l[:2], l[1:4], l[3:]
        res = self.interpret(dummyfn, [])
        assert res == ([5, 6], [6, 7, 8], [8, 9])

    def test_setslice(self):
        def dummyfn():
            l = [10, 9, 8, 7]
            l[:2] = [6, 5]
            return l[0], l[1], l[2], l[3]
        res = self.interpret(dummyfn, ())
        assert res == [6, 5, 8, 7]

    def test_insert_bug(self):
        def dummyfn(n):
            l = [1]
            l = l[:]
            l.pop(0)
            if n < 0:
                l.insert(0, 42)
            else:
                l.insert(n, 42)
            return l
        res = self.interpret(dummyfn, [0])
        assert len(res) == 1
        assert res[0] == 42
        res = self.interpret(dummyfn, [-1])
        assert len(res) == 1
        assert res[0] == 42

    def test_list_str(self):
        pass

    def test_inst_list(self):
        def fn():
            l = [None]
            l[0] = Foo()
            l.append(Bar())
            l2 = [l[1], l[0], l[0]]
            l.extend(l2)
            for x in l2:
                l.append(x)
            x = l.pop()
            x = l.pop()
            x = l.pop()
            x = l2.pop()
            return str(x)+";"+str(l)
        res = self.ll_to_string(self.interpret(fn, []))
        res = res.replace('pypy.translator.js.test.test_rlist.', '')
        assert res == '<Foo object>;[<Foo object>, <Bar object>, <Bar object>, <Foo object>, <Foo object>]'
