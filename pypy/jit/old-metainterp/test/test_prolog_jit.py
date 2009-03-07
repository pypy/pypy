import py
py.test.skip("in-progress")
from pyjitpl import get_stats
from test.test_basic import OOJitMixin, LLJitMixin
from pypy.rlib.jit import JitDriver, hint
from pypy.lang.prolog.interpreter import portal, term
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine
from pypy.lang.prolog.interpreter.engine import Engine

POLICY = portal.PyrologHintAnnotatorPolicy()


class PrologLanguageTests:

    def setup_class(cls):
        del Engine._virtualizable_
        Engine._virtualizable2_ = True

    def teardown_class(cls):
        del Engine._virtualizable2_
        Engine._virtualizable_ = True

    def test_jit_append(self):
        e = get_engine("""
            append([], L, L).
            append([X|Y], L, [X|Z]) :- append(Y, L, Z).
            foo(X) :- append([a, b, c, aa, bb, cc], [d, f, g], X).
        """)

        def main():
            X = term.Var()
            e.call(term.Term("foo", [X]))
            return isinstance(X.dereference(e), term.Term)

        res = main()
        assert res == True

        e.reset()
        res = self.meta_interp(main, [], policy=POLICY)
        assert res == True


##class TestOOtype(PrologLanguageTests, OOJitMixin):
##    pass

class TestLLtype(PrologLanguageTests, LLJitMixin):
    pass
