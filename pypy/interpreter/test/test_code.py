from pypy.conftest import gettestobjspace
from pypy.interpreter import gateway
import py

class AppTestCodeIntrospection:
    def setup_class(cls):
        space = gettestobjspace()
        cls.space = space
        filename = __file__
        if filename[-3:] != '.py':
            filename = filename[:-1]

        cls.w_file = space.wrap(filename)

    def test_attributes(self):
        def f(): pass
        def g(x, *y, **z): "docstring"
        assert hasattr(f.__code__, 'co_code')
        assert hasattr(g.__code__, 'co_code')

        testcases = [
            (f.__code__, {'co_name': 'f',
                           'co_names': (),
                           'co_varnames': (),
                           'co_argcount': 0,
                           'co_kwonlyargcount': 0,
                           'co_consts': (None,)
                           }),
            (g.__code__, {'co_name': 'g',
                           'co_names': (),
                           'co_varnames': ('x', 'y', 'z'),
                           'co_argcount': 1,
                           'co_kwonlyargcount': 0,
                           'co_consts': ("docstring", None),
                           }),
            ]

        import sys
        if hasattr(sys, 'pypy_objspaceclass'): 
            testcases += [
                (abs.__code__, {'co_name': 'abs',
                                 'co_varnames': ('val',),
                                 'co_argcount': 1,
                                 'co_flags': 0,
                                 'co_consts': ("abs(number) -> number\n\nReturn the absolute value of the argument.",),
                                 }),
                (object.__init__.__code__,
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

    def test_kwonlyargcount(self):
        """
        def f(*args, a, b, **kw): pass
        assert f.__code__.co_kwonlyargcount == 2
        """

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
        exec(src, d)

        assert list(sorted(d['f'].__code__.co_names)) == ['foo', 'g']

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
        exec(co, d)
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
        exec(co, d)
        assert d['c'] == 3
        def f(x):
            y = 1
        ccode = f.__code__
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
        exec("def f(): pass", d1)
        d2 = {}
        exec("def f(): pass", d2)
        assert d1['f'].__code__ == d2['f'].__code__
        assert hash(d1['f'].__code__) == hash(d2['f'].__code__)

    def test_repr(self):
        def f():
            xxx
        res = repr(f.__code__)
        expected = ["<code object f",
                    self.file,
                    'line']
        for i in expected:
            assert i in res

    def test_code_extra(self):
        d = {}
        exec("""if 1:
        def f():
            "docstring"
            'stuff'
            56
""", d)

        # check for new flag, CO_NOFREE
        assert d['f'].__code__.co_flags & 0x40

        exec("""if 1:
        def f(x):
            def g(y):
                return x+y
            return g
""", d)

        # CO_NESTED
        assert d['f'](4).__code__.co_flags & 0x10
        assert d['f'].__code__.co_flags & 0x10 == 0
        # check for CO_CONTAINSGLOBALS
        assert not d['f'].__code__.co_flags & 0x0800


        exec("""if 1:
        r = range
        def f():
            return [l for l in r(100)]
        def g():
            return [l for l in [1, 2, 3, 4]]
""", d)

        # check for CO_CONTAINSGLOBALS
        assert d['f'].__code__.co_flags & 0x0800
        assert not d['g'].__code__.co_flags & 0x0800

        exec("""if 1:
        b = 2
        def f(x):
            exec("a = 1")
            return a + b + x
""", d)
        # check for CO_CONTAINSGLOBALS
        assert d['f'].__code__.co_flags & 0x0800
