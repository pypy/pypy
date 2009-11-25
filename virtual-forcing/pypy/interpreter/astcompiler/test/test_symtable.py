import string
import py
from pypy.interpreter.astcompiler import ast, astbuilder, symtable, consts
from pypy.interpreter.pyparser import pyparse
from pypy.interpreter.pyparser.error import SyntaxError


class TestSymbolTable:

    def setup_class(cls):
        cls.parser = pyparse.PythonParser(cls.space)

    def mod_scope(self, source, mode="exec"):
        info = pyparse.CompileInfo("<test>", mode,
                                   consts.CO_FUTURE_WITH_STATEMENT)
        tree = self.parser.parse_source(source, info)
        module = astbuilder.ast_from_node(self.space, tree, info)
        builder = symtable.SymtableBuilder(self.space, module, info)
        scope = builder.find_scope(module)
        assert isinstance(scope, symtable.ModuleScope)
        return scope

    def func_scope(self, func_code):
        mod_scope = self.mod_scope(func_code)
        assert len(mod_scope.children) == 1
        func_name = mod_scope.lookup("f")
        assert func_name == symtable.SCOPE_LOCAL
        func_scope = mod_scope.children[0]
        assert isinstance(func_scope, symtable.FunctionScope)
        return func_scope

    def class_scope(self, class_code):
        mod_scope = self.mod_scope(class_code)
        assert len(mod_scope.children) == 1
        class_name = mod_scope.lookup("x")
        assert class_name == symtable.SCOPE_LOCAL
        class_scope = mod_scope.children[0]
        assert isinstance(class_scope, symtable.ClassScope)
        return class_scope

    def gen_scope(self, gen_code):
        mod_scope = self.mod_scope(gen_code)
        assert len(mod_scope.children) == 1
        gen_scope = mod_scope.children[0]
        assert isinstance(gen_scope, symtable.FunctionScope)
        assert not gen_scope.children
        assert gen_scope.name == "genexp"
        return mod_scope, gen_scope

    def check_unknown(self, scp, *names):
        for name in names:
            assert scp.lookup(name) == symtable.SCOPE_UNKNOWN

    def test_toplevel(self):
        scp = self.mod_scope("x = 4")
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        assert not scp.locals_fully_known
        scp = self.mod_scope("x = 4", "single")
        assert not scp.locals_fully_known
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        scp = self.mod_scope("x*4*6", "eval")
        assert not scp.locals_fully_known
        assert scp.lookup("x") == symtable.SCOPE_GLOBAL_IMPLICIT

    def test_duplicate_argument(self):
        input = "def f(x, x): pass"
        exc = py.test.raises(SyntaxError, self.mod_scope, input).value
        assert exc.msg == "duplicate argument 'x' in function definition"

    def test_function_defaults(self):
        scp = self.mod_scope("y = 4\ndef f(x=y): return x")
        self.check_unknown(scp, "x")
        assert scp.lookup("y") == symtable.SCOPE_LOCAL
        scp = scp.children[0]
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        self.check_unknown(scp, "y")

    def test_genexp(self):
        scp, gscp = self.gen_scope("(y[1] for y in z)")
        assert scp.lookup("z") == symtable.SCOPE_GLOBAL_IMPLICIT
        self.check_unknown(scp, "y", "x")
        self.check_unknown(gscp, "z")
        assert gscp.lookup("y") == symtable.SCOPE_LOCAL
        scp, gscp = self.gen_scope("(x for x in z if x)")
        self.check_unknown(scp, "x")
        assert gscp.lookup("x") == symtable.SCOPE_LOCAL
        scp, gscp = self.gen_scope("(x for y in g for f in n if f[h])")
        self.check_unknown(scp, "f")
        assert gscp.lookup("f") == symtable.SCOPE_LOCAL

    def test_arguments(self):
        scp = self.func_scope("def f(): pass")
        assert not scp.children
        self.check_unknown(scp, "x", "y")
        assert not scp.symbols
        assert not scp.roles
        scp = self.func_scope("def f(x): pass")
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        scp = self.func_scope("def f(*x): pass")
        assert scp.has_variable_arg
        assert not scp.has_keywords_arg
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        scp = self.func_scope("def f(**x): pass")
        assert scp.has_keywords_arg
        assert not scp.has_variable_arg
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        scp = self.func_scope("def f((x, y), a): pass")
        for name in ("x", "y", "a"):
            assert scp.lookup(name) == symtable.SCOPE_LOCAL
        scp = self.func_scope("def f(((a, b), c)): pass")
        for name in ("a", "b", "c"):
            assert scp.lookup(name) == symtable.SCOPE_LOCAL

    def test_function(self):
        scp = self.func_scope("def f(): x = 4")
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        scp = self.func_scope("def f(): x")
        assert scp.lookup("x") == symtable.SCOPE_GLOBAL_IMPLICIT

    def test_nested_scopes(self):
        def nested_scope(*bodies):
            names = enumerate("f" + string.ascii_letters)
            lines = []
            for body, (level, name) in zip(bodies, names):
                lines.append(" " * level + "def %s():\n" % (name,))
                if body:
                    if isinstance(body, str):
                        body = [body]
                    lines.extend(" " * (level + 1) + line + "\n"
                                 for line in body)
            return self.func_scope("".join(lines))
        scp = nested_scope("x = 1", "return x")
        assert not scp.has_free
        assert scp.child_has_free
        assert scp.lookup("x") == symtable.SCOPE_CELL
        child = scp.children[0]
        assert child.has_free
        assert child.lookup("x") == symtable.SCOPE_FREE
        scp = nested_scope("x = 1", None, "return x")
        assert not scp.has_free
        assert scp.child_has_free
        assert scp.lookup("x") == symtable.SCOPE_CELL
        child = scp.children[0]
        assert not child.has_free
        assert child.child_has_free
        assert child.lookup("x") == symtable.SCOPE_FREE
        child = child.children[0]
        assert child.has_free
        assert not child.child_has_free
        assert child.lookup("x") == symtable.SCOPE_FREE
        scp = nested_scope("x = 1", "x = 3", "return x")
        assert scp.child_has_free
        assert not scp.has_free
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        child = scp.children[0]
        assert child.child_has_free
        assert not child.has_free
        assert child.lookup("x") == symtable.SCOPE_CELL
        child = child.children[0]
        assert child.has_free
        assert child.lookup("x") == symtable.SCOPE_FREE

    def test_class(self):
        scp = self.mod_scope("class x(A, B): pass")
        cscp = scp.children[0]
        for name in ("A", "B"):
            assert scp.lookup(name) == symtable.SCOPE_GLOBAL_IMPLICIT
            self.check_unknown(cscp, name)
        scp = self.func_scope("""def f(x):
    class X:
         def n():
              return x
         a = x
    return X()""")
        self.check_unknown(scp, "a")
        assert scp.lookup("x") == symtable.SCOPE_CELL
        assert scp.lookup("X") == symtable.SCOPE_LOCAL
        cscp = scp.children[0]
        assert cscp.lookup("a") == symtable.SCOPE_LOCAL
        assert cscp.lookup("x") == symtable.SCOPE_FREE
        fscp = cscp.children[0]
        assert fscp.lookup("x") == symtable.SCOPE_FREE
        self.check_unknown(fscp, "a")
        scp = self.func_scope("""def f(n):
    class X:
         def n():
             return y
         def x():
             return n""")
        assert scp.lookup("n") == symtable.SCOPE_CELL
        cscp = scp.children[0]
        assert cscp.lookup("n") == symtable.SCOPE_LOCAL
        assert "n" in cscp.free_vars
        xscp = cscp.children[1]
        assert xscp.lookup("n") == symtable.SCOPE_FREE

    def test_lambda(self):
        scp = self.mod_scope("lambda x: y")
        self.check_unknown(scp, "x", "y")
        assert len(scp.children) == 1
        lscp = scp.children[0]
        assert isinstance(lscp, symtable.FunctionScope)
        assert lscp.name == "lambda"
        assert lscp.lookup("x") == symtable.SCOPE_LOCAL
        assert lscp.lookup("y") == symtable.SCOPE_GLOBAL_IMPLICIT
        scp = self.mod_scope("lambda x=a: b")
        self.check_unknown(scp, "x", "b")
        assert scp.lookup("a") == symtable.SCOPE_GLOBAL_IMPLICIT
        lscp = scp.children[0]
        self.check_unknown(lscp, "a")

    def test_import(self):
        scp = self.mod_scope("import x")
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        scp = self.mod_scope("import x as y")
        assert scp.lookup("y") == symtable.SCOPE_LOCAL
        self.check_unknown(scp, "x")
        scp = self.mod_scope("import x.y")
        assert scp.lookup("x") == symtable.SCOPE_LOCAL
        self.check_unknown(scp, "y")

    def test_from_import(self):
        scp = self.mod_scope("from x import y")
        self.check_unknown("x")
        assert scp.lookup("y") == symtable.SCOPE_LOCAL
        scp = self.mod_scope("from a import b as y")
        assert scp.lookup("y") == symtable.SCOPE_LOCAL
        self.check_unknown(scp, "a", "b")
        scp = self.mod_scope("from x import *")
        self.check_unknown("x")
        scp = self.func_scope("def f(): from x import *")
        self.check_unknown(scp, "x")
        assert not scp.optimized
        assert scp.import_star

    def test_global(self):
        scp = self.func_scope("def f():\n   global x\n   x = 4")
        assert scp.lookup("x") == symtable.SCOPE_GLOBAL_EXPLICIT
        input = "def f(x):\n   global x"
        scp = self.func_scope("""def f():
    y = 3
    def x():
        global y
        y = 4
    def z():
        return y""")
        assert scp.lookup("y") == symtable.SCOPE_CELL
        xscp, zscp = scp.children
        assert xscp.lookup("y") == symtable.SCOPE_GLOBAL_EXPLICIT
        assert zscp.lookup("y") == symtable.SCOPE_FREE
        exc = py.test.raises(SyntaxError, self.func_scope, input).value
        assert exc.msg == "name 'x' is both local and global"

    def test_optimization(self):
        assert not self.mod_scope("").can_be_optimized
        assert not self.class_scope("class x: pass").can_be_optimized
        assert self.func_scope("def f(): pass").can_be_optimized

    def test_unoptimization_with_nested_scopes(self):
        table = (
            ("from x import *; exec 'hi'", "function 'f' uses import * " \
                 "and bare exec, which are illegal because it"),
            ("from x import *", "import * is not allowed in function 'f' " \
                 "because it"),
            ("exec 'hi'", "unqualified exec is not allowed in function 'f' " \
                 "because it")
         )
        for line, error in table:
            input = """def n():
    x = 4
    def f():
         %s
         return x""" % (line,)
            exc = py.test.raises(SyntaxError, self.mod_scope, input).value
            assert exc.msg == error + " is a nested function"
            input = """def f():
     %s
     x = 4
     def n():
         return x""" % (line,)
            exc = py.test.raises(SyntaxError, self.mod_scope, input).value
            assert exc.msg == error + " contains a nested function with free variables"
            input = """def f():
     %s
     x = 4
     class Y:
         def n():
             return x""" % (line,)
            exc = py.test.raises(SyntaxError, self.mod_scope, input).value
            assert exc.msg == error + " contains a nested function with free variables"

    def test_exec(self):
        self.mod_scope("exec 'hi'")
        scp = self.func_scope("def f(): exec 'hi'")
        assert not scp.optimized
        assert not scp.locals_fully_known
        assert isinstance(scp.bare_exec, ast.Exec)
        assert scp.has_exec
        for line in ("exec 'hi' in g", "exec 'hi' in g, h"):
            scp = self.func_scope("def f(): " + line)
            assert scp.optimized
            assert not scp.locals_fully_known
            assert scp.bare_exec is None
            assert scp.has_exec

    def test_yield(self):
        scp = self.func_scope("def f(): yield x")
        assert scp.is_generator
        for input in ("yield x", "class y: yield x"):
            exc = py.test.raises(SyntaxError, self.mod_scope, "yield x").value
            assert exc.msg == "'yield' outside function"
        for input in ("yield\n    return x", "return x\n    yield"):
            input = "def f():\n    " + input
            exc = py.test.raises(SyntaxError, self.func_scope, input).value
            assert exc.msg == "'return' with argument inside generator"
        scp = self.func_scope("def f():\n    return\n    yield x")

    def test_return(self):
        for input in ("class x: return", "return"):
            exc = py.test.raises(SyntaxError, self.func_scope, input).value
            assert exc.msg == "return outside function"

    def test_tmpnames(self):
        scp = self.mod_scope("[x for x in y]")
        assert scp.lookup("_[1]") == symtable.SCOPE_LOCAL
        scp = self.mod_scope("with x: pass")
        assert scp.lookup("_[1]") == symtable.SCOPE_LOCAL
        scp = self.mod_scope("with x as y: pass")
        assert scp.lookup("_[1]") == symtable.SCOPE_LOCAL
        assert scp.lookup("_[2]") == symtable.SCOPE_LOCAL
        # Just in case.
        scp = self.mod_scope("with [x for y in z]: pass")
        assert scp.lookup("_[1]") == symtable.SCOPE_LOCAL
        assert scp.lookup("_[2]") == symtable.SCOPE_LOCAL
