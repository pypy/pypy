
from pypy.rpython.extfunc import ExtFuncEntry, register_external,\
     is_external, lazy_register
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation.policy import AnnotatorPolicy
from pypy.rpython.test.test_llinterp import interpret

class TestExtFuncEntry:

    def test_basic(self):
        """
        A ExtFuncEntry provides an annotation for a function, no need to flow
        its graph.
        """
        def b(x):
            "NOT_RPYTHON"
            return eval("x+40")

        class BTestFuncEntry(ExtFuncEntry):
            _about_ = b
            name = 'b'
            signature_args = [annmodel.SomeInteger()]
            signature_result = annmodel.SomeInteger()

        def f():
            return b(2)

        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)

        res = interpret(f, [])
        assert res == 42

    def test_lltypeimpl(self):
        """
        interpret() calls lltypeimpl instead of of the function/
        """
        def c(y, x):
            yyy

        class CTestFuncEntry(ExtFuncEntry):
            _about_ = c
            name = 'ccc'
            signature_args = [annmodel.SomeInteger()] * 2
            signature_result = annmodel.SomeInteger()

            def lltypeimpl(y, x):
                return y + x
            lltypeimpl = staticmethod(lltypeimpl)

        def f():
            return c(3, 4)

        res = interpret(f, [])
        assert res == 7

    def test_callback(self):
        """
        Verify annotation when a callback function is in the arguments list.
        """
        def d(y):
            return eval("y()")

        class DTestFuncEntry(ExtFuncEntry):
            _about_ = d
            name = 'd'
            signature_args = [annmodel.SomeGenericCallable(args=[], result=
                                                           annmodel.SomeFloat())]
            signature_result = annmodel.SomeFloat()

        def callback():
            return 2.5

        def f():
            return d(callback)

        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeFloat)
        assert a.translator._graphof(callback)

    def test_register_external_signature(self):
        """
        Test the standard interface for external functions.
        """
        def dd():
            pass
        register_external(dd, [int], int)

        def f():
            return dd(3)

        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_register_external_tuple_args(self):
        """
        Verify the annotation of a registered external function which takes a
        tuple argument.
        """

        def function_with_tuple_arg():
            """
            Dummy function which is declared via register_external to take a
            tuple as an argument so that register_external's behavior for
            tuple-taking functions can be verified.
            """
        register_external(function_with_tuple_arg, [(int,)], int)

        def f():
            return function_with_tuple_arg((1,))

        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        s = a.build_types(f, [])

        # Not a very good assertion, but at least it means _something_ happened.
        assert isinstance(s, annmodel.SomeInteger)

    def test_register_external_return_goes_back(self):
        """
        Check whether it works to pass the same list from one external
        fun to another
        [bookkeeper and list joining issues]
        """
        def function_with_list():
            pass
        register_external(function_with_list, [[int]], int)

        def function_returning_list():
            pass
        register_external(function_returning_list, [], [int])

        def f():
            return function_with_list(function_returning_list())

        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_register_external_specialcase(self):
        """
        When args=None, the external function accepts any arguments unmodified.
        """
        def function_withspecialcase(arg):
            return repr(arg)
        register_external(function_withspecialcase, args=None, result=str)

        def f():
            x = function_withspecialcase
            return x(33) + x("aaa") + x([]) + "\n"

        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeString)

    def test_str0(self):
        str0 = annmodel.SomeString(no_nul=True)
        def os_open(s):
            pass
        register_external(os_open, [str0], None)
        def f(s):
            return os_open(s)
        policy = AnnotatorPolicy()
        policy.allow_someobjects = False
        a = RPythonAnnotator(policy=policy)
        a.build_types(f, [str])  # Does not raise
        assert a.translator.config.translation.check_str_without_nul == False
        # Now enable the str0 check, and try again with a similar function
        a.translator.config.translation.check_str_without_nul=True
        def g(s):
            return os_open(s)
        raises(Exception, a.build_types, g, [str])
        a.build_types(g, [str0])  # Does not raise

