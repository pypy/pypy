

class PyInt extends PyObject {

    int intval;
    
    PyInt(int x) {
        intval = x;
    }

    boolean is_true() {
        return intval != 0;
    }

    boolean eq(PyObject other) {
        if (other instanceof PyInt)
            return intval == ((PyInt) other).intval;
        else
            return false;
    }

    boolean lt(PyObject other) {
        if (other instanceof PyInt)
            return intval < ((PyInt) other).intval;
        else
            throw new TypeError();
    }

    PyObject op_neg() {
        return new PyInt(-intval);
    }

    PyObject op_add(PyObject other) {
        if (other instanceof PyInt)
            return new PyInt(intval + ((PyInt) other).intval);
        else
            throw new TypeError();
    }

    PyObject op_sub(PyObject other) {
        if (other instanceof PyInt)
            return new PyInt(intval - ((PyInt) other).intval);
        else
            throw new TypeError();
    }

};
