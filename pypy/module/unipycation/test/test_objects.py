import pytest

class AppTestObjects(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_var(self):
        import unipycation as upy
        N = 10

        vs = [ str(upy.Var()) for x in range(N) ]
        combos = [ (str(x), str(y)) for x in vs for y in vs if x != y ]

        for (x, y) in combos:
            assert x != y # should all have distinct names

    def test_list(self):
        import unipycation as u

        e = u.Engine("f([w, x]).")
        X = u.Var()
        t = u.Term("f", [X])
        x_val = e.query_single(t, [X])[X]

        assert x_val.name == "."
        assert x_val.args[0] == "w"
        assert x_val.args[1].name == "."
        assert x_val.args[1].args[0] == "x"
        assert x_val.args[1].args[1] == "[]"

    def test_functor(self):
        import unipycation as u

        e = u.Engine("f(g(a, b, c, d)).")
        X = u.Var()
        
        t = u.Term("f", [X])
        x_val = e.query_single(t, [X])[X]

        assert len(x_val) == 4 and \
                x_val[0] == "a" and \
                x_val[1] == "b" and \
                x_val[2] == "c" and \
                x_val[3] == "d"

    def test_term_builder(self):
        import unipycation

        t = unipycation.Term("myterm", ["e1", "e2", "e3"])
        elems = [ t[x] for x in range(len(t)) ]

        assert elems == ["e1", "e2", "e3" ]

    def test_nest_term_builder(self):
        import unipycation

        def nest_many(count):
            if count < 10:
                return unipycation.Term("myterm", [count, nest_many(count + 1)])
            else:
                return 666

        def unnest_many(term, count):
            assert len(term) == 2
            assert term[0] == count
            if isinstance(term[1], unipycation.Term):
                assert term.name == "myterm"
                assert term[1].name == "myterm"
                unnest_many(term[1], count + 1)
            else:
                assert 9 == count
                assert term[1] == 666

        top = nest_many(0)
        unnest_many(top, 0)
