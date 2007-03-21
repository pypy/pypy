from pypy.conftest import gettestobjspace

class AppTest_Taint:

    def setup_class(cls):
        cls.space = gettestobjspace('taint')

    def test_simple(self):
        from __pypy__ import taint, untaint, TaintError
        x = taint(6)
        x = x * 7
        raises(TaintError, "if x: y = 1")
        t = type(x)
        raises(TaintError, "if t is int: y = 1")
        assert untaint(int, x) == 42
        raises(TaintError, "untaint(float, x)")

    def test_bomb(self):
        from __pypy__ import taint, untaint, TaintError
        x = taint(6)
        x = x / 0
        raises(TaintError, "if x: y = 1")
        t = type(x)
        raises(TaintError, "if t is int: y = 1")
        raises(TaintError, "untaint(int, x)")
        raises(TaintError, "untaint(float, x)")

    def test_taint_atomic(self):
        from __pypy__ import taint, untaint, TaintError, taint_atomic
        x = taint(6)
        x *= 7

        def dummy(x):
            if x > 40:
                return 5
            else:
                return 3
        dummy = taint_atomic(dummy)

        y = dummy(x)
        raises(TaintError, "if y == 3: z = 1")
        assert untaint(int, y) == 5

    def test_taint_atomic_exception(self):
        from __pypy__ import taint, untaint, TaintError, taint_atomic
        x = taint(6)
        x *= 7

        def dummy(x):
            if x + "world" == "hello world":
                return 5
            else:
                return 3
        dummy = taint_atomic(dummy)

        y = dummy(x)
        raises(TaintError, "if y == 3: z = 1")
        raises(TaintError, "untaint(int, y)")

    def test_taint_atomic_incoming_bomb(self):
        from __pypy__ import taint, untaint, TaintError, taint_atomic
        x = taint(6)
        x /= 0
        lst = []

        def dummy(x):
            lst.append("running!")
            if x > 40:
                return 5
            else:
                return 3
        dummy = taint_atomic(dummy)

        y = dummy(x)
        raises(TaintError, "if y == 3: z = 1")
        assert lst == []
        raises(TaintError, "untaint(int, y)")
