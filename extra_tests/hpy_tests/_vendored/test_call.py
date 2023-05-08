from .support import HPyTest


class TestCall(HPyTest):
    def argument_combinations(self, **items):
        """ Returns all possible ways of expressing the given items as
            arguments to a function.
        """
        items = list(items.items())
        for i in range(len(items) + 1):
            args = tuple(item[1] for item in items[:i])
            kw = dict(items[i:])
            yield {"args": args, "kw": kw}
            if not args:
                yield {"kw": kw}
            if not kw:
                yield {"args": args}
            if not args and not kw:
                yield {}

    def argument_combinations_tuple(self, **items):
        """ Same as 'argument_combinations' but returns a tuple where
            the first element is the argument tuple and the second is
            a dict that may contain the keywords dict.
        """
        items = list(items.items())
        for i in range(len(items) + 1):
            args = tuple(item[1] for item in items[:i])
            kw = dict(items[i:])
            yield args, kw
            if not args:
                yield tuple(), kw
            if not kw:
                yield args, {}
            if not args and not kw:
                yield tuple(), {}

    def test_hpy_calltupledict(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(call, "call", HPyFunc_KEYWORDS)
            static HPy call_impl(HPyContext *ctx, HPy self, const HPy *args,
                                 size_t nargs, HPy kwnames)
            {

                HPy f, result;
                HPy f_args = HPy_NULL;
                HPy f_kw = HPy_NULL;
                HPyTracker ht;
                static const char *kwlist[] = { "f", "args", "kw", NULL };
                if (!HPyArg_ParseKeywords(ctx, &ht, args, nargs, kwnames,
                                          "O|OO", kwlist, &f, &f_args, &f_kw)) {
                    return HPy_NULL;
                }
                result = HPy_CallTupleDict(ctx, f, f_args, f_kw);
                HPyTracker_Close(ctx, ht);
                return result;
            }
            @EXPORT(call)
            @INIT
        """)

        def f(a, b):
            return a + b

        def g():
            return "this is g"

        # test passing arguments with handles of the correct type --
        # i.e. args is a tuple or a null handle, kw is a dict or a null handle.
        for d in self.argument_combinations(a=1, b=2):
            assert mod.call(f, **d) == 3
        for d in self.argument_combinations(a=1):
            with pytest.raises(TypeError):
                mod.call(f, **d)
        for d in self.argument_combinations():
            with pytest.raises(TypeError):
                mod.call(f, **d)
        for d in self.argument_combinations():
            assert mod.call(g, **d) == "this is g"
        for d in self.argument_combinations(object=2):
            assert mod.call(str, **d) == "2"
        for d in self.argument_combinations():
            with pytest.raises(TypeError):
                mod.call("not callable", **d)
        for d in self.argument_combinations(unknown=2):
            with pytest.raises(TypeError):
                mod.call("not callable", **d)

        # test passing handles of the incorrect type as arguments
        with pytest.raises(TypeError):
            mod.call(f, args=[1, 2])
        with pytest.raises(TypeError):
            mod.call(f, args="string")
        with pytest.raises(TypeError):
            mod.call(f, args=1)
        with pytest.raises(TypeError):
            mod.call(f, args=None)
        with pytest.raises(TypeError):
            mod.call(f, kw=[1, 2])
        with pytest.raises(TypeError):
            mod.call(f, kw="string")
        with pytest.raises(TypeError):
            mod.call(f, kw=1)
        with pytest.raises(TypeError):
            mod.call(f, kw=None)

    def test_hpy_callmethodtupledict(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(call, "call", HPyFunc_KEYWORDS)
            static HPy call_impl(HPyContext *ctx, HPy self,
                                 const HPy *args, size_t nargs, HPy kwnames)
            {
                HPy result, result_0, result_1;
                HPy receiver = HPy_NULL;
                HPy h_name = HPy_NULL;
                HPy m_args = HPy_NULL;
                const char *s_name = "";
                HPyTracker ht;
                static const char *kwlist[] = { "receiver", "name", "args", NULL };
                if (!HPyArg_ParseKeywords(ctx, &ht, args, nargs, kwnames, "OO|O",
                                          kwlist, &receiver, &h_name, &m_args)) {
                    return HPy_NULL;
                }
                s_name = HPyUnicode_AsUTF8AndSize(ctx, h_name, NULL);
                if (s_name == NULL) {
                    HPyTracker_Close(ctx, ht);
                    return HPy_NULL;
                }

                result_0 = HPy_CallMethodTupleDict(ctx, h_name, receiver, m_args, HPy_NULL);
                if (HPy_IsNull(result_0)) {
                    HPyTracker_Close(ctx, ht);
                    return HPy_NULL;
                }

                result_1 = HPy_CallMethodTupleDict_s(ctx, s_name, receiver, m_args, HPy_NULL);
                if (HPy_IsNull(result_1)) {
                    HPyTracker_Close(ctx, ht);
                    HPy_Close(ctx, result_0);
                    return HPy_NULL;
                }

                HPyTracker_Close(ctx, ht);
                result = HPyTuple_Pack(ctx, 2, result_0, result_1);
                HPy_Close(ctx, result_0);
                HPy_Close(ctx, result_1);
                return result;
            }
            @EXPORT(call)
            @INIT
        """)

        test_args = (
            # (receiver, method, args_tuple)
            dict(receiver={"hello": 1, "world": 2}, name="keys", args=tuple()),
            dict(receiver="Hello, World", name="find", args=("Wo", )),
        )

        for kw in test_args:
            res = getattr(kw["receiver"], kw["name"])(*kw["args"])
            assert mod.call(**kw) == (res, res)

        with pytest.raises(AttributeError):
            mod.call(receiver=dict(), name="asdf", args=tuple())

        with pytest.raises(TypeError):
            mod.call(receiver="Hello, World", name="find")

        with pytest.raises(TypeError):
            mod.call(receiver="Hello, World", name="find", args=("1", ) * 100)

    def test_hpy_call(self):
        import pytest
        mod = self.make_module("""
            #define SELF 1

            HPyDef_METH(call, "call", HPyFunc_KEYWORDS)
            static HPy call_impl(HPyContext *ctx, HPy self,
                                 const HPy *args, size_t nargs, HPy kwnames)
            {
                if (nargs < SELF) {
                    HPyErr_SetString(ctx, ctx->h_TypeError, "HPy_Call requires a receiver");
                    return HPy_NULL;
                }
                return HPy_Call(ctx, args[0], args + SELF, nargs - SELF, kwnames);
            }
            @EXPORT(call)
            @INIT
        """)

        def foo():
            raise ValueError

        def listify(*args):
            return args

        def f(a, b):
            return a + b

        def g():
            return "this is g"

        class KwDict(dict):
            def __getitem__(self, key):
                return "key=" + str(key);

        test_args = (
            # (receiver, args_tuple, kwd)
            (dict, (dict(a=0, b=1), ), {}),
            (dict, tuple(), dict(a=0, b=1)),
        )
        for receiver, args_tuple, kwd in test_args:
            assert mod.call(receiver, *args_tuple, **kwd) == receiver(*args_tuple, **kwd)

        # NULL dict for keywords
        mod.call(dict)

        # dict subclass for keywords
        kwdict = KwDict(x=11, y=12, z=13)
        assert mod.call(dict, **kwdict) == dict(kwdict)

        with pytest.raises(ValueError):
            mod.call(foo)
        with pytest.raises(TypeError):
            mod.call()

        # large amount of args
        r = range(1000)
        assert mod.call(listify, *r) == listify(*r)

        # test passing arguments with handles of the correct type --
        # i.e. args is a tuple or a null handle, kw is a dict or a null handle.
        for args, kwd in self.argument_combinations_tuple(a=1, b=2):
            assert mod.call(f, *args, **kwd) == 3
        for args, kwd in self.argument_combinations_tuple(a=1):
            with pytest.raises(TypeError):
                mod.call(f, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple():
            with pytest.raises(TypeError):
                mod.call(f, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple():
            assert mod.call(g, *args, **kwd) == "this is g"
        for args, kwd in self.argument_combinations_tuple(object=2):
            assert mod.call(str, *args, **kwd) == "2"
        for args, kwd in self.argument_combinations_tuple():
            with pytest.raises(TypeError):
                mod.call("not callable", *args, **kwd)
        for args, kwd in self.argument_combinations_tuple(unknown=2):
            with pytest.raises(TypeError):
                mod.call("not callable", *args, **kwd)

    def test_hpy_callmethod(self):
        import pytest
        mod = self.make_module("""
            #define NAME 1

            HPyDef_METH(call, "call", HPyFunc_KEYWORDS)
            static HPy call_impl(HPyContext *ctx, HPy self,
                                 const HPy *args, size_t nargs, HPy kwnames)
            {
                if (nargs < NAME) {
                    HPyErr_SetString(ctx, ctx->h_TypeError, "HPy_CallMethod requires a receiver and a method name");
                    return HPy_NULL;
                }
                // 'args[0]' is the name
                return HPy_CallMethod(ctx, args[0], args + NAME, nargs - NAME, kwnames);
            }
            @EXPORT(call)
            @INIT
        """)

        class Dummy:
            not_callable = 123

            def f(self, a, b):
                return a + b

            def g(self):
                return 'this is g'

        test_obj = Dummy()

        # test passing arguments with handles of the correct type --
        # i.e. args is a tuple or a null handle, kw is a dict or a null handle.
        for args, kwd in self.argument_combinations_tuple(a=1, b=2):
            assert mod.call('f', test_obj, *args, **kwd) == 3
        for args, kwd in self.argument_combinations_tuple(a=1):
            with pytest.raises(TypeError):
                mod.call('f', test_obj, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple(a=1, b=2, c=3):
            with pytest.raises(TypeError):
                mod.call('f', test_obj, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple():
            with pytest.raises(TypeError):
                mod.call('f', test_obj, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple():
            assert mod.call('g', test_obj, *args, **kwd) == 'this is g'
        for args, kwd in self.argument_combinations_tuple():
            with pytest.raises(TypeError):
                mod.call('not_callable', test_obj, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple(unknown=2):
            with pytest.raises(TypeError):
                mod.call('not_callable', test_obj, *args, **kwd)
        for args, kwd in self.argument_combinations_tuple():
            with pytest.raises(AttributeError):
                mod.call('embedded null byte', test_obj, *args, **kwd)

    def test_hpycallable_check(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                if (HPyCallable_Check(ctx, arg))
                    return HPy_Dup(ctx, ctx->h_True);
                return HPy_Dup(ctx, ctx->h_False);
            }
            @EXPORT(f)
            @INIT
        """)

        def f():
            return "this is f"

        assert mod.f(f) is True
        assert mod.f(str) is True
        assert mod.f("a") is False
        assert mod.f(3) is False
