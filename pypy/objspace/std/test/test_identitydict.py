from pypy.interpreter.gateway import interp2app
from pypy.conftest import gettestobjspace
from pypy.conftest import option

class AppTestTrackVersion:

    def setup_class(cls):
        from pypy.objspace.std import identitydict
        cls.space = gettestobjspace(
                        **{"objspace.std.withidentitydict": True})

        def compares_by_identity(space, w_cls):
            return space.wrap(w_cls.compares_by_identity())
        cls.w_compares_by_identity = cls.space.wrap(interp2app(compares_by_identity))

        def get_version(space):
            v = cls.versions.setdefault(identitydict.get_global_version(space),
                                        len(cls.versions))
            return space.wrap(v)
        cls.w_get_version = cls.space.wrap(interp2app(get_version))

    def setup_method(self, m):
        self.__class__.versions = {}

    def test_compares_by_identity(self):
        class Plain(object):
            pass

        class CustomEq(object):
            def __eq__(self, other):
                return True

        class CustomCmp (object):
            def __cmp__(self, other):
                return 0

        class CustomHash(object):
            def __hash__(self):
                return 0

        assert self.compares_by_identity(Plain)
        assert not self.compares_by_identity(CustomEq)
        assert not self.compares_by_identity(CustomCmp)
        assert not self.compares_by_identity(CustomHash)

    def test_modify_class(self):
        class X(object):
            pass

        assert self.compares_by_identity(X)
        X.__eq__ = lambda x: None
        assert not self.compares_by_identity(X)
        del X.__eq__
        assert self.compares_by_identity(X)

    def test_versioning(self):
        class X(object):
            pass

        class Y(object):
            def __eq__(self, other):
                pass

        assert self.get_version() == 0
        X.__eq__ = lambda x: None
        # modifying a class for which we never checked the
        # compares_by_identity() status does not increase the version
        assert self.get_version() == 0

        del X.__eq__
        assert self.compares_by_identity(X) # now we check it
        X.__add__ = lambda x: None
        assert self.get_version() == 0 # innocent change
        #
        X.__eq__ = lambda x: None
        assert self.get_version() == 1 # BUMP!

        del X.__eq__
        assert self.compares_by_identity(X)
        X.__bases__ = (object,)
        assert self.get_version() == 2 # BUMP!

        # modifying a class which is already "bad" does not increase the
        # version
        Y.__eq__ = lambda x: None
        assert self.get_version() == 2

    def test_change___class__(self):
        class X(object):
            pass

        class Y(object):
            pass

        class Z(object):
            def __eq__(self, other):
                pass

        x = X()
        assert self.compares_by_identity(X)
        assert self.get_version() == 0
        x.__class__ = Y
        assert self.get_version() == 0
        x.__class__ = Z
        assert self.get_version() == 1


class AppTestIdentityDict(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withidentitydict": True})
        if option.runappdirect:
            py.test.skip("__repr__ doesn't work on appdirect")

    def w_uses_identity_strategy(self, obj):
        import __pypy__
        return "IdentityDictStrategy" in __pypy__.internal_repr(obj)

    def test_use_strategy(self):
        class X(object):
            pass
        d = {}
        x = X()
        d[x] = 1
        assert self.uses_identity_strategy(d)
        assert d[x] == 1

    def test_bad_item(self):
        class X(object):
            pass
        class Y(object):
            def __hash__(self):
                return 32

        d = {}
        x = X()
        y = Y()
        d[x] = 1
        assert self.uses_identity_strategy(d)
        d[y] = 2
        assert not self.uses_identity_strategy(d)
        assert d[x] == 1
        assert d[y] == 2

    def test_bad_key(self):
        class X(object):
            pass
        d = {}
        x = X()

        class Y(object):
            def __hash__(self):
                return hash(x) # to make sure we do x == y

            def __eq__(self, other):
                return True

        y = Y()
        d[x] = 1
        assert self.uses_identity_strategy(d)
        assert d[y] == 1
        assert not self.uses_identity_strategy(d)

    def test_iter(self):
        class X(object):
            pass
        x = X()
        d = {x: 1}
        assert self.uses_identity_strategy(d)
        assert list(iter(d)) == [x]
