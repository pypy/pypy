

class PyObject {

    static PyBool Py_False = new PyBool(false);
    static PyBool Py_True  = new PyBool(true);

    boolean is_true() { return true; }
    PyObject op_is_true() { return new PyBool(is_true()); }

    boolean eq(PyObject other) { return this == other; }
    boolean lt(PyObject other) { throw new TypeError(); }
    PyObject op_lt(PyObject other) { return new PyBool(lt(other)); }
    PyObject op_le(PyObject other) { return new PyBool(!other.lt(this)); }
    PyObject op_eq(PyObject other) { return new PyBool(eq(other)); }
    PyObject op_ne(PyObject other) { return new PyBool(!eq(other)); }
    PyObject op_gt(PyObject other) { return new PyBool(other.lt(this)); }
    PyObject op_ge(PyObject other) { return new PyBool(!lt(other)); }

    PyObject op_neg() { throw new TypeError(); }
    PyObject op_add(PyObject other) { throw new TypeError(); }
    PyObject op_sub(PyObject other) { throw new TypeError(); }
    PyObject op_mul(PyObject other) { throw new TypeError(); }
    PyObject op_inplace_add(PyObject other) { return op_add(other); }
    PyObject op_inplace_sub(PyObject other) { return op_sub(other); }
    PyObject op_inplace_mul(PyObject other) { return op_mul(other); }

    int len() { throw new TypeError(); }
    PyObject op_len() { return new PyInt(len()); }
    PyObject op_getitem(PyObject index) { throw new TypeError(); }
    PyObject op_setitem(PyObject index, PyObject o) { throw new TypeError(); }
    PyObject[] unpack(int expected_length, PyObject[] defaults) {
        throw new TypeError();
    }

    /* CUT HERE -- automatically generated code below this line */
    PyObject meth_append_1(PyObject x) {
        return op_getattr_append().op_call_1(x);
    }
    PyObject op_getattr_append() { throw new TypeError(); }
    PyObject op_call_0() { throw new TypeError(); }
    PyObject op_call_1(PyObject x) { throw new TypeError(); }
    PyObject op_call_0_5tar(PyObject stararg) { throw new TypeError(); }
};
