

class PyTuple extends PySequence {

    PyTuple(PyObject[] x) {
        super(x);
    }

    PyObject op_add(PyObject other) {
        if (other instanceof PyTuple) {
            PyObject[] items2 = ((PyTuple) other).items;
            PyObject[] nitems = new PyObject[items.length + items2.length];
            System.arraycopy(items, 0, nitems, 0, items.length);
            System.arraycopy(items2, 0, nitems, items.length, items2.length);
            return new PyTuple(nitems);
        }
        throw new TypeError();
    }

};
