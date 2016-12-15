from pypy.module.cpyext.cparser import Parser

def test_simple():
    decl = """
    typedef intptr_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        struct _typeobject *ob_type;
        double ob_fval;
    } PyFloatObject;
    """
    ctx = Parser()
    ctx.parse(decl)
