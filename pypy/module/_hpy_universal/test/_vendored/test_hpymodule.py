import types
import pytest
from .support import HPyTest

class TestModule(HPyTest):
    def test_HPyModule_simple(self):
        """
        The simplest fully declarative module creation.
        """
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 42);
            }

            static HPyDef *moduledefs[] = { &f, NULL };
            static HPyModuleDef moduledef = {
                .doc = "Some doc",
                .size = 0,
                .legacy_methods = NULL,
                .defines = moduledefs,
                .globals = NULL,
            };

            @HPy_MODINIT(moduledef)
        """)
        assert mod.__name__ == mod.__spec__.name
        assert mod.__doc__ == "Some doc"
        assert mod.f() == 42

    def test_HPyModule_custom_exec(self):
        """
        Module that defines several exec slots. HPy specifies that the slots
        will be executed in declaration order. Exec slots can add new types,
        and other objects into the module. They can also initialize other
        objects. The exec slots will be called on every new instance of the
        module, for example, when it is imported in several subinterpreters.
        """
        mod = self.make_module("""
            HPyDef_SLOT(exec1, HPy_mod_exec)
            static int exec1_impl(HPyContext *ctx, HPy mod)
            {
                HPy list = HPyList_New(ctx, 0);
                if (HPy_IsNull(list))
                    return -1;
                HPy_SetAttr_s(ctx, mod, "data", list);
                HPy_Close(ctx, list);
                return 0;
            }

            HPyDef_SLOT(exec2, HPy_mod_exec)
            static int exec2_impl(HPyContext *ctx, HPy mod)
            {
                HPy list = HPy_GetAttr_s(ctx, mod, "data");
                if (HPy_IsNull(list))
                    return -1;
                if (HPy_Length(ctx, list) != 0) {
                    HPyErr_SetString(ctx, ctx->h_RuntimeError, "Unexpected: len(list) != 0");
                    return -1;
                }
                HPy item = HPyLong_FromLong(ctx, 42);
                HPyList_Append(ctx, list, item);
                HPy_Close(ctx, item);
                HPy_Close(ctx, list);
                return 0;
            }

            static HPyDef *moduledefs[] = {
                &exec1,
                &exec2,
                NULL
            };

            static HPyModuleDef moduledef = {
                .doc = "Some doc",
                .size = 0,
                .legacy_methods = NULL,
                .defines = moduledefs,
                .globals = NULL,
            };

            @HPy_MODINIT(moduledef)
        """)
        assert mod.data == [42]

    def test_HPyModule_custom_create_returns_non_module(self):
        """
        Module that defines create slot that returns non module object. This
        is, for the time being, the only supported way to implement the module
        'create' slot. HPy intentionally does not expose direct API to create
        a module object. Module objects are created for the extension by the
        runtime and the extension can only populate that module object in the
        init slots.
        """
        mod = self.make_module("""
            HPyDef_SLOT(create, HPy_mod_create)
            static HPy create_impl(HPyContext *ctx, HPy spec)
            {
                HPy result = HPy_NULL, dict = HPy_NULL, ns_type = HPy_NULL;

                HPy types = HPyImport_ImportModule(ctx, "types");
                if (HPy_IsNull(types))
                    return HPy_NULL;

                ns_type = HPy_GetAttr_s(ctx, types, "SimpleNamespace");
                if (HPy_IsNull(types))
                    goto cleanup;
                dict = HPyDict_New(ctx);
                HPy_SetItem_s(ctx, dict, "spec", spec);
                result = HPy_CallTupleDict(ctx, ns_type, HPy_NULL, dict);
                if (HPy_IsNull(result))
                    goto cleanup;

            cleanup:
                HPy_Close(ctx, dict);
                HPy_Close(ctx, types);
                HPy_Close(ctx, ns_type);
                return result;
            }

            static HPyDef *moduledefs[] = {
                &create,
                NULL
            };

            static HPyModuleDef moduledef = {
                .doc = NULL,
                .size = 0,
                .legacy_methods = NULL,
                .defines = moduledefs,
                .globals = NULL,
            };

            @HPy_MODINIT(moduledef)
        """)
        assert isinstance(mod, types.SimpleNamespace)
        assert mod.spec is mod.__spec__

    def test_HPyModule_error_when_create_returns_module(self):
        """
        The HPy_mod_create slot cannot return a builtin module object.
        HPy does not expose any API to create builtin module objects and, until
        there are any actual use-cases, the purpose of the 'create' slot is to
        create non-builtin-module objects.
        """
        expected_message = "HPy_mod_create slot returned a builtin module " \
                           "object. This is currently not supported."
        with pytest.raises(SystemError, match=expected_message):
            self.make_module("""
                HPyDef_SLOT(create, HPy_mod_create)
                static HPy create_impl(HPyContext *ctx, HPy spec)
                {
                    return HPyImport_ImportModule(ctx, "types");
                }

                static HPyDef *moduledefs[] = {
                    &create,
                    NULL
                };

                static HPyModuleDef moduledef = {
                    .doc = NULL,
                    .size = 0,
                    .legacy_methods = NULL,
                    .defines = moduledefs,
                    .globals = NULL,
                };

                @HPy_MODINIT(moduledef)
            """)

    def test_HPyModule_create_raises(self):
        with pytest.raises(RuntimeError, match="Test error"):
            self.make_module("""
                HPyDef_SLOT(create, HPy_mod_create)
                static HPy create_impl(HPyContext *ctx, HPy spec)
                {
                    HPyErr_SetString(ctx, ctx->h_RuntimeError, "Test error");
                    return HPy_NULL;
                }

                static HPyDef *moduledefs[] = {
                    &create,
                    NULL
                };

                static HPyModuleDef moduledef = {
                    .doc = NULL,
                    .size = 0,
                    .legacy_methods = NULL,
                    .defines = moduledefs,
                    .globals = NULL,
                };

                @HPy_MODINIT(moduledef)
            """)

    def test_HPyModule_create_and_nondefault_values(self):
        expected_message = r'^HPyModuleDef defines a HPy_mod_create slot.*'
        with pytest.raises(SystemError, match=expected_message):
            self.make_module("""
                HPyDef_SLOT(create, HPy_mod_create)
                static HPy create_impl(HPyContext *ctx, HPy spec)
                {
                    HPyErr_SetString(ctx, ctx->h_RuntimeError, "Test error");
                    return HPy_NULL;
                }

                static HPyDef *moduledefs[] = {
                    &create,
                    NULL
                };

                static HPyModuleDef moduledef = {
                    .doc = "Some doc - this is non-default",
                    .size = 0,
                    .legacy_methods = NULL,
                    .defines = moduledefs,
                    .globals = NULL,
                };

                @HPy_MODINIT(moduledef)
            """)

    def test_HPyModule_create_and_exec_slots(self):
        expected_message = r'^HPyModuleDef defines a HPy_mod_create slot.*'
        with pytest.raises(SystemError, match=expected_message):
            self.make_module("""
                HPyDef_SLOT(create, HPy_mod_create)
                static HPy create_impl(HPyContext *ctx, HPy spec)
                {
                    HPyErr_SetString(ctx, ctx->h_RuntimeError, "Test error");
                    return HPy_NULL;
                }

                HPyDef_SLOT(exec, HPy_mod_exec)
                static int exec_impl(HPyContext *ctx, HPy mod)
                {
                    return 0;
                }

                static HPyDef *moduledefs[] = {
                    &create,
                    &exec,
                    NULL
                };

                static HPyModuleDef moduledef = {
                    .doc = NULL,
                    .size = 0,
                    .legacy_methods = NULL,
                    .defines = moduledefs,
                    .globals = NULL,
                };

                @HPy_MODINIT(moduledef)
            """)

    def test_HPyModule_negative_size(self):
        """
        The simplest fully declarative module creation.
        """
        expected_message = "HPy does not permit HPyModuleDef.size < 0"
        with pytest.raises(SystemError, match=expected_message):
            self.make_module("""
                HPyDef_METH(f, "f", HPyFunc_NOARGS)
                static HPy f_impl(HPyContext *ctx, HPy self)
                {
                    return HPyLong_FromLong(ctx, 42);
                }

                static HPyDef *moduledefs[] = { &f, NULL };
                static HPyModuleDef moduledef = {
                    .doc = "Some doc",
                    .size = -1,
                    .legacy_methods = NULL,
                    .defines = moduledefs,
                    .globals = NULL,
                };

                @HPy_MODINIT(moduledef)
            """)
