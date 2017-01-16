from rpython.flowspace.model import const
from rpython.flowspace.objspace import build_flow
from rpython.translator.simplify import simplify_graph
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.cparser import parse_source, CTypeSpace

def test_configure():
    decl = """
    typedef ssize_t Py_ssize_t;

    typedef struct {
        Py_ssize_t ob_refcnt;
        Py_ssize_t ob_pypy_link;
        double ob_fval;
    } TestFloatObject;
    """
    cts = parse_source(decl)
    TestFloatObject = cts.definitions['TestFloatObject']
    assert isinstance(TestFloatObject, lltype.Struct)
    assert TestFloatObject.c_ob_refcnt == rffi.SSIZE_T
    assert TestFloatObject.c_ob_pypy_link == rffi.SSIZE_T
    assert TestFloatObject.c_ob_fval == rffi.DOUBLE

def test_simple():
    decl = "typedef ssize_t Py_ssize_t;"
    cts = parse_source(decl)
    assert cts.definitions == {'Py_ssize_t': rffi.SSIZE_T}

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
    cts = parse_source(decl)
    assert 'PyFloatObject' in cts.definitions
    assert 'PyObject_HEAD' in cts.macros

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
    cts1 = parse_source(cdef1)
    Type = cts1.definitions['Type']
    assert isinstance(Type, lltype.Struct)
    cts2 = parse_source(cdef2, includes=[cts1])
    assert 'Type' not in cts2.definitions
    Object = cts2.definitions['Object']
    assert Object.c_type.TO is Type

def test_multiple_sources():
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
    cts = CTypeSpace()
    cts.parse_source(cdef1)
    Type = cts.definitions['Type']
    assert isinstance(Type, lltype.Struct)
    assert 'Object' not in cts.definitions
    cts.parse_source(cdef2)
    Object = cts.definitions['Object']
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
    cts = parse_source(cdef)
    Object = cts.gettype('Object')
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
    cts = parse_source(cdef)
    Object = cts.definitions['Object']
    assert isinstance(Object, lltype.Struct)
    hash(Object)

def test_const():
    cdef = """
    typedef struct {
        const char * const foo;
    } bar;
    """
    cts = parse_source(cdef)
    assert cts.definitions['bar'].c_foo == rffi.CONST_CCHARP != rffi.CCHARP

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
    cts = parse_source(decl)
    assert cts.gettype('Py_ssize_t') == rffi.SSIZE_T
    assert cts.gettype('TestFloatObject *').TO.c_ob_refcnt == rffi.SSIZE_T
    assert cts.cast('Py_ssize_t', 42) == rffi.cast(rffi.SSIZE_T, 42)

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
    cts = parse_source(decl)
    name, FUNC = cts.parse_func("func_t some_func(TestFloatObject*)")
    assert name == 'some_func'
    assert FUNC.RESULT == cts.gettype('func_t')
    assert FUNC.ARGS == (cts.gettype('TestFloatObject *'),)

def test_translate_cast():
    cdef = "typedef ssize_t Py_ssize_t;"
    cts = parse_source(cdef)

    def f():
        return cts.cast('Py_ssize_t*', 0)
    graph = build_flow(f)
    simplify_graph(graph)
    assert len(graph.startblock.operations) == 1
    op = graph.startblock.operations[0]
    assert op.args[0] == const(rffi.cast)
    assert op.args[1].value is cts.gettype('Py_ssize_t*')

def test_translate_gettype():
    cdef = "typedef ssize_t Py_ssize_t;"
    cts = parse_source(cdef)

    def f():
        return cts.gettype('Py_ssize_t*')
    graph = build_flow(f)
    simplify_graph(graph)
    # Check that the result is constant-folded
    assert graph.startblock.operations == []
    [link] = graph.startblock.exits
    assert link.target is graph.returnblock
    assert link.args[0] == const(rffi.CArrayPtr(rffi.SSIZE_T))
