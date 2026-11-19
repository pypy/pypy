class AppTestWeakref(object):
    spaceconfig = dict(usemodules=('_weakref',))

    def setup_class(cls):
        cls.w_runappdirect = cls.space.wrap(cls.runappdirect)

    def test_del_and_callback_and_id(self):
        if not self.runappdirect:
            skip("the id() doesn't work correctly in __del__ and "
                 "callbacks before translation")
        import gc, weakref
        seen_del = []
        class A(object):
            def __del__(self):
                seen_del.append(id(self))
                seen_del.append(w1() is None)
                seen_del.append(w2() is None)
        seen_callback = []
        def callback(r):
            seen_callback.append(r is w2)
            seen_callback.append(w1() is None)
            seen_callback.append(w2() is None)
        a = A()
        w1 = weakref.ref(a)
        w2 = weakref.ref(a, callback)
        aid = id(a)
        del a
        for i in range(5):
            gc.collect()
        if seen_del:
            assert seen_del == [aid, True, True]
        if seen_callback:
            assert seen_callback == [True, True, True]
