class AppTestCompile:

    # TODO: This test still fails for now because the docstrings are not
    #       removed with optimize=2.
    def untest_compile(self):
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
        """Test just removal of the asserts with optimize=1."""
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


# TODO: Remove docstrings with optimize=2.
# TODO: Check the value of __debug__ inside of the compiled block!
#       According to the documentation, it should follow the optimize flag.
# TODO: It would also be good to test that with the assert is not removed and
#       is executed when -O flag is set but optimize=0.
