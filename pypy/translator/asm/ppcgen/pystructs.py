class PyVarObject(object):
    ob_size = 8

class PyObject(object):
    ob_refcnt = 0
    ob_type = 4

class PyTupleObject(object):
    ob_item = 12

class PyTypeObject(object):
    tp_name = 12
    tp_basicsize = 16
    tp_itemsize = 20
    tp_dealloc = 24

class PyFloatObject(object):
    ob_fval = 8

class PyIntObject(object):
    ob_ival = 8

