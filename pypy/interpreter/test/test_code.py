from pypy.conftest import gettestobjspace
from pypy.interpreter import gateway
import py

class AppTestCodeIntrospection:
    def setup_class(cls):
        space = gettestobjspace()
        cls.space = space
        if py.test.config.option.runappdirect:
            filename = __file__
        else:
            filename = gateway.__file__

        if filename[-3:] != '.py':
            filename = filename[:-1]

        cls.w_file = space.wrap(filename)

    def test_attributes(self):
        def f(): pass
        def g(x, *y, **z): "docstring"
        assert hasattr(f.func_code, 'co_code')
        assert hasattr(g.func_code, 'co_code')

        testcases = [
            (f.func_code, {'co_name': 'f',
                           'co_names': (),
                           'co_varnames': (),
                           'co_argcount': 0,
                           'co_consts': (None,)
                           }),
            (g.func_code, {'co_name': 'g',
                           'co_names': (),
                           'co_varnames': ('x', 'y', 'z'),
                           'co_argcount': 1,
                           'co_consts': ("docstring", None),
                           }),
            ]

        import sys
        if hasattr(sys, 'pypy_objspaceclass'): 
            testcases += [
                (abs.func_code, {'co_name': 'abs',
                                 'co_varnames': ('val',),
                                 'co_argcount': 1,
                                 'co_flags': 0,
                                 'co_consts': ("abs(number) -> number\n\nReturn the absolute value of the argument.",),
                                 }),
                (object.__init__.im_func.func_code,
                                {#'co_name': '__init__',   XXX getting descr__init__
                                 'co_varnames': ('obj', 'args', 'keywords'),
                                 'co_argcount': 1,
                                 'co_flags': 0x000C,  # VARARGS|VARKEYWORDS
                                 }),
                ]

        # in PyPy, built-in functions have code objects
        # that emulate some attributes
        for code, expected in testcases:
            assert hasattr(code, '__class__')
            assert not hasattr(code,'__dict__')
            for key, value in expected.items():
                assert getattr(code, key) == value

    def test_co_names(self):
        src = '''if 1:
        def foo():
            pass

        g = 3

        def f(x, y):
            z = x + y
            foo(g)
'''
        d = {}
        exec src in d

        assert list(sorted(d['f'].func_code.co_names)) == ['foo', 'g']

    def test_code(self):
        import sys
        try: 
            import new
        except ImportError: 
            skip("could not import new module")
        codestr = "global c\na = 1\nb = 2\nc = a + b\n"
        ccode = compile(codestr, '<string>', 'exec')
        co = new.code(ccode.co_argcount,
                      ccode.co_nlocals,
                      ccode.co_stacksize,
                      ccode.co_flags,
                      ccode.co_code,
                      ccode.co_consts,
                      ccode.co_names,
                      ccode.co_varnames,
                      ccode.co_filename,
                      ccode.co_name,
                      ccode.co_firstlineno,
                      ccode.co_lnotab,
                      ccode.co_freevars,
                      ccode.co_cellvars)
        d = {}
        exec co in d
        assert d['c'] == 3
        # test backwards-compatibility version with no freevars or cellvars
        co = new.code(ccode.co_argcount,
                      ccode.co_nlocals,
                      ccode.co_stacksize,
                      ccode.co_flags,
                      ccode.co_code,
                      ccode.co_consts,
                      ccode.co_names,
                      ccode.co_varnames,
                      ccode.co_filename,
                      ccode.co_name,
                      ccode.co_firstlineno,
                      ccode.co_lnotab)
        d = {}
        exec co in d
        assert d['c'] == 3
        def f(x):
            y = 1
        ccode = f.func_code
        raises(ValueError, new.code,
              -ccode.co_argcount,
              ccode.co_nlocals,
              ccode.co_stacksize,
              ccode.co_flags,
              ccode.co_code,
              ccode.co_consts,
              ccode.co_names,
              ccode.co_varnames,
              ccode.co_filename,
              ccode.co_name,
              ccode.co_firstlineno,
              ccode.co_lnotab)
        raises(ValueError, new.code,
              ccode.co_argcount,
              -ccode.co_nlocals,
              ccode.co_stacksize,
              ccode.co_flags,
              ccode.co_code,
              ccode.co_consts,
              ccode.co_names,
              ccode.co_varnames,
              ccode.co_filename,
              ccode.co_name,
              ccode.co_firstlineno,
              ccode.co_lnotab)

    def test_hash(self):
        d1 = {}
        exec "def f(): pass" in d1
        d2 = {}
        exec "def f(): pass" in d2
        assert d1['f'].func_code == d2['f'].func_code
        assert hash(d1['f'].func_code) == hash(d2['f'].func_code)

    def test_repr(self):
        def f():
            xxx
        res = repr(f.func_code)
        expected = ["<code object f",
                    self.file,
                    'line']
        for i in expected:
            assert i in res

    def test_code_extra(self):
        exec """if 1:
        def f():
            "docstring"
            'stuff'
            56
"""

        # check for new flag, CO_NOFREE
        assert f.func_code.co_flags & 0x40

        exec """if 1:
        def f(x):
            def g(y):
                return x+y
            return g
"""

        # CO_NESTED
        assert f(4).func_code.co_flags & 0x10
        assert f.func_code.co_flags & 0x10 == 0
        # check for CO_CONTAINSLOOP
        assert not f.func_code.co_flags & 0x0080
        # check for CO_CONTAINSGLOBALS
        assert not f.func_code.co_flags & 0x0800


        exec """if 1:
        r = range
        def f():
            return [l for l in r(100)]
        def g():
            return [l for l in [1, 2, 3, 4]]
"""

        # check for CO_CONTAINSLOOP
        assert f.func_code.co_flags & 0x0080
        assert g.func_code.co_flags & 0x0080
        # check for CO_CONTAINSGLOBALS
        assert f.func_code.co_flags & 0x0800
        assert not g.func_code.co_flags & 0x0800

        exec """if 1:
        b = 2
        def f(x):
            exec "a = 1";
            return a + b + x
"""
        # check for CO_CONTAINSGLOBALS
        assert f.func_code.co_flags & 0x0800
