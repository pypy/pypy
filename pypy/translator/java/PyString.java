

class PyString extends PyObject {

    String string;

    PyString(String data) {
        string = data;
    }

    boolean is_true() {
        return string.length() != 0;
    }

    int len() {
        return string.length();
    }

    boolean eq(PyObject other) {
        if (other instanceof PyString)
            return string.equals(((PyString) other).string);
        else
            return false;
    }

    boolean lt(PyObject other) {
        if (other instanceof PyString)
            return string.compareTo(((PyString) other).string) < 0;
        else
            throw new TypeError();
    }

    PyObject op_getitem(PyObject index) {
        if (index instanceof PyInt) {
            int i = ((PyInt) index).intval;
            return new PyString(string.substring(i, i+1));
        }
        throw new TypeError();
    }

    PyObject op_add(PyObject other) {
        if (other instanceof PyString) {
            return new PyString(string.concat(((PyString) other).string));
        }
        throw new TypeError();
    }

};
