

class PyList extends PySequence {

    PyList(PyObject[] x) {
        super(x);
    }

    PyObject op_setitem(PyObject index, PyObject o) {
        if (index instanceof PyInt) {
            int i = ((PyInt) index).intval;
            items[i] = o;
            return null;
        }
        throw new TypeError();
    }

    PyObject op_add(PyObject other) {
        if (other instanceof PyList) {
            PyObject[] items2 = ((PyList) other).items;
            PyObject[] nitems = new PyObject[items.length + items2.length];
            System.arraycopy(items, 0, nitems, 0, items.length);
            System.arraycopy(items2, 0, nitems, items.length, items2.length);
            return new PyList(nitems);
        }
        throw new TypeError();
    }

    PyObject op_inplace_add(PyObject other) {
        if (other instanceof PySequence) {
            PyObject[] items2 = ((PySequence) other).items;
            PyObject[] nitems = new PyObject[items.length + items2.length];
            System.arraycopy(items, 0, nitems, 0, items.length);
            System.arraycopy(items2, 0, nitems, items.length, items2.length);
            items = nitems;
            return this;
        }
        throw new TypeError();
    }

    PyObject op_mul(PyObject other) {
        if (items.length == 1 && other instanceof PyInt) {
            int i, count = ((PyInt) other).intval;
            PyObject item = items[0];
            PyObject[] nitems = new PyObject[count];
            for (i=0; i<count; i++)
                nitems[i] = item;
            return new PyList(nitems);
        }
        throw new TypeError();
    }

    PyObject op_inplace_mul(PyObject other) {
        if (items.length == 1 && other instanceof PyInt) {
            int i, count = ((PyInt) other).intval;
            PyObject item = items[0];
            PyObject[] nitems = new PyObject[count];
            for (i=0; i<count; i++)
                nitems[i] = item;
            items = nitems;
            return this;
        }
        throw new TypeError();
    }

    PyObject meth_append(PyObject item) {
        PyObject[] nitems = new PyObject[items.length + 1];
        System.arraycopy(items, 0, nitems, 0, items.length);
        nitems[items.length] = item;
        items = nitems;
        return null;
    }

};
