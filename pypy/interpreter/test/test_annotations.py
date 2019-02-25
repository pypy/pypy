class AppTestAnnotations:

    def test_toplevel_annotation(self):
        # exec because this needs to be in "top level" scope
        # whereas the docstring-based tests are inside a function
        # (or don't care)
        exec("a: int; assert __annotations__['a'] == int")

    def test_toplevel_invalid(self):
        exec('try: a: invalid\nexcept NameError: pass\n')

    def test_non_simple_annotation(self):
        '''
        class C:
            (a): int
            assert "a" not in __annotations__
        '''

    def test_simple_with_target(self):
        '''
        class C:
            a: int = 1
            assert __annotations__["a"] == int
            assert a == 1
        '''

    def test_attribute_target(self):
        '''
        class C:
            a = 1
            a.x: int
            assert __annotations__ == {}
        '''

    def test_subscript_target(self):
        '''
        # ensure that these type annotations don't raise exceptions
        # during compilation
        class C:
            a = 1
            a[0]: int
            a[1:2]: int
            a[1:2:2]: int
            a[1:2:2,...]: int
            assert __annotations__ == {}
        '''

    def test_class_annotation(self):
        '''
        class C:
            a: int
            b: str
            assert "__annotations__" in locals()
        assert C.__annotations__ == {"a": int, "b": str}
        '''

    def test_unevaluated_name(self):
        '''
        class C:
            def __init__(self):
                self.x: invalid_name = 1
                assert self.x == 1
        C()
        '''

    def test_nonexistent_target(self):
        '''
        try:
            # this is invalid because `y` is undefined
            # it should raise a NameError
            y[0]: invalid
        except NameError:
            ...
        '''

    def test_non_simple_func_annotation(self):
        '''
        a = 5
        def f():
            (a): int
            return a
        assert f() == 5
        '''

    def test_repeated_setup(self):
        # each exec will run another SETUP_ANNOTATIONS
        # we want to confirm that this doesn't blow away
        # the previous __annotations__
        d = {}
        exec('a: int', d)
        exec('b: int', d)
        exec('assert __annotations__ == {"a": int, "b": int}', d)

    def test_function_no___annotations__(self):
        '''
        a: int
        assert "__annotations__" not in locals()
        '''

    def test_unboundlocal(self):
        # a simple variable annotation implies its target is a local
        '''
        a: int
        try:
            print(a)
        except UnboundLocalError:
            return
        assert False
        '''

    def test_ternary_expression_bug(self):
        """
        class C:
            var: bool = True if False else False
            assert var is False
        assert C.__annotations__ == {"var": bool}
        """

    def test_reassigned___annotations__(self):
        '''
        class C:
            __annotations__ = None
            try:
                a: int
                raise
            except TypeError:
                pass
            except:
                assert False
        '''

    def test_locals_arent_dicts(self):
        class O:
            def __init__(self):
                self.dct = {}
            def __getitem__(self, name):
                return self.dct[name]
            def __setitem__(self, name, value):
                self.dct[name] = value
        # don't crash if locals aren't just a normal dict
        exec("a: int; assert __annotations__['a'] == int", {}, O())

    def test_NameError_if_annotations_are_gone(self):
        exec("""if 1:
            raises(NameError, '''if 1:
                class A:
                    del __annotations__
                    a: int
            ''')
        """)

    def test_lineno(self):
        s = """

a: int
        """
        c = compile(s, "f", "exec")
        assert c.co_firstlineno == 3

    def test_scoping(self):
        exec("""if 1:
            def f(classvar):
                class C:
                    cls: classvar = 23
                assert C.__annotations__ == {"cls": "abc"}

            f("abc")
        """)
