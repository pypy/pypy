
class builtin_len extends PyObject {
    PyObject op_simple_call(PyObject x)
    {
        return new PyInt(x.len());
    }
}

class Builtin {

    static PyObject len = new builtin_len();

}
