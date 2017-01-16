from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.cparser import parse_source

def test_configure():
    decl = """
    typedef ssize_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        double ob_fval;
    } TestFloatObject;
    """
    res = parse_source(decl)
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
    cdef2 = """
    typedef struct {
        PyObject_HEAD
        Py_ssize_t ob_foo;
        Type *type;
    } Object;
    """
    hdr1 = parse_source(cdef1)
    Type = hdr1.definitions['Type']
    assert isinstance(Type, lltype.Struct)
    hdr2 = parse_source(cdef2, includes=[hdr1])
    assert 'Type' not in hdr2.definitions
    Object = hdr2.definitions['Object']
    assert Object.c_type.TO is Type

def test_incomplete():
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
    foo_h = parse_source(cdef)
    Object = foo_h.gettype('Object')
    assert isinstance(Object, lltype.Struct)

def test_recursive():
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
    foo_h = parse_source(cdef)
    Object = foo_h.definitions['Object']
    assert isinstance(Object, lltype.Struct)
    hash(Object)

def test_const():
    cdef = """
    typedef struct {
        const char * const foo;
    } bar;
    """
    hdr = parse_source(cdef)
    assert hdr.definitions['bar'].c_foo == rffi.CONST_CCHARP != rffi.CCHARP

def test_gettype():
    decl = """
    typedef ssize_t Py_ssize_t;

    #define PyObject_HEAD  \
        Py_ssize_t ob_refcnt;        \
        Py_ssize_t ob_pypy_link;     \

    typedef struct {
        PyObject_HEAD
        double ob_fval;
    } TestFloatObject;
    """
    res = parse_source(decl)
    assert res.gettype('Py_ssize_t') == rffi.SSIZE_T
    assert res.gettype('TestFloatObject *').TO.c_ob_refcnt == rffi.SSIZE_T

def test_parse_funcdecl():
    decl = """
    typedef ssize_t Py_ssize_t;

    #define PyObject_HEAD  \
        Py_ssize_t ob_refcnt;        \
        Py_ssize_t ob_pypy_link;     \

    typedef struct {
        PyObject_HEAD
        double ob_fval;
    } TestFloatObject;

    typedef TestFloatObject* (*func_t)(int, int);
    """
    res = parse_source(decl)
    name, FUNC = res.parse_func("func_t some_func(TestFloatObject*)")
    assert name == 'some_func'
    assert FUNC.RESULT == res.gettype('func_t')
    assert FUNC.ARGS == (res.gettype('TestFloatObject *'),)
