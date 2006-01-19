import unification as u
from py.test import raises, skip

class TestUnification:
    
    def setup_method(self, meth):
        u._store = u.Store()

    def test_bind_var_var(self):
        x = u.var('x')
        y = u.var('y')
        z = u.var('z')
        u.bind(x, z)
        assert u._store.unbound == set([u.EqSet([y]),
                                        u.EqSet([x,z])])
        assert u.bound() == []

    def test_bind_var_val(self):
        y = u.var('y')
        u.bind(y, 42)
        assert u.unbound() == []
        assert u._store.bound == {y:42}
        x = u.var('x')
        z = u.var('z')
        u.bind(x, z)
        u.bind(z, 3.14)
        assert u.unbound() == []
        assert u._store.bound == {x:3.14, y:42, z:3.14}

    def test_already_in_store(self):
        x = u.var('x')
        raises(u.AlreadyInStore, u.var, 'x')

    def test_already_bound(self):
        x = u.var('x')
        u.bind(x, 42)
        raises(u.AlreadyBound, u.bind, x, 42)

    def test_unify_lists_success(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, [42, z])
        u.bind(y, [w, 44])
        u.unify(x, y)
        assert u._store.bound == {y: [w, 44], x: [42, z],
                                  z: 44,      w: 42}

    def test_unify_dicts_success(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, {1:42, 2:z})
        u.bind(y, {1:w,  2:44})
        u.unify(x, y)
        assert u._store.bound == {y: {1:w,  2:44},
                                  x: {1:42, 2:z},
                                  z: 44, w: 42}

    def test_unify_failure(self):
        x,y,z = u.var('x'), u.var('y'), u.var('z')
        u.bind(x, [42, z])
        u.bind(y, [z, 44])
        raises(u.UnificationFailure, u.unify, x, y)

    def test_unify_failure2(self):
        x,y,z,w = (u.var('x'), u.var('y'),
                   u.var('z'), u.var('w'))
        u.bind(x, [42, z])
        u.bind(y, [w, 44])
        u.bind(z, w)
        raises(u.UnificationFailure, u.unify, x, y)

    def test_unify_circular(self):
        x, y, z, w, a, b = (u.var('x'), u.var('y'),
                            u.var('z'), u.var('w'),
                            u.var('a'), u.var('b'))
        u.bind(x, [y])
        u.bind(y, [x])
        raises(u.Circularity, u.unify, x, y)
        u.bind(z, [1, w])
        u.bind(w, [z, 2])
        raises(u.UnificationFailure, u.unify, z, w)
        u.bind(a, {1:42, 2:b})
        u.bind(b, {1:a,  2:42})
        raises(u.UnificationFailure, u.unify, a, b)
        
