import pytest

class AppTestObjects(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_var(self):
        import unipycation as upy

        X = upy.Var()
        assert str(X) == "_G0"

    def test_list(self):
        import unipycation as u

        e = u.CoreEngine("f([w, x]).")
        X = u.Var()
        t = u.CoreTerm("f", [X])
        x_val = e.query_single(t, [X])[X]

        assert x_val.name == "."
        assert x_val.args[0] == "w"
        assert x_val.args[1].name == "."
        assert x_val.args[1].args[0] == "x"
        assert x_val.args[1].args[1] == "[]"

    def test_functor(self):
        import unipycation as u

        e = u.CoreEngine("f(g(a, b, c, d)).")
        X = u.Var()

        t = u.CoreTerm("f", [X])
        x_val = e.query_single(t, [X])[X]

        assert len(x_val) == 4 and \
                x_val[0] == "a" and \
                x_val[1] == "b" and \
                x_val[2] == "c" and \
                x_val[3] == "d"

    def test_term_builder(self):
        import unipycation

        t = unipycation.CoreTerm("myterm", ["e1", "e2", "e3"])
        elems = [ t[x] for x in range(len(t)) ]

        assert elems == ["e1", "e2", "e3" ]

    def test_term_builder_wrong_arguments(self):
        import unipycation

        raises(TypeError, unipycation.CoreTerm, "myterm", a=1)
        raises(TypeError, unipycation.CoreTerm, "myterm", 1, 2, 3)

    def test_nest_term_builder(self):
        import unipycation

        def nest_many(count):
            if count < 10:
                return unipycation.CoreTerm("myterm", [count, nest_many(count + 1)])
            else:
                return 666

        def unnest_many(term, count):
            assert len(term) == 2
            assert term[0] == count
            if isinstance(term[1], unipycation.CoreTerm):
                assert term.name == "myterm"
                assert term[1].name == "myterm"
                unnest_many(term[1], count + 1)
            else:
                assert 9 == count
                assert term[1] == 666

        top = nest_many(0)
        unnest_many(top, 0)

    def test_term_str(self):
        import unipycation as u
        t = u.CoreTerm("x", [1,2,666])
        assert str(t) == "x(1, 2, 666)"

    def test_term_str_with_var(self):
        import unipycation as u
        vs = [X, Y, Z] = [ u.Var() for i in range(3) ]
        t = u.CoreTerm("x", vs)
        assert str(t) == ("x(_G0, _G1, _G2)")

    def test_nested_term_str(self):
        import unipycation as u
        t2 = u.CoreTerm("y", ["blah", "123", "bobbins"])
        t = u.CoreTerm("x", [1, 2, t2])
        assert str(t) == "x(1, 2, y(blah, 123, bobbins))"

    def test_term_repr(self):
        import unipycation as u
        t = u.CoreTerm("x", [1,2,666])
        assert repr(t) == "CoreTerm('x', [1, 2, 666])"

    def test_nested_term_repr(self):
        import unipycation as u
        t2 = u.CoreTerm("y", ["blah", "123", "bobbins"])
        t = u.CoreTerm("x", [1, 2, t2])
        assert repr(t) == "CoreTerm('x', [1, 2, CoreTerm('y', ['blah', '123', 'bobbins'])])"

    def test_term_indexing(self):
        import unipycation

        t = unipycation.CoreTerm("f", [1, "abc"])
        assert list(t) == [1, "abc"]
        assert t[-1] == "abc"
