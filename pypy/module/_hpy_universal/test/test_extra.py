"""
This file contains extra hpy tests in addition to the ones which are in
test/_vendored.

The idea is that during development, sometimes it is useful to write tests
about certain specific features/code paths/corner cases which are not covered
(yet!) by the official hpy tests, so this is a place to collect them.

Once the development phase is finished, please move these tests to the main
hpy repo, and then copy them back here via ./update_vendored.sh.
"""

from pypy.module._hpy_universal.test._vendored.support import HPyTest

class TestExtra(HPyTest):
    pass

    """
    Additional tests to write:

      - check the .readonly field of HPyDef_MEMBER (and also the corresponding
        flag for the PyMemberDef cpy_compat case)


    ListBuilder:

      - in the C code there is logic to delay the MemoryError until we call
        ListBuilder_Build, but it is not tested

      - ListBuilder_Cancel is not tested

    """



class TestExtraCPythonCompatibility(HPyTest):
    # these tests are run with cpyext support, see conftest.py

    # this is like the original test_legacy_slots_repr, but it also tests
    # nb_add (which is interesting since it's another function type, and it's
    # not a 'direct' tp_* slot but it's inside PyNumberMethods
    def test_legacy_slots(self):
        mod = self.make_module("""
            #include <Python.h>

            static PyObject *Dummy_repr(PyObject *self)
            {
                return PyUnicode_FromString("myrepr");
            }

            static PyObject *Dummy_add(PyObject *self, PyObject *other)
            {
                return Py_BuildValue("OO", self, other);
            }

            HPyDef_SLOT(Dummy_abs, Dummy_abs_impl, HPy_nb_absolute);
            static HPy Dummy_abs_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            static HPyDef *Dummy_defines[] = {
                &Dummy_abs,
                NULL
            };
            static PyType_Slot Dummy_type_slots[] = {
                {Py_tp_repr, Dummy_repr},
                {Py_nb_add, Dummy_add},
                {0, 0},
            };
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .legacy_slots = Dummy_type_slots,
                .defines = Dummy_defines
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert repr(d) == 'myrepr'
        assert d + 42 == (d, 42)
        assert abs(d) == 1234
