import py

class AppTestAnnotations:

    def test_simple_annotation(self):
        # exec because this needs to be in "top level" scope
        # whereas the docstring-based tests are inside a function
        # (or don't care)
        exec("a: int; assert __annotations__['a'] == int")

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
        # this test exists to ensure that these type annotations
        # don't raise exceptions during compilation
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
            b: str = "s"
            assert "__annotations__" in locals()
        assert C.__annotations__ == {"a": int, "b": str}
        assert C.b == "s"
        '''

    def test_unevaluated_name(self):
        '''
        class C:
            def __init__(self):
                self.x: invalid_name = 1
                y[0]: also_invalid
                assert self.x == 1
        C()
        '''

    def test_function_no___annotations__(self):
        '''
        a: int
        assert "__annotations__" not in locals()
        '''

    def test_unboundlocal(self):
        # this test and the one below it are adapted from PEP 526
        '''
        a: int
        try:
            print(a)
        except UnboundLocalError:
            pass
        except:
            assert False
        '''

    def test_nameerror(self):
        # there's no annotation here, but it's present for contrast with
        # the test above
        '''
        try:
            print(a)
        except NameError:
            pass
        except:
            raise
        '''
