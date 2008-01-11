import py
from pypy.interpreter.astcompiler import misc, pycodegen, opt
from pypy.interpreter.pyparser.test.test_astbuilder import source2ast
from pypy.interpreter.pyparser.test import expressions
from pypy.interpreter.pycode import PyCode

def compile_with_astcompiler(expr, mode, space):
    ast = source2ast(expr, mode, space)
    misc.set_filename('<testing>', ast)
    ast = opt.optimize_ast_tree(space, ast)
    if mode == 'exec':
        Generator = pycodegen.ModuleCodeGenerator
    elif mode == 'single':
        Generator = pycodegen.InteractiveCodeGenerator
    elif mode == 'eval':
        Generator = pycodegen.ExpressionCodeGenerator
    codegen = Generator(space, ast)
    rcode = codegen.getCode()
    assert isinstance(rcode, PyCode)
    assert rcode.co_filename == '<testing>'
    return rcode


class TestCompiler:
    """These tests compile snippets of code and check them by
    running them with our own interpreter.  These are thus not
    completely *unit* tests, but given that our interpreter is
    pretty stable now it is the best way I could find to check
    the compiler.
    """

    def run(self, source):
        source = str(py.code.Source(source))
        space = self.space
        code = compile_with_astcompiler(source, 'exec', space)
        print
        code.dump()
        w_dict = space.newdict()
        code.exec_code(space, w_dict, w_dict)
        return w_dict

    def check(self, w_dict, evalexpr, expected):
        # for now, we compile evalexpr with CPython's compiler but run
        # it with our own interpreter to extract the data from w_dict
        co_expr = compile(evalexpr, '<evalexpr>', 'eval')
        space = self.space
        pyco_expr = PyCode._from_code(space, co_expr)
        w_res = pyco_expr.exec_code(space, w_dict, w_dict)
        res = space.str_w(space.repr(w_res))
        assert res == repr(expected)

    def simple_test(self, source, evalexpr, expected):
        w_g = self.run(source)
        self.check(w_g, evalexpr, expected)

    st = simple_test

    def test_argtuple(self):
        yield (self.simple_test, "def f( x, (y,z) ): return x,y,z",
               "f((1,2),(3,4))", ((1,2),3,4))
        yield (self.simple_test, "def f( x, (y,(z,t)) ): return x,y,z,t",
               "f(1,(2,(3,4)))", (1,2,3,4))
        yield (self.simple_test, "def f(((((x,),y),z),t),u): return x,y,z,t,u",
               "f(((((1,),2),3),4),5)", (1,2,3,4,5))

    def test_constants(self):
        for c in expressions.constants:
            yield (self.simple_test, "x="+c, "x", eval(c))

    def test_tuple_assign(self):
        yield self.simple_test, "x,= 1,", "x", 1
        yield self.simple_test, "x,y = 1,2", "x,y", (1, 2)
        yield self.simple_test, "x,y,z = 1,2,3", "x,y,z", (1, 2, 3)
        yield self.simple_test, "x,y,z,t = 1,2,3,4", "x,y,z,t", (1, 2, 3, 4)
        yield self.simple_test, "x,y,x,t = 1,2,3,4", "x,y,t", (3, 2, 4)
        yield self.simple_test, "[x]= 1,", "x", 1
        yield self.simple_test, "[x,y] = [1,2]", "x,y", (1, 2)
        yield self.simple_test, "[x,y,z] = 1,2,3", "x,y,z", (1, 2, 3)
        yield self.simple_test, "[x,y,z,t] = [1,2,3,4]", "x,y,z,t", (1, 2, 3,4)
        yield self.simple_test, "[x,y,x,t] = 1,2,3,4", "x,y,t", (3, 2, 4)

    def test_tuple_assign_order(self):
        decl = py.code.Source("""
            class A:
                def __getattr__(self, name):
                    global seen
                    seen += name
                    return name
                def __setattr__(self, name, value):
                    global seen
                    seen += '%s=%s' % (name, value)
            seen = ''
            a = A()
        """)
        decl = str(decl) + '\n'
        yield self.st, decl+"a.x,= a.a,", 'seen', 'ax=a'
        yield self.st, decl+"a.x,a.y = a.a,a.b", 'seen', 'abx=ay=b'
        yield self.st, decl+"a.x,a.y,a.z = a.a,a.b,a.c", 'seen', 'abcx=ay=bz=c'
        yield self.st, decl+"a.x,a.y,a.x,a.t = a.a,a.b,a.c,a.d", 'seen', \
            'abcdx=ay=bx=ct=d'
        yield self.st, decl+"[a.x] = [a.a]", 'seen', 'ax=a'
        yield self.st, decl+"[a.x,a.y] = a.a,a.b", 'seen', 'abx=ay=b'
        yield self.st, decl+"[a.x,a.y,a.z] = [a.a,a.b,a.c]", 'seen', \
            'abcx=ay=bz=c'
        yield self.st, decl+"[a.x,a.y,a.x,a.t] = a.a,a.b,a.c,a.d", 'seen', \
            'abcdx=ay=bx=ct=d'

    def test_binary_operator(self):
        for operator in ['+', '-', '*', '**', '/', '&', '|', '^', '//',
                         '<<', '>>', 'and', 'or', '<', '>', '<=', '>=',
                         'is', 'is not']:
            expected = eval("17 %s 5" % operator)
            yield self.simple_test, "x = 17 %s 5" % operator, "x", expected
            expected = eval("0 %s 11" % operator)
            yield self.simple_test, "x = 0 %s 11" % operator, "x", expected

    def test_augmented_assignment(self):
        for operator in ['+', '-', '*', '**', '/', '&', '|', '^', '//',
                         '<<', '>>']:
            expected = eval("17 %s 5" % operator)
            yield self.simple_test, "x = 17; x %s= 5" % operator, "x", expected

    def test_subscript(self):
        yield self.simple_test, "d={2:3}; x=d[2]", "x", 3
        yield self.simple_test, "d={(2,):3}; x=d[2,]", "x", 3
        yield self.simple_test, "d={}; d[1]=len(d); x=d[len(d)]", "x", 0
        yield self.simple_test, "d={}; d[1]=3; del d[1]", "len(d)", 0

    def test_attribute(self):
        yield self.simple_test, """
            class A:
                pass
            a1 = A()
            a2 = A()
            a1.bc = A()
            a1.bc.de = a2
            a2.see = 4
            a1.bc.de.see += 3
            x = a1.bc.de.see
        """, 'x', 7

    def test_slice(self):
        decl = py.code.Source("""
            class A(object):
                def __getitem__(self, x):
                    global got
                    got = x
                def __setitem__(self, x, y):
                    global set
                    set = x
                def __delitem__(self, x):
                    global deleted
                    deleted = x
            a = A()
        """)
        decl = str(decl) + '\n'
        testcases = ['[:]',    '[:,9]',    '[8,:]',
                     '[2:]',   '[2:,9]',   '[8,2:]',
                     '[:2]',   '[:2,9]',   '[8,:2]',
                     '[4:7]',  '[4:7,9]',  '[8,4:7]',
                     '[::]',   '[::,9]',   '[8,::]',
                     '[2::]',  '[2::,9]',  '[8,2::]',
                     '[:2:]',  '[:2:,9]',  '[8,:2:]',
                     '[4:7:]', '[4:7:,9]', '[8,4:7:]',
                     '[::3]',  '[::3,9]',  '[8,::3]',
                     '[2::3]', '[2::3,9]', '[8,2::3]',
                     '[:2:3]', '[:2:3,9]', '[8,:2:3]',
                     '[4:7:3]','[4:7:3,9]','[8,4:7:3]',
                     ]
        class Checker(object):
            def __getitem__(self, x):
                self.got = x
        checker = Checker()
        for testcase in testcases:
            exec "checker" + testcase
            yield self.st, decl + "a" + testcase, "got", checker.got
            yield self.st, decl + "a" + testcase + ' = 5', "set", checker.got
            yield self.st, decl + "del a" + testcase, "deleted", checker.got

    def test_funccalls(self):
        decl = py.code.Source("""
            def f(*args, **kwds):
                kwds = kwds.items()
                kwds.sort()
                return list(args) + kwds
        """)
        decl = str(decl) + '\n'
        yield self.st, decl + "x=f()", "x", []
        yield self.st, decl + "x=f(5)", "x", [5]
        yield self.st, decl + "x=f(5, 6, 7, 8)", "x", [5, 6, 7, 8]
        yield self.st, decl + "x=f(a=2, b=5)", "x", [('a',2), ('b',5)]
        yield self.st, decl + "x=f(5, b=2, *[6,7])", "x", [5, 6, 7, ('b', 2)]
        yield self.st, decl + "x=f(5, b=2, **{'a': 8})", "x", [5, ('a', 8),
                                                                  ('b', 2)]

    def test_listmakers(self):
        yield (self.st,
               "l = [(j, i) for j in range(10) for i in range(j)"
               + " if (i+j)%2 == 0 and i%3 == 0]",
               "l",
               [(2, 0), (4, 0), (5, 3), (6, 0),
                (7, 3), (8, 0), (8, 6), (9, 3)])

    def test_genexprs(self):
        yield (self.st,
               "l = list((j, i) for j in range(10) for i in range(j)"
               + " if (i+j)%2 == 0 and i%3 == 0)",
               "l",
               [(2, 0), (4, 0), (5, 3), (6, 0),
                (7, 3), (8, 0), (8, 6), (9, 3)])

    def test_comparisons(self):
        yield self.st, "x = 3 in {3: 5}", "x", True
        yield self.st, "x = 3 not in {3: 5}", "x", False
        yield self.st, "t = True; x = t is True", "x", True
        yield self.st, "t = True; x = t is False", "x", False
        yield self.st, "t = True; x = t is None", "x", False
        yield self.st, "n = None; x = n is True", "x", False
        yield self.st, "n = None; x = n is False", "x", False
        yield self.st, "n = None; x = n is None", "x", True
        yield self.st, "t = True; x = t is not True", "x", False
        yield self.st, "t = True; x = t is not False", "x", True
        yield self.st, "t = True; x = t is not None", "x", True
        yield self.st, "n = None; x = n is not True", "x", True
        yield self.st, "n = None; x = n is not False", "x", True
        yield self.st, "n = None; x = n is not None", "x", False

        yield self.st, "x = not (3 in {3: 5})", "x", False
        yield self.st, "x = not (3 not in {3: 5})", "x", True
        yield self.st, "t = True; x = not (t is True)", "x", False
        yield self.st, "t = True; x = not (t is False)", "x", True
        yield self.st, "t = True; x = not (t is None)", "x", True
        yield self.st, "n = None; x = not (n is True)", "x", True
        yield self.st, "n = None; x = not (n is False)", "x", True
        yield self.st, "n = None; x = not (n is None)", "x", False
        yield self.st, "t = True; x = not (t is not True)", "x", True
        yield self.st, "t = True; x = not (t is not False)", "x", False
        yield self.st, "t = True; x = not (t is not None)", "x", False
        yield self.st, "n = None; x = not (n is not True)", "x", False
        yield self.st, "n = None; x = not (n is not False)", "x", False
        yield self.st, "n = None; x = not (n is not None)", "x", True

    def test_multiexpr(self):
        yield self.st, "z = 2+3; x = y = z", "x,y,z", (5,5,5)

    def test_imports(self):
        import os
        yield self.st, "import sys", "sys.__name__", "sys"
        yield self.st, "import sys as y", "y.__name__", "sys"
        yield (self.st, "import sys, os",
               "sys.__name__, os.__name__", ("sys", "os"))
        yield (self.st, "import sys as x, os.path as y",
               "x.__name__, y.__name__", ("sys", os.path.__name__))
        yield self.st, 'import os.path', "os.path.__name__", os.path.__name__
        yield (self.st, 'import os.path, sys',
               "os.path.__name__, sys.__name__", (os.path.__name__, "sys"))
        yield (self.st, 'import sys, os.path as osp',
               "osp.__name__, sys.__name__", (os.path.__name__, "sys"))
        yield (self.st, 'import os.path as osp',
               "osp.__name__", os.path.__name__)
        yield (self.st, 'from os import path',
               "path.__name__", os.path.__name__)
        yield (self.st, 'from os import path, sep',
               "path.__name__, sep", (os.path.__name__, os.sep))
        yield (self.st, 'from os import path as p',
               "p.__name__", os.path.__name__)
        yield (self.st, 'from os import *',
               "path.__name__, sep", (os.path.__name__, os.sep))

    def test_if_stmts(self):
        yield self.st, "a = 42\nif a > 10: a += 2", "a", 44
        yield self.st, "a=5\nif 0: a=7", "a", 5
        yield self.st, "a=5\nif 1: a=7", "a", 7
        yield self.st, "a=5\nif a and not not (a<10): a=7", "a", 7
        yield self.st, """
            lst = []
            for a in range(10):
                if a < 3:
                    a += 20
                elif a > 3 and a < 8:
                    a += 30
                else:
                    a += 40
                lst.append(a)
            """, "lst", [20, 21, 22, 43, 34, 35, 36, 37, 48, 49]
        yield self.st, """
            lst = []
            for a in range(10):
                b = (a & 7) ^ 1
                if a or 1 or b: lst.append('A')
                if a or 0 or b: lst.append('B')
                if a and 1 and b: lst.append('C')
                if a and 0 and b: lst.append('D')
                if not (a or 1 or b): lst.append('-A')
                if not (a or 0 or b): lst.append('-B')
                if not (a and 1 and b): lst.append('-C')
                if not (a and 0 and b): lst.append('-D')
                if (not a) or (not 1) or (not b): lst.append('A')
                if (not a) or (not 0) or (not b): lst.append('B')
                if (not a) and (not 1) and (not b): lst.append('C')
                if (not a) and (not 0) and (not b): lst.append('D')
            """, "lst", ['A', 'B', '-C', '-D', 'A', 'B', 'A', 'B', '-C',
                         '-D', 'A', 'B', 'A', 'B', 'C', '-D', 'B', 'A', 'B',
                         'C', '-D', 'B', 'A', 'B', 'C', '-D', 'B', 'A', 'B',
                         'C', '-D', 'B', 'A', 'B', 'C', '-D', 'B', 'A', 'B',
                         'C', '-D', 'B', 'A', 'B', 'C', '-D', 'B', 'A', 'B',
                         '-C', '-D', 'A', 'B']

    def test_docstrings(self):
        for source, expected in [
            ('''def foo(): return 1''',      None),
            ('''class foo: pass''',          None),
            ('''class foo: "foo"''',         "foo"),
            ('''def foo():
                    """foo docstring"""
                    return 1
             ''',                            "foo docstring"),
            ('''def foo():
                    """foo docstring"""
                    a = 1
                    """bar"""
                    return a
             ''',                            "foo docstring"),
            ('''def foo():
                    """doc"""; print 1
                    a=1
             ''',                            "doc"),
            ('''
                class Foo(object): pass
                foo = Foo()
                exec "'moduledoc'" in foo.__dict__
             ''',                            "moduledoc"),
            ]:
            yield self.simple_test, source, "foo.__doc__", expected

    def test_in(self):
        yield self.st, "n = 5; x = n in [3,4,5]", 'x', True
        yield self.st, "n = 5; x = n in [3,4,6]", 'x', False
        yield self.st, "n = 5; x = n in [3,4,n]", 'x', True
        yield self.st, "n = 5; x = n in [3,4,n+1]", 'x', False
        yield self.st, "n = 5; x = n in (3,4,5)", 'x', True
        yield self.st, "n = 5; x = n in (3,4,6)", 'x', False
        yield self.st, "n = 5; x = n in (3,4,n)", 'x', True
        yield self.st, "n = 5; x = n in (3,4,n+1)", 'x', False

    def test_for_loops(self):
        yield self.st, """
            total = 0
            for i in [2, 7, 5]:
                total += i
        """, 'total', 2 + 7 + 5
        yield self.st, """
            total = 0
            for i in (2, 7, 5):
                total += i
        """, 'total', 2 + 7 + 5
        yield self.st, """
            total = 0
            for i in [2, 7, total+5]:
                total += i
        """, 'total', 2 + 7 + 5
        yield self.st, "x = sum([n+2 for n in [6, 1, 2]])", 'x', 15
        yield self.st, "x = sum([n+2 for n in (6, 1, 2)])", 'x', 15
        yield self.st, "k=2; x = sum([n+2 for n in [6, 1, k]])", 'x', 15
        yield self.st, "k=2; x = sum([n+2 for n in (6, 1, k)])", 'x', 15
        yield self.st, "x = sum(n+2 for n in [6, 1, 2])", 'x', 15
        yield self.st, "x = sum(n+2 for n in (6, 1, 2))", 'x', 15
        yield self.st, "k=2; x = sum(n+2 for n in [6, 1, k])", 'x', 15
        yield self.st, "k=2; x = sum(n+2 for n in (6, 1, k))", 'x', 15

    def test_closure(self):
        decl = py.code.Source("""
            def make_adder(n):
                def add(m):
                    return n + m
                return add
        """)
        decl = str(decl) + "\n"
        yield self.st, decl + "x = make_adder(40)(2)", 'x', 42

        decl = py.code.Source("""
            def f(a, g, e, c):
                def b(n, d):
                    return (a, c, d, g, n)
                def f(b, a):
                    return (a, b, c, g)
                return (a, g, e, c, b, f)
            A, G, E, C, B, F = f(6, 2, 8, 5)
            A1, C1, D1, G1, N1 = B(7, 3)
            A2, B2, C2, G2 = F(1, 4)
        """)
        decl = str(decl) + "\n"
        yield self.st, decl, 'A,A1,A2,B2,C,C1,C2,D1,E,G,G1,G2,N1', \
                             (6,6 ,4 ,1 ,5,5 ,5 ,3 ,8,2,2 ,2 ,7 )

        decl = py.code.Source("""
            def f((a, b)):
                def g((c, d)):
                    return (a, b, c, d)
                return g
            x = f((1, 2))((3, 4))
        """)
        decl = str(decl) + "\n"
        yield self.st, decl, 'x', (1, 2, 3, 4)

    def test_try_except_finally(self):
        yield self.simple_test, """
            try:
                x = 5
                try:
                    if x > 2:
                        raise ValueError
                finally:
                    x += 1
            except ValueError:
                x *= 7
        """, 'x', 42

    def test_while_loop(self):
        yield self.simple_test, """
            comments = [42]
            comment = '# foo'
            while comment[:1] == '#':
                comments[:0] = [comment]
                comment = ''
        """, 'comments', ['# foo', 42]

    def test_return_lineno(self):
        # the point of this test is to check that there is no code associated
        # with any line greater than 4.  The implicit return should not have
        # any line number - otherwise it would probably show up at line 5,
        # which is confusing because it's in the wrong branch of the "if"
        # in the case where a == b.
        yield self.simple_test, """\
            def ireturn_example():    # line 1
                global b              # line 2
                if a == b:            # line 3
                    b = a+1           # line 4
                else:                 # line 5
                    if 1: pass        # line 6
            import dis
            co = ireturn_example.func_code
            x = [lineno for addr, lineno in dis.findlinestarts(co)]
        """, 'x', [3, 4]

    def test_pprint(self):
        # a larger example that showed a bug with jumps
        # over more than 256 bytes
        decl = py.code.Source("""
            def _safe_repr(object, context, maxlevels, level):
                typ = type(object)
                if typ is str:
                    if 'locale' not in _sys.modules:
                        return repr(object), True, False
                    if "'" in object and '"' not in object:
                        closure = '"'
                        quotes = {'"': '\\"'}
                    else:
                        closure = "'"
                        quotes = {"'": "\\'"}
                    qget = quotes.get
                    sio = _StringIO()
                    write = sio.write
                    for char in object:
                        if char.isalpha():
                            write(char)
                        else:
                            write(qget(char, repr(char)[1:-1]))
                    return ("%s%s%s" % (closure, sio.getvalue(), closure)), True, False

                r = getattr(typ, "__repr__", None)
                if issubclass(typ, dict) and r is dict.__repr__:
                    if not object:
                        return "{}", True, False
                    objid = id(object)
                    if maxlevels and level > maxlevels:
                        return "{...}", False, objid in context
                    if objid in context:
                        return _recursion(object), False, True
                    context[objid] = 1
                    readable = True
                    recursive = False
                    components = []
                    append = components.append
                    level += 1
                    saferepr = _safe_repr
                    for k, v in object.iteritems():
                        krepr, kreadable, krecur = saferepr(k, context, maxlevels, level)
                        vrepr, vreadable, vrecur = saferepr(v, context, maxlevels, level)
                        append("%s: %s" % (krepr, vrepr))
                        readable = readable and kreadable and vreadable
                        if krecur or vrecur:
                            recursive = True
                    del context[objid]
                    return "{%s}" % ', '.join(components), readable, recursive

                if (issubclass(typ, list) and r is list.__repr__) or \
                   (issubclass(typ, tuple) and r is tuple.__repr__):
                    if issubclass(typ, list):
                        if not object:
                            return "[]", True, False
                        format = "[%s]"
                    elif _len(object) == 1:
                        format = "(%s,)"
                    else:
                        if not object:
                            return "()", True, False
                        format = "(%s)"
                    objid = id(object)
                    if maxlevels and level > maxlevels:
                        return format % "...", False, objid in context
                    if objid in context:
                        return _recursion(object), False, True
                    context[objid] = 1
                    readable = True
                    recursive = False
                    components = []
                    append = components.append
                    level += 1
                    for o in object:
                        orepr, oreadable, orecur = _safe_repr(o, context, maxlevels, level)
                        append(orepr)
                        if not oreadable:
                            readable = False
                        if orecur:
                            recursive = True
                    del context[objid]
                    return format % ', '.join(components), readable, recursive

                rep = repr(object)
                return rep, (rep and not rep.startswith('<')), False
        """)
        decl = str(decl) + '\n'
        g = {}
        exec decl in g
        expected = g['_safe_repr']([5], {}, 3, 0)
        yield self.st, decl + 'x=_safe_repr([5], {}, 3, 0)', 'x', expected

    def test_mapping_test(self):
        decl = py.code.Source("""
            class X(object):
                reference = {1:2, "key1":"value1", "key2":(1,2,3)}
                key, value = reference.popitem()
                other = {key:value}
                key, value = reference.popitem()
                inmapping = {key:value}
                reference[key] = value
                def _empty_mapping(self):
                    return {}
                _full_mapping = dict
                def assertEqual(self, x, y):
                    assert x == y
                failUnlessRaises = staticmethod(raises)
                def assert_(self, x):
                    assert x
                def failIf(self, x):
                    assert not x

            def test_read(self):
                # Test for read only operations on mapping
                p = self._empty_mapping()
                p1 = dict(p) #workaround for singleton objects
                d = self._full_mapping(self.reference)
                if d is p:
                    p = p1
                #Indexing
                for key, value in self.reference.items():
                    self.assertEqual(d[key], value)
                knownkey = self.other.keys()[0]
                self.failUnlessRaises(KeyError, lambda:d[knownkey])
                #len
                self.assertEqual(len(p), 0)
                self.assertEqual(len(d), len(self.reference))
                #has_key
                for k in self.reference:
                    self.assert_(d.has_key(k))
                    self.assert_(k in d)
                for k in self.other:
                    self.failIf(d.has_key(k))
                    self.failIf(k in d)
                #cmp
                self.assertEqual(cmp(p,p), 0)
                self.assertEqual(cmp(d,d), 0)
                self.assertEqual(cmp(p,d), -1)
                self.assertEqual(cmp(d,p), 1)
                #__non__zero__
                if p: self.fail("Empty mapping must compare to False")
                if not d: self.fail("Full mapping must compare to True")
                # keys(), items(), iterkeys() ...
                def check_iterandlist(iter, lst, ref):
                    self.assert_(hasattr(iter, 'next'))
                    self.assert_(hasattr(iter, '__iter__'))
                    x = list(iter)
                    self.assert_(set(x)==set(lst)==set(ref))
                check_iterandlist(d.iterkeys(), d.keys(), self.reference.keys())
                check_iterandlist(iter(d), d.keys(), self.reference.keys())
                check_iterandlist(d.itervalues(), d.values(), self.reference.values())
                check_iterandlist(d.iteritems(), d.items(), self.reference.items())
                #get
                key, value = d.iteritems().next()
                knownkey, knownvalue = self.other.iteritems().next()
                self.assertEqual(d.get(key, knownvalue), value)
                self.assertEqual(d.get(knownkey, knownvalue), knownvalue)
                self.failIf(knownkey in d)
                return 42
        """)
        decl = str(decl) + '\n'
        yield self.simple_test, decl + 'r = test_read(X())', 'r', 42
