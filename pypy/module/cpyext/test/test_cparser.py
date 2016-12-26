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
    TestFloatObject = res.definitions['TestFloatObject']
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

def test_include(tmpdir):
    cdef1 = """
    typedef ssize_t Py_ssize_t;

    #define PyObject_HEAD  \
        Py_ssize_t ob_refcnt;        \
        Py_ssize_t ob_pypy_link;     \

    typedef struct {
        char *name;
    } Type;
    """
    base_name = tmpdir / 'base.h'
    base_name.write(cdef1)
    cdef2 = """
    typedef struct {
        PyObject_HEAD
        Py_ssize_t ob_foo;
        Type *type;
    } Object;
    """
    (tmpdir / 'object.h').write(cdef2)
    eci = ExternalCompilationInfo(
        include_dirs=[str(tmpdir)],
        includes=['sys/types.h', 'base.h', 'object.h'])
    hdr1 = parse_source(cdef1, eci=eci)
    hdr1.configure_types()
    Type = hdr1.definitions['Type']
    assert isinstance(Type, lltype.Struct)
    hdr2 = parse_source(cdef2, includes=[hdr1], eci=eci)
    hdr2.configure_types()
    assert 'Type' not in hdr2.definitions
    Object = hdr2.definitions['Object']
    assert Object.c_type.TO is Type

def test_incomplete(tmpdir):
    cdef = """
    typedef ssize_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        struct _typeobject *ob_type;
    } Object;

    typedef struct {
        void *buf;
        Object *obj;
    } Buffer;

    """
    (tmpdir / 'foo.h').write(cdef)
    eci = ExternalCompilationInfo(
        include_dirs=[str(tmpdir)],
        includes=['sys/types.h', 'foo.h'])
    foo_h = parse_source(cdef, eci=eci)
    foo_h.configure_types()
    Object = foo_h.definitions['Object']
    assert isinstance(Object, lltype.ForwardReference) or hash(Object)

def test_recursive(tmpdir):
    cdef = """
    typedef ssize_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        struct _typeobject *ob_type;
    } Object;

    typedef struct {
        void *buf;
        Object *obj;
    } Buffer;

    typedef struct _typeobject {
        Object *obj;
    } Type;
    """
    (tmpdir / 'foo.h').write(cdef)
    eci = ExternalCompilationInfo(
        include_dirs=[str(tmpdir)],
        includes=['sys/types.h', 'foo.h'])
    foo_h = parse_source(cdef, eci=eci)
    foo_h.configure_types()
    Object = foo_h.definitions['Object']
    assert isinstance(Object, lltype.Struct)
    hash(Object)
