"""
NOTE: these tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
import pytest
from .support import HPyTest, DefaultExtensionTemplate

class CapsuleTemplate(DefaultExtensionTemplate):

    def DEFINE_strdup(self):
        return """
            #include <string.h>

            static char *strdup0(const char *s)
            {
                size_t n = strlen(s) + 1;
                char *copy = (char *) malloc(n * sizeof(char));
                if (copy == NULL) {
                    return NULL;
                }
                strncpy(copy, s, n);
                return copy;
            }
        """

    def DEFINE_SomeObject(self):
        return """
            #include <string.h>

            typedef struct {
                int value;
                char message[];
            } SomeObject;

            static SomeObject *create_payload(int value, char *message)
            {
                size_t n_message = strlen(message) + 1;
                SomeObject *pointer = (SomeObject *)
                        malloc(sizeof(SomeObject) + n_message * sizeof(char));
                if (pointer == NULL) {
                    return NULL;
                }
                pointer->value = value;
                strncpy(pointer->message, message, n_message);
                return pointer;
            }
        """

    def DEFINE_Capsule_New(self, destructor="NULL"):
        return """
            #include <string.h>

            static const char *_capsule_name = "some_capsule";

            #define CAPSULE_NAME _capsule_name

            HPyDef_METH(Capsule_New, "capsule_new", HPyFunc_VARARGS)
            static HPy Capsule_New_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy res;
                int value;
                char *message;
                void *ptr;

                if (nargs > 0)
                {
                    if (!HPyArg_Parse(ctx, NULL, args, nargs, "is", &value, &message)) {
                        return HPy_NULL;
                    }
                    ptr = (void *) create_payload(value, message);
                    if (ptr == NULL) {
                        HPyErr_SetString(ctx, ctx->h_MemoryError, "out of memory");
                        return HPy_NULL;
                    }
                    res = HPyCapsule_New(ctx, ptr, CAPSULE_NAME, %s);
                    if (HPy_IsNull(res)) {
                        free(ptr);
                    }
                    return res;
                }
                /* just for error case testing */
                return HPyCapsule_New(ctx, NULL, CAPSULE_NAME, NULL);
            }
        """ % destructor

    def DEFINE_Payload_Free(self):
        return """
            #include <string.h>

            HPyDef_METH(Payload_Free, "payload_free", HPyFunc_O)
            static HPy Payload_Free_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                const char *name = HPyCapsule_GetName(ctx, arg);
                if (name == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }

                void *pointer = HPyCapsule_GetPointer(ctx, arg, name);
                if (pointer == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                free(pointer);

                void *context = HPyCapsule_GetContext(ctx, arg);
                if (context == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                free(context);

                return HPy_Dup(ctx, ctx->h_None);
            }
        """

    def DEFINE_Capsule_GetName(self):
        return """
            HPyDef_METH(Capsule_GetName, "capsule_getname", HPyFunc_O)
            static HPy Capsule_GetName_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                const char *name = HPyCapsule_GetName(ctx, arg);
                if (name == NULL) {
                    return HPy_NULL;
                }
                return HPyUnicode_FromString(ctx, name);
            }
        """

    def DEFINE_Capsule_GetPointer(self):
        return """
            static HPy payload_as_tuple(HPyContext *ctx, SomeObject *pointer)
            {
                HPy value = HPyLong_FromLong(ctx, pointer->value);
                HPy message = HPyUnicode_FromString(ctx, pointer->message);
                HPy result = HPyTuple_Pack(ctx, 2, value, message);
                HPy_Close(ctx, value);
                HPy_Close(ctx, message);
                return result;
            }

            HPyDef_METH(Capsule_GetPointer, "capsule_getpointer", HPyFunc_O)
            static HPy Capsule_GetPointer_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                SomeObject *pointer = (SomeObject *) HPyCapsule_GetPointer(ctx, arg, CAPSULE_NAME);
                if (pointer == NULL) {
                    return HPy_NULL;
                }
                return payload_as_tuple(ctx, pointer);
            }
        """

class TestHPyCapsule(HPyTest):

    ExtensionTemplate = CapsuleTemplate

    def test_capsule_new(self):
        mod = self.make_module("""
            @DEFINE_SomeObject
            @DEFINE_Capsule_New
            @DEFINE_Capsule_GetName
            @DEFINE_Payload_Free

            @EXPORT(Capsule_New)
            @EXPORT(Capsule_GetName)
            @EXPORT(Payload_Free)

            @INIT
        """)
        p = mod.capsule_new(789, "Hello, World!")
        try:
            assert mod.capsule_getname(p) == "some_capsule"
        finally:
            # manually free the payload to avoid a memleak
            mod.payload_free(p)
        with pytest.raises(ValueError):
            mod.capsule_new()

    def test_capsule_getter_and_setter(self):
        mod = self.make_module("""
            #include <string.h>

            @DEFINE_strdup
            @DEFINE_SomeObject
            @DEFINE_Capsule_New
            @DEFINE_Capsule_GetPointer
            @DEFINE_Capsule_GetName
            @DEFINE_Payload_Free

            HPyDef_METH(Capsule_SetPointer, "capsule_setpointer", HPyFunc_VARARGS)
            static HPy Capsule_SetPointer_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy capsule;
                int value;
                char *message;
                int non_null_pointer;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "Oisi",
                                  &capsule, &value, &message, &non_null_pointer)) {
                    return HPy_NULL;
                }

                /* avoid memleak; get and later free previous pointer */
                void *old_ptr= HPyCapsule_GetPointer(ctx, capsule, CAPSULE_NAME);
                if (old_ptr == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }

                SomeObject *pointer = NULL;
                if (non_null_pointer) {
                    pointer = create_payload(value, message);
                    if (pointer == NULL) {
                        HPyErr_SetString(ctx, ctx->h_MemoryError, "out of memory");
                        return HPy_NULL;
                    }
                }

                if (HPyCapsule_SetPointer(ctx, capsule, (void *) pointer) < 0) {
                    if (non_null_pointer) {
                        free(pointer);
                    }
                    return HPy_NULL;
                }
                free(old_ptr);
                return HPy_Dup(ctx, ctx->h_None);
            }

            HPyDef_METH(Capsule_GetContext, "capsule_getcontext", HPyFunc_O)
            static HPy Capsule_GetContext_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                SomeObject *context = (SomeObject *) HPyCapsule_GetContext(ctx, arg);
                if (context == NULL) {
                    return HPyErr_Occurred(ctx) ? HPy_NULL : HPy_Dup(ctx, ctx->h_None);
                }
                return payload_as_tuple(ctx, context);
            }

            HPyDef_METH(Capsule_SetContext, "capsule_setcontext", HPyFunc_VARARGS)
            static HPy Capsule_SetContext_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy capsule;
                int value;
                char *message;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "Ois", &capsule, &value, &message)) {
                    return HPy_NULL;
                }

                /* avoid memleak; get and free previous context */
                void *old_context = HPyCapsule_GetContext(ctx, capsule);
                if (old_context == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                free(old_context);

                SomeObject *context = create_payload(value, message);
                if (context == NULL) {
                    HPyErr_SetString(ctx, ctx->h_MemoryError, "out of memory");
                    return HPy_NULL;
                }
                if (HPyCapsule_SetContext(ctx, capsule, (void *) context) < 0) {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            HPyDef_METH(Capsule_SetName, "capsule_setname", HPyFunc_VARARGS)
            static HPy Capsule_SetName_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy capsule;
                const char *name;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "Os", &capsule, &name)) {
                    return HPy_NULL;
                }

                /* avoid memleak; get and free previous context */
                const char *old_name = HPyCapsule_GetName(ctx, capsule);
                if (old_name == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                if (old_name != CAPSULE_NAME) {
                    free((void *) old_name);
                }

                char *name_copy = strdup0(name);
                if (name_copy == NULL) {
                    HPyErr_SetString(ctx, ctx->h_MemoryError, "out of memory");
                    return HPy_NULL;
                }

                if (HPyCapsule_SetName(ctx, capsule, (const char *) name_copy) < 0) {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            static HPyCapsule_Destructor invalid_dtor = { NULL, NULL };

            HPyDef_METH(Capsule_SetDestructor, "capsule_set_destructor", HPyFunc_VARARGS)
            static HPy Capsule_SetDestructor_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy capsule;
                HPy null_dtor;
                HPyCapsule_Destructor *dtor;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "OO", &capsule, &null_dtor)) {
                    return HPy_NULL;
                }

                if (HPy_IsTrue(ctx, null_dtor)) {
                    dtor = NULL;
                } else {
                    dtor = &invalid_dtor;
                }

                if (HPyCapsule_SetDestructor(ctx, capsule, dtor) < 0) {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            HPyDef_METH(Capsule_free_name, "capsule_freename", HPyFunc_O)
            static HPy Capsule_free_name_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                /* avoid memleak; get and free previous context */
                const char *old_name = HPyCapsule_GetName(ctx, arg);
                if (old_name == NULL && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                if (old_name != CAPSULE_NAME) {
                    free((void *) old_name);
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT(Capsule_New)
            @EXPORT(Capsule_GetPointer)
            @EXPORT(Capsule_SetPointer)
            @EXPORT(Capsule_GetContext)
            @EXPORT(Capsule_SetContext)
            @EXPORT(Capsule_GetName)
            @EXPORT(Capsule_SetName)
            @EXPORT(Capsule_SetDestructor)
            @EXPORT(Capsule_free_name)
            @EXPORT(Payload_Free)

            @INIT
        """)
        p = mod.capsule_new(789, "Hello, World!")
        try:
            assert mod.capsule_getpointer(p) == (789, "Hello, World!")
            assert mod.capsule_setpointer(p, 456, "lorem ipsum", True) is None
            assert mod.capsule_getpointer(p) == (456, "lorem ipsum")

            assert mod.capsule_getcontext(p) == None
            assert mod.capsule_setcontext(p, 123, "hello") is None
            assert mod.capsule_getcontext(p) == (123, "hello")

            assert mod.capsule_getname(p) == "some_capsule"
            assert mod.capsule_setname(p, "foo") is None
            assert mod.capsule_getname(p) == "foo"

            assert mod.capsule_set_destructor(p, True) is None

            not_a_capsule = "hello"
            with pytest.raises(ValueError):
                mod.capsule_getpointer(not_a_capsule)
            with pytest.raises(ValueError):
                mod.capsule_setpointer(not_a_capsule, 0, "", True)
            with pytest.raises(ValueError):
                mod.capsule_setpointer(p, 456, "lorem ipsum", False)
            with pytest.raises(ValueError):
               mod.capsule_getcontext(not_a_capsule)
            with pytest.raises(ValueError):
               mod.capsule_setcontext(not_a_capsule, 0, "")
            with pytest.raises(ValueError):
               mod.capsule_getname(not_a_capsule)
            with pytest.raises(ValueError):
               mod.capsule_setname(not_a_capsule, "")
            with pytest.raises(ValueError):
                mod.capsule_set_destructor(not_a_capsule, True)
            with pytest.raises(ValueError):
                mod.capsule_set_destructor(p, False)
        finally:
            # manually free the payload to avoid a memleak
            mod.payload_free(p)
            mod.capsule_freename(p)

    def test_capsule_isvalid(self):
        mod = self.make_module("""
            @DEFINE_SomeObject
            @DEFINE_Capsule_New
            @DEFINE_Capsule_GetName
            @DEFINE_Payload_Free

            HPyDef_METH(Capsule_isvalid, "capsule_isvalid", HPyFunc_VARARGS)
            static HPy Capsule_isvalid_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy capsule;
                const char *name;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "Os", &capsule, &name)) {
                    return HPy_NULL;
                }
                return HPyBool_FromLong(ctx, HPyCapsule_IsValid(ctx, capsule, name));
            }

            @EXPORT(Capsule_New)
            @EXPORT(Capsule_GetName)
            @EXPORT(Capsule_isvalid)
            @EXPORT(Payload_Free)

            @INIT
        """)
        p = mod.capsule_new(789, "Hello, World!")
        name = mod.capsule_getname(p)
        try:
            assert mod.capsule_isvalid(p, name)
            assert not mod.capsule_isvalid(p, "asdf")
            assert not mod.capsule_isvalid("asdf", name)
        finally:
            # manually free the payload to avoid a memleak since the
            # capsule doesn't have a destructor
            mod.payload_free(p)

    @pytest.mark.syncgc
    def test_capsule_new_with_destructor(self):
        mod = self.make_module("""
            static int pointer_freed = 0;

            HPyCapsule_DESTRUCTOR(mydtor)
            static void mydtor_impl(const char *name, void *pointer, void *context)
            {
                free(pointer);
                pointer_freed = 1;
            }

            @DEFINE_SomeObject
            @DEFINE_Capsule_New(&mydtor)
            @DEFINE_Capsule_GetName
            @DEFINE_Payload_Free

            HPyDef_METH(Pointer_freed, "pointer_freed", HPyFunc_NOARGS)
            static HPy Pointer_freed_impl(HPyContext *ctx, HPy self)
            {
                return HPyBool_FromLong(ctx, pointer_freed);
            }

            @EXPORT(Capsule_New)
            @EXPORT(Capsule_GetName)
            @EXPORT(Pointer_freed)

            @INIT
        """)
        p = mod.capsule_new(789, "Hello, World!")
        assert mod.capsule_getname(p) == "some_capsule"
        del p
        assert mod.pointer_freed()

    def test_capsule_new_with_invalid_destructor(self):
        mod = self.make_module("""
            static HPyCapsule_Destructor mydtor = { NULL, NULL };

            @DEFINE_SomeObject
            @DEFINE_Capsule_New(&mydtor)
            @EXPORT(Capsule_New)
            @INIT
        """)
        with pytest.raises(ValueError):
            mod.capsule_new(789, "Hello, World!")
