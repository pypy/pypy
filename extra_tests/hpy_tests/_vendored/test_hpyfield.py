"""
NOTE: these tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
import pytest
from .support import HPyTest, DefaultExtensionTemplate

class PairTemplate(DefaultExtensionTemplate):

    def DEFINE_PairObject(self):
        return """
            typedef struct {
                HPyField a;
                HPyField b;
            } PairObject;

            HPyType_HELPERS(PairObject);
        """

    def DEFINE_Pair_new(self):
        return """
            HPyDef_SLOT(Pair_new, HPy_tp_new)
            static HPy Pair_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                HPy a;
                HPy b;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "OO", &a, &b))
                    return HPy_NULL;
                PairObject *pair;
                HPy h_obj = HPy_New(ctx, cls, &pair);
                HPyField_Store(ctx, h_obj, &pair->a, a);
                HPyField_Store(ctx, h_obj, &pair->b, b);
                return h_obj;
            }
        """

    def DEFINE_Pair_traverse(self):
        return """
            HPyDef_SLOT(Pair_traverse, HPy_tp_traverse)
            static int Pair_traverse_impl(void *self, HPyFunc_visitproc visit, void *arg)
            {
                PairObject *p = (PairObject *)self;
                HPy_VISIT(&p->a);
                HPy_VISIT(&p->b);
                return 0;
            }
        """

    def DEFINE_Pair_set_a(self):
        return """
            HPyDef_METH(Pair_set_a, "set_a", HPyFunc_O)
            static HPy Pair_set_a_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                PairObject *pair = PairObject_AsStruct(ctx, self);
                HPyField_Store(ctx, self, &pair->a, arg);
                return HPy_Dup(ctx, ctx->h_None);
            }
        """

    def DEFINE_Pair_get_ab(self):
        return """
            HPyDef_METH(Pair_get_a, "get_a", HPyFunc_NOARGS)
            static HPy Pair_get_a_impl(HPyContext *ctx, HPy self)
            {
                PairObject *pair = PairObject_AsStruct(ctx, self);
                if (HPy_IsNull(pair->a))
                    return HPyUnicode_FromString(ctx, "<NULL>");
                return HPyField_Load(ctx, self, pair->a);
            }

            HPyDef_METH(Pair_get_b, "get_b", HPyFunc_NOARGS)
            static HPy Pair_get_b_impl(HPyContext *ctx, HPy self)
            {
                PairObject *pair = PairObject_AsStruct(ctx, self);
                if (HPy_IsNull(pair->b))
                    return HPyUnicode_FromString(ctx, "<NULL>");
                return HPyField_Load(ctx, self, pair->b);
            }
        """

    pair_type_flags = 'HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_HAVE_GC'
    def PAIR_TYPE_FLAGS(self, flags):
        self.pair_type_flags = flags

    def EXPORT_PAIR_TYPE(self, *defines):
        defines += ('NULL',)
        defines = ', '.join(defines)
        self.EXPORT_TYPE('"Pair"', "Pair_spec")
        return """
            static HPyDef *Pair_defines[] = { %s };
            static HPyType_Spec Pair_spec = {
                .name = "mytest.Pair",
                .basicsize = sizeof(PairObject),
                .flags = %s,
                .defines = Pair_defines
            };
        """ % (defines, self.pair_type_flags)

class TestHPyField(HPyTest):

    ExtensionTemplate = PairTemplate

    def test_gc_track(self):
        if not self.supports_refcounts():
            import pytest
            pytest.skip("CPython only")
        import sys
        # Test that we correctly call PyObject_GC_Track on CPython. The
        # easiest way is to check whether the object is in
        # gc.get_objects().
        import gc
        mod = self.make_module("""
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_traverse

            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse)
            @INIT
        """)
        p = mod.Pair("hello", "world")
        assert gc.is_tracked(p)

    def test_gc_track_no_gc_flag(self):
        if not self.supports_refcounts():
            import pytest
            pytest.skip("CPython only")
        # Same code as test_gc_track, but without HPy_TPFLAGS_HAVE_GC. On
        # CPython, the object is NOT tracked.
        import gc
        mod = self.make_module("""
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_traverse

            @PAIR_TYPE_FLAGS(HPy_TPFLAGS_DEFAULT)
            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse)
            @INIT
        """)
        p = mod.Pair("hello", "world")
        assert not gc.is_tracked(p)

    def test_tp_traverse(self):
        import sys
        import gc
        mod = self.make_module("""
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_traverse

            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse)
            @INIT
        """)
        p = mod.Pair("hello", "world")
        referents = gc.get_referents(p)
        referents.sort()
        assert referents == ['hello', 'world']

    def test_tp_traverse_sanity_check(self):
        import pytest
        with pytest.raises(ValueError):
            self.make_module("""
                @DEFINE_PairObject
                @DEFINE_Pair_new

                // here we are defining a type with HPy_TPFLAGS_HAVE_GC but
                // without providing a tp_traverse
                @EXPORT_PAIR_TYPE(&Pair_new)
                @INIT
            """)

    def test_store_load(self):
        import sys
        mod = self.make_module("""
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_get_ab
            @DEFINE_Pair_traverse

            @PAIR_TYPE_FLAGS(HPy_TPFLAGS_DEFAULT)
            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse, &Pair_get_a, &Pair_get_b)
            @INIT
        """)
        p = mod.Pair("hello", "world")
        assert p.get_a() == 'hello'
        assert p.get_b() == 'world'
        #
        # check the refcnt
        if self.supports_refcounts():
            a = object()
            a_refcnt = sys.getrefcount(a)
            p2 = mod.Pair(a, None)
            assert sys.getrefcount(a) == a_refcnt + 1
            assert p2.get_a() is a
            assert sys.getrefcount(a) == a_refcnt + 1

    def test_store_overwrite(self):
        import sys
        mod = self.make_module("""
            #include <assert.h>
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_get_ab
            @DEFINE_Pair_traverse
            @DEFINE_Pair_set_a

            HPyDef_METH(Pair_clear_a, "clear_a", HPyFunc_NOARGS)
            static HPy Pair_clear_a_impl(HPyContext *ctx, HPy self)
            {
                PairObject *pair = PairObject_AsStruct(ctx, self);
                HPyField_Store(ctx, self, &pair->a, HPy_NULL);
                return HPy_Dup(ctx, ctx->h_None);
            }

            @PAIR_TYPE_FLAGS(HPy_TPFLAGS_DEFAULT)
            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse, &Pair_get_a, &Pair_get_b, &Pair_set_a, &Pair_clear_a)
            @INIT
        """)
        p = mod.Pair("hello", "world")
        assert p.get_a() == 'hello'
        assert p.get_b() == 'world'
        p.set_a('foo')
        assert p.get_a() == 'foo'
        p.clear_a()
        assert p.get_a() == '<NULL>'
        p.set_a('bar')
        assert p.get_a() == 'bar'
        #
        # check the refcnt
        if self.supports_refcounts():
            a = object()
            a_refcnt = sys.getrefcount(a)
            p2 = mod.Pair(a, None)
            assert sys.getrefcount(a) == a_refcnt + 1
            assert p2.get_a() is a
            p2.set_a('foo')
            assert sys.getrefcount(a) == a_refcnt
            p2.set_a(a)
            assert sys.getrefcount(a) == a_refcnt + 1
            p2.clear_a()
            assert sys.getrefcount(a) == a_refcnt
            p2.clear_a()
            assert sys.getrefcount(a) == a_refcnt

    def test_automatic_tp_dealloc(self):
        import sys
        if not self.supports_refcounts():
            import pytest
            pytest.skip("CPython only")

        import sys
        mod = self.make_module("""
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_traverse

            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse)
            @INIT
        """)
        a = object()
        b = object()
        p = mod.Pair(a, b)
        a_cnt = sys.getrefcount(a)
        b_cnt = sys.getrefcount(b)
        del p
        assert sys.getrefcount(a) == a_cnt - 1
        assert sys.getrefcount(b) == b_cnt - 1

    @pytest.mark.syncgc
    def test_automatic_tp_clear(self):
        if not self.supports_refcounts():
            import pytest
            pytest.skip("CPython only")
        import sys

        import gc
        mod = self.make_module("""
            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_traverse
            @DEFINE_Pair_set_a

            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse, &Pair_set_a)
            @INIT
        """)
        def count_pairs():
            return len([obj for obj in gc.get_objects() if type(obj) is mod.Pair])
        assert count_pairs() == 0
        p1 = mod.Pair(None, 'hello')
        p2 = mod.Pair(None, 'world')
        p1.set_a(p2)
        p2.set_a(p1)
        assert count_pairs() == 2
        #
        try:
            gc.disable()
            del p1
            del p2
            assert count_pairs() == 2
        finally:
            gc.enable()
        #
        gc.collect()
        assert count_pairs() == 0

    def test_tp_finalize(self):
        # Tests the contract of tp_finalize: what it should see
        # if called from within HPyField_Store
        mod = self.make_module("""
            #include <stdio.h>

            @DEFINE_PairObject
            @DEFINE_Pair_new
            @DEFINE_Pair_traverse
            @DEFINE_Pair_set_a

            static bool saw_expected_finalize_call;
            static bool unexpected_finalize_call;
            static bool test_finished;

            // During the test we check our assumptions with an assert to play
            // nicely with pytest, but if the finalizer gets called after the
            // test has finished, we have no choice but to abort to signal
            // the error
            static void on_unexpected_finalize_call() {
                if (test_finished)
                    abort();
                else
                    unexpected_finalize_call = true;
            }

            HPyDef_SLOT(Pair_finalize, HPy_tp_finalize)
            static void Pair_finalize_impl(HPyContext *ctx, HPy to_be_finalized)
            {
                PairObject *pair = PairObject_AsStruct(ctx, to_be_finalized);

                // Check that we were called on the right object: 'to_be_finalized'
                HPy to_be_finalized_b = HPyField_Load(ctx, to_be_finalized, pair->b);
                if (!HPy_Is(ctx, to_be_finalized_b, ctx->h_True)) {
                    HPy_Close(ctx, to_be_finalized_b);
                    // This is OK to happen after the test was finished
                    unexpected_finalize_call = true;
                    return;
                }
                HPy_Close(ctx, to_be_finalized_b);

                // Check that we were not called twice
                if (saw_expected_finalize_call) {
                    printf("tp_finalize called twice for 'to_be_finalized'\\\n");
                    on_unexpected_finalize_call();
                    return;
                }

                HPy owner = HPy_NULL, owner_a = HPy_NULL, owner_b = HPy_NULL;
                owner = HPyField_Load(ctx, to_be_finalized, pair->a);
                PairObject *owner_pair = PairObject_AsStruct(ctx, owner);

                // Check that 'to_be_finalized'->a really points to 'owner'
                owner_b = HPyField_Load(ctx, owner, owner_pair->b);
                if (!HPy_Is(ctx, owner_b, ctx->h_False)) {
                    printf("to_be_finalized'->a != 'owner'\\\n");
                    on_unexpected_finalize_call();
                    goto owner_cleanup;
                }

                // Whatever we see in owner->a must not be 'to_be_finalized'
                // For CPython it should be NULL, because Pair_finalize should
                // be called immediately when the field is swapped to new value
                if (HPyField_IsNull(owner_pair->a)) {
                    saw_expected_finalize_call = true;
                    goto owner_cleanup;
                }

                // For GC based implementations, it can be already the 42 if
                // Pair_finalize gets called later
                owner_a = HPyField_Load(ctx, owner, owner_pair->a);
                if (HPyLong_AsLong(ctx, owner_a) == 42) {
                    saw_expected_finalize_call = true;
                    goto owner_cleanup;
                }

                HPyErr_Clear(ctx); // if the field was not a long at all
                printf("unexpected value of the field: %p\\\n", (void*) owner_a._i);
                on_unexpected_finalize_call();
            owner_cleanup:
                HPy_Close(ctx, owner);
                HPy_Close(ctx, owner_a);
                HPy_Close(ctx, owner_b);
            }

            HPyDef_METH(check_finalize_calls, "check_finalize_calls", HPyFunc_NOARGS)
            static HPy check_finalize_calls_impl(HPyContext *ctx, HPy self)
            {
                test_finished = true;
                if (!unexpected_finalize_call && saw_expected_finalize_call)
                    return HPy_Dup(ctx, ctx->h_True);
                else
                    return HPy_Dup(ctx, ctx->h_False);
            }

            @EXPORT(check_finalize_calls)
            @EXPORT_PAIR_TYPE(&Pair_new, &Pair_traverse, &Pair_finalize, &Pair_set_a)
            @INIT
        """)
        to_be_finalized = mod.Pair(None, True)
        owner = mod.Pair(to_be_finalized, False)
        to_be_finalized.set_a(owner)
        del to_be_finalized
        # Now 'to_be_finalized' is referenced only by 'owner'.
        # By setting the field to the new value, the object originally pointed
        # by 'to_be_finalized' becomes garbage. In CPython, this should
        # immediately trigger tp_finalize, in other impls it may also
        # trigger tp_finalize at that point or any later point.
        # In any case, tp_finalize should not see the original value of the
        # field anymore.
        owner.set_a(42)
        from gc import collect
        collect()
        assert mod.check_finalize_calls()