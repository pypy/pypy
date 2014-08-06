class AppTestCompile:

    def test_compile(self):
        """Clone of the part of the original test that was failing."""
        import ast

        codestr = '''def f():
        """doc"""
        try:
            assert False
        except AssertionError:
            return (True, f.__doc__)
        else:
            return (False, f.__doc__)
        '''

        def f(): """doc"""
        values = [(-1, __debug__, f.__doc__),
                  (0, True, 'doc'),
                  (1, False, 'doc'),
                  (2, False, None)]

        for optval, debugval, docstring in values:
            # test both direct compilation and compilation via AST
            codeobjs = []
            codeobjs.append(
                    compile(codestr, "<test>", "exec", optimize=optval))
            tree = ast.parse(codestr)
            codeobjs.append(compile(tree, "<test>", "exec", optimize=optval))

            for i, code in enumerate(codeobjs):
                print(optval, debugval, docstring, i)
                ns = {}
                exec(code, ns)
                rv = ns['f']()
                assert rv == (debugval, docstring)

    def test_assert_remove(self):
        """Test removal of the asserts with optimize=1."""
        import ast

        code = """def f():
        assert False
        """
        tree = ast.parse(code)
        for to_compile in [code, tree]:
            compiled = compile(to_compile, "<test>", "exec", optimize=1)
            ns = {}
            exec(compiled, ns)
            ns['f']()

    def test_docstring_remove(self):
        """Test removal of docstrings with optimize=2."""
        import ast
        import marshal

        code = """
'module_doc'

def f():
    'func_doc'

class C:
    'class_doc'
"""
        tree = ast.parse(code)
        for to_compile in [code, tree]:
            compiled = compile(to_compile, "<test>", "exec", optimize=2)

            ns = {}
            exec(compiled, ns)
            assert '__doc__' not in ns
            assert ns['f'].__doc__ is None
            assert ns['C'].__doc__ is None

            # Check that the docstrings are gone from the bytecode and not just
            # inaccessible.
            marshalled = str(marshal.dumps(compiled))
            assert 'module_doc' not in marshalled
            assert 'func_doc' not in marshalled
            assert 'class_doc' not in marshalled


class TestOptimizeO:
    """Test interaction of -O flag and optimize parameter of compile."""

    def setup_method(self, method):
        space = self.space
        self._sys_debug = space.sys.debug
        # imitate -O
        space.sys.debug = False

    def teardown_method(self, method):
        self.space.sys.debug = self._sys_debug

    def test_O_optmize_0(self):
        """Test that assert is not ignored if -O flag is set but optimize=0."""
        space = self.space
        w_res = space.appexec([], """():
            assert False  # check that our -O imitation hack works
            try:
                exec(compile('assert False', '', 'exec', optimize=0))
            except AssertionError:
                return True
            else:
                return False
        """)
        assert space.unwrap(w_res)

    def test_O_optimize__1(self):
        """Test that assert is ignored with -O and optimize=-1."""
        space = self.space
        space.appexec([], """():
            exec(compile('assert False', '', 'exec', optimize=-1))
        """)


# TODO: Check the value of __debug__ inside of the compiled block!
#       According to the documentation, it should follow the optimize flag.
#       However, cpython3.5.0a0 behaves the same way as PyPy (__debug__ follows
#       -O, -OO flags of the interpreter).
