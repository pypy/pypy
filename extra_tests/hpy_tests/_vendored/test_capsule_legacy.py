import pytest
from .support import HPyTest, make_hpy_abi_fixture
from .test_capsule import CapsuleTemplate

hpy_abi = make_hpy_abi_fixture('with hybrid')

class TestHPyCapsuleLegacy(HPyTest):

    ExtensionTemplate = CapsuleTemplate

    def test_legacy_capsule_compat(self):
        import pytest
        mod = self.make_module("""
            @DEFINE_strdup

            #include <Python.h>
            #include <string.h>

            static int dummy = 123;

            static void legacy_destructor(PyObject *capsule)
            {
                /* We need to use C lib 'free' because the string was
                   created with 'strdup0'. */
                free((void *) PyCapsule_GetName(capsule));
            }

            HPyDef_METH(Create_pycapsule, "create_pycapsule", HPyFunc_O)
            static HPy Create_pycapsule_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_ssize_t n;
                const char *name = HPyUnicode_AsUTF8AndSize(ctx, arg, &n);
                char *name_copy = strdup0(name);
                if (name_copy == NULL) {
                    HPyErr_SetString(ctx, ctx->h_MemoryError, "out of memory");
                    return HPy_NULL;
                }
                PyObject *legacy_caps = PyCapsule_New(&dummy, (const char *) name_copy,
                                                      legacy_destructor);
                HPy res = HPy_FromPyObject(ctx, legacy_caps);
                Py_DECREF(legacy_caps);
                return res;
            }

            HPyDef_METH(Capsule_get, "get", HPyFunc_O)
            static HPy Capsule_get_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy res = HPy_NULL;
                HPy h_value = HPy_NULL;
                int *ptr = NULL;

                const char *name = HPyCapsule_GetName(ctx, arg);
                if (name == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                HPy h_name = HPyUnicode_FromString(ctx, name);
                if (HPy_IsNull(h_name)) {
                    goto finish;
                }

                ptr = (int *) HPyCapsule_GetPointer(ctx, arg, name);
                if (ptr == NULL && HPyErr_Occurred(ctx)) {
                    goto finish;
                }

                h_value = HPyLong_FromLong(ctx, *ptr);
                if (HPy_IsNull(h_value)) {
                    goto finish;
                }

                res = HPyTuple_Pack(ctx, 2, h_name, h_value);

            finish:
                HPy_Close(ctx, h_name);
                HPy_Close(ctx, h_value);
                return res;
            }

            @EXPORT(Create_pycapsule)
            @EXPORT(Capsule_get)

            @INIT
        """)
        name = "legacy_capsule"
        p = mod.create_pycapsule(name)
        assert mod.get(p) == (name, 123)
