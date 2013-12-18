import pytest

class AppTestObjects(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_var(self):
        import unipycation as upy

        X = upy.Var()
        sX = str(X)
        assert isinstance(sX, str)
        assert len(sX) > 0

    def test_term_comparison(self):
        import unipycation as u
        X = u.CoreTerm("f", [1,2,3])
        Y = u.CoreTerm("f", [1,2,4])
        assert X == X
        assert X != Y

    @pytest.mark.xfail
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

    @pytest.mark.xfail
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
        import unipycation as u, re

        # x(X, Y, Z)
        vs = [X, Y, Z] = [ u.Var() for i in range(3) ]
        t = u.CoreTerm("x", vs)

        # XXX if we get Var.UNIQUE_PREFIX working
        #pat = "x\({0}([0-9]), {0}([0-9]), {0}([0-9])\)".format(u.Var.UNIQUE_PREFIX)
        pat = "x\(_V([0-9]), _V([0-9]), _V([0-9])\)"
        m = re.match(pat, str(t))
        assert(m)
        
        # names should be sequential
        nums = [ int(x) for x in m.groups() ]
        assert(nums[1] == nums[0] + 1)
        assert(nums[2] == nums[0] + 2)

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

    def test_term_unpacking(self):
        import unipycation
        t = unipycation.CoreTerm("f", [1, "abc"])
        assert len(t) == 2

        (x, y) = t
        assert x == 1
        assert y == "abc"
