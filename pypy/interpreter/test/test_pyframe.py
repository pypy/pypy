import autopath


class AppTestPyFrame:

    # test for the presence of the attributes, not functionality

    def test_f_locals(self):
        import sys
        f = sys._getframe()
        assert f.f_locals is locals()

    def test_f_globals(self):
        import sys
        f = sys._getframe()
        assert f.f_globals is globals()

    def test_f_builtins(self):
        import sys, __builtin__
        f = sys._getframe()
        assert f.f_builtins is __builtin__.__dict__

    def test_f_code(self):
        def g():
            import sys
            f = sys._getframe()
            return f.f_code
        assert g() is g.func_code

    def test_f_lineno(self):
        def g():
            import sys
            f = sys._getframe()
            x = f.f_lineno
            y = f.f_lineno
            z = f.f_lineno
            return [x, y, z]
        origin = g.func_code.co_firstlineno
        assert g() == [origin+3, origin+4, origin+5]
