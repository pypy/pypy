from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from pypy.module.cpyext.cparser import parse_source

def test_configure(tmpdir):
    decl = """
    typedef ssize_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        double ob_fval;
    } TestFloatObject;
    """
    hdr = tmpdir / 'header.h'
    hdr.write(decl)
    eci = ExternalCompilationInfo(
        include_dirs=[str(tmpdir)], includes=['sys/types.h', 'header.h'])
    res = parse_source(decl, eci=eci)
    res.configure_types()
    TestFloatObject = res.definitions['TestFloatObject'].OF
    assert isinstance(TestFloatObject, lltype.Struct)
    assert TestFloatObject.c_ob_refcnt == rffi.SSIZE_T
    assert TestFloatObject.c_ob_pypy_link == rffi.SSIZE_T
    assert TestFloatObject.c_ob_fval == rffi.DOUBLE

def test_simple():
    decl = "typedef ssize_t Py_ssize_t;"
    hdr = parse_source(decl)
    assert hdr.definitions == {'Py_ssize_t': rffi.SSIZE_T}

def test_macro():
    decl = """
    typedef ssize_t Py_ssize_t;

    #define PyObject_HEAD  \
        Py_ssize_t ob_refcnt;        \
        Py_ssize_t ob_pypy_link;     \

    typedef struct {
        PyObject_HEAD
        double ob_fval;
    } PyFloatObject;
    """
    hdr = parse_source(decl)
    assert 'PyFloatObject' in hdr.definitions
    assert 'PyObject_HEAD' in hdr.macros

def test_include():
    cdef1 = """
    typedef ssize_t Py_ssize_t;

    #define PyObject_HEAD  \
        Py_ssize_t ob_refcnt;        \
        Py_ssize_t ob_pypy_link;     \

    typedef struct {
        char *name;
    } Type;
    """
    hdr1 = parse_source(cdef1)
    cdef2 = """
    typedef struct {
        PyObject_HEAD
        Py_ssize_t ob_foo;
        Type *type;
    } Object;
    """
    hdr2 = parse_source(cdef2, includes=[hdr1])
    assert 'Object' in hdr2.definitions
    assert 'Type' not in hdr2.definitions
