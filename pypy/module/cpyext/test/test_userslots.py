from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.pyobject import make_ref, from_ref
from pypy.module.cpyext.api import generic_cpy_call
from pypy.module.cpyext.typeobject import PyTypeObjectPtr


class TestAppLevelObject(BaseApiTest):
    def test_nb_add_from_python(self, space, api):
        w_date = space.appexec([], """():
            class DateType(object):
                def __add__(self, other):
                    return 'sum!'
            return DateType()
            """)
        w_datetype = space.type(w_date)
        py_date = make_ref(space, w_date)
        py_datetype = rffi.cast(PyTypeObjectPtr, make_ref(space, w_datetype))
        assert py_datetype.c_tp_as_number
        assert py_datetype.c_tp_as_number.c_nb_add
        w_obj = generic_cpy_call(space, py_datetype.c_tp_as_number.c_nb_add,
                                 py_date, py_date)
        assert space.str_w(w_obj) == 'sum!'

    def test_tp_hash_from_python(self, space, api):
        w_c = space.appexec([], """():
            class C:
                def __hash__(self):
                    return -23
            return C()
        """)
        w_ctype = space.type(w_c)
        py_c = make_ref(space, w_c)
        py_ctype = rffi.cast(PyTypeObjectPtr, make_ref(space, w_ctype))
        assert py_ctype.c_tp_hash
        val = generic_cpy_call(space, py_ctype.c_tp_hash, py_c)
        assert val == -23

    def test_tp_new_from_python(self, space, api):
        w_date = space.appexec([], """():
            class Date(object):
                def __new__(cls, year, month, day):
                    self = object.__new__(cls)
                    self.year = year
                    self.month = month
                    self.day = day
                    return self
            return Date
            """)
        py_datetype = rffi.cast(PyTypeObjectPtr, make_ref(space, w_date))
        one = space.newint(1)
        arg = space.newtuple([one, one, one])
        # call w_date.__new__
        w_obj = space.call_function(w_date, one, one, one)
        w_year = space.getattr(w_obj, space.newbytes('year'))
        assert space.int_w(w_year) == 1

        w_obj = generic_cpy_call(space, py_datetype.c_tp_new, py_datetype, 
                                 arg, space.newdict({}))
        w_year = space.getattr(w_obj, space.newbytes('year'))
        assert space.int_w(w_year) == 1


