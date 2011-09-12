from pypy.conftest import gettestobjspace


class AppTestPickle:
    version = 0

    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_continuation',),
                                    CALL_METHOD=True)
        cls.space.appexec([], """():
            global continulet, A, __name__

            import sys
            __name__ = 'test_pickle_continulet'
            thismodule = type(sys)(__name__)
            sys.modules[__name__] = thismodule

            from _continuation import continulet
            class A(continulet):
                pass

            thismodule.__dict__.update(globals())
        """)
        cls.w_version = cls.space.wrap(cls.version)

    def test_basic_setup(self):
        from _continuation import continulet
        lst = [4]
        co = continulet(lst.append)
        assert lst == [4]
        res = co.switch()
        assert res is None
        assert lst == [4, co]

    def test_pickle_continulet_empty(self):
        from _continuation import continulet
        lst = [4]
        co = continulet.__new__(continulet)
        import pickle
        pckl = pickle.dumps(co, self.version)
        print repr(pckl)
        co2 = pickle.loads(pckl)
        assert co2 is not co
        assert not co.is_pending()
        assert not co2.is_pending()
        # the empty unpickled coroutine can still be used:
        result = [5]
        co2.__init__(result.append)
        res = co2.switch()
        assert res is None
        assert result == [5, co2]

    def test_pickle_continulet_empty_subclass(self):
        from test_pickle_continulet import continulet, A
        lst = [4]
        co = continulet.__new__(A)
        co.foo = 'bar'
        co.bar = 'baz'
        import pickle
        pckl = pickle.dumps(co, self.version)
        print repr(pckl)
        co2 = pickle.loads(pckl)
        assert co2 is not co
        assert not co.is_pending()
        assert not co2.is_pending()
        assert type(co) is type(co2) is A
        assert co.foo == co2.foo == 'bar'
        assert co.bar == co2.bar == 'baz'
        # the empty unpickled coroutine can still be used:
        result = [5]
        co2.__init__(result.append)
        res = co2.switch()
        assert res is None
        assert result == [5, co2]


class AppTestPickle_v1(AppTestPickle):
    version = 1

class AppTestPickle_v2(AppTestPickle):
    version = 2
