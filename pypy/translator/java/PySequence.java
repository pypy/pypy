

class PySequence extends PyObject {

    PyObject[] items;

    PySequence(PyObject[] x) {
        items = x;
    }

    boolean is_true() {
        return items.length != 0;
    }

    int len() {
        return items.length;
    }

    PyObject op_getitem(PyObject index) {
        if (index instanceof PyInt) {
            int i = ((PyInt) index).intval;
            return items[i];
        }
        throw new TypeError();
    }

    PyObject[] unpack(int expected_length, PyObject[] defaults) {
        int missing = expected_length - items.length;
        if (missing == 0)
            return items;
        if (defaults == null || missing < 0 || missing > defaults.length) {
            throw new TypeError();
        }
        PyObject[] result = new PyObject[expected_length];
        System.arraycopy(items, 0, result, 0, items.length);
        System.arraycopy(defaults, defaults.length-missing,
                         result, items.length, missing);
        return result;
    }

};
