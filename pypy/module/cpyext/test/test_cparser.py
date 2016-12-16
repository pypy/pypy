from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.cparser import Parser, cname_to_lltype

def test_simple():
    decl = """
    typedef intptr_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        double ob_fval;
    } PyFloatObject;
    """
    ctx = Parser()
    ctx.parse(decl)
    obj = ctx._declarations['typedef PyFloatObject'][0]
    assert [cname_to_lltype(tp.name) for tp in obj.fldtypes] == [
        rffi.INTPTR_T, rffi.INTPTR_T, rffi.DOUBLE]
