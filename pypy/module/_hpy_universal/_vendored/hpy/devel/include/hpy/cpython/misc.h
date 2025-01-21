#ifndef HPY_CPYTHON_MISC_H
#define HPY_CPYTHON_MISC_H

#include <Python.h>
#include "hpy.h"
#include "hpy/runtime/ctx_funcs.h"

static inline PyObject* _h2py(HPy h) {
    return (PyObject*) h._i;
}

static inline HPy _py2h(PyObject *o) {
    return _hconv((intptr_t)o);
}

static inline HPyThreadState _threads2h(PyThreadState *s) {
    return _htsconv((intptr_t)s);
}

static inline PyThreadState* _h2threads(HPyThreadState h) {
    return (PyThreadState*) h._i;
}

static inline HPyField _py2hf(PyObject *obj)
{
    HPy h = _py2h(obj);
    return _hfconv( ._i = h._i );
}

static inline PyObject * _hf2py(HPyField hf)
{
    HPy h = { ._i = hf._i };
    return _h2py(h);
}

static inline HPyGlobal _py2hg(PyObject *obj)
{
    HPy h = _py2h(obj);
    return _hgconv(._i = h._i);
}

static inline PyObject * _hg2py(HPyGlobal hf)
{
    HPy h = { ._i = hf._i };
    return _h2py(h);
}

static inline const HPy *_arr_py2h(PyObject *const *py_arr) {
    assert(sizeof(HPy) == sizeof(PyObject *));
    return (const HPy *)py_arr;
}

/* XXX! should be defined only once, not once for every .c! */
static struct _HPyContext_s _global_ctx;

HPyAPI_FUNC HPyContext * _HPyGetContext(void) {
    HPyContext *ctx = &_global_ctx;
    if (!ctx->name) {
        ctx->name = "HPy CPython ABI";
        ctx->abi_version = HPY_ABI_VERSION;
        /* Constants */
        ctx->h_None = _py2h(Py_None);
        ctx->h_True = _py2h(Py_True);
        ctx->h_False = _py2h(Py_False);
        ctx->h_NotImplemented = _py2h(Py_NotImplemented);
        ctx->h_Ellipsis = _py2h(Py_Ellipsis);
        /* Exceptions */
        ctx->h_BaseException = _py2h(PyExc_BaseException);
        ctx->h_Exception = _py2h(PyExc_Exception);
        ctx->h_StopAsyncIteration = _py2h(PyExc_StopAsyncIteration);
        ctx->h_StopIteration = _py2h(PyExc_StopIteration);
        ctx->h_GeneratorExit = _py2h(PyExc_GeneratorExit);
        ctx->h_ArithmeticError = _py2h(PyExc_ArithmeticError);
        ctx->h_LookupError = _py2h(PyExc_LookupError);
        ctx->h_AssertionError = _py2h(PyExc_AssertionError);
        ctx->h_AttributeError = _py2h(PyExc_AttributeError);
        ctx->h_BufferError = _py2h(PyExc_BufferError);
        ctx->h_EOFError = _py2h(PyExc_EOFError);
        ctx->h_FloatingPointError = _py2h(PyExc_FloatingPointError);
        ctx->h_OSError = _py2h(PyExc_OSError);
        ctx->h_ImportError = _py2h(PyExc_ImportError);
        ctx->h_ModuleNotFoundError = _py2h(PyExc_ModuleNotFoundError);
        ctx->h_IndexError = _py2h(PyExc_IndexError);
        ctx->h_KeyError = _py2h(PyExc_KeyError);
        ctx->h_KeyboardInterrupt = _py2h(PyExc_KeyboardInterrupt);
        ctx->h_MemoryError = _py2h(PyExc_MemoryError);
        ctx->h_NameError = _py2h(PyExc_NameError);
        ctx->h_OverflowError = _py2h(PyExc_OverflowError);
        ctx->h_RuntimeError = _py2h(PyExc_RuntimeError);
        ctx->h_RecursionError = _py2h(PyExc_RecursionError);
        ctx->h_NotImplementedError = _py2h(PyExc_NotImplementedError);
        ctx->h_SyntaxError = _py2h(PyExc_SyntaxError);
        ctx->h_IndentationError = _py2h(PyExc_IndentationError);
        ctx->h_TabError = _py2h(PyExc_TabError);
        ctx->h_ReferenceError = _py2h(PyExc_ReferenceError);
        ctx->h_SystemError = _py2h(PyExc_SystemError);
        ctx->h_SystemExit = _py2h(PyExc_SystemExit);
        ctx->h_TypeError = _py2h(PyExc_TypeError);
        ctx->h_UnboundLocalError = _py2h(PyExc_UnboundLocalError);
        ctx->h_UnicodeError = _py2h(PyExc_UnicodeError);
        ctx->h_UnicodeEncodeError = _py2h(PyExc_UnicodeEncodeError);
        ctx->h_UnicodeDecodeError = _py2h(PyExc_UnicodeDecodeError);
        ctx->h_UnicodeTranslateError = _py2h(PyExc_UnicodeTranslateError);
        ctx->h_ValueError = _py2h(PyExc_ValueError);
        ctx->h_ZeroDivisionError = _py2h(PyExc_ZeroDivisionError);
        ctx->h_BlockingIOError = _py2h(PyExc_BlockingIOError);
        ctx->h_BrokenPipeError = _py2h(PyExc_BrokenPipeError);
        ctx->h_ChildProcessError = _py2h(PyExc_ChildProcessError);
        ctx->h_ConnectionError = _py2h(PyExc_ConnectionError);
        ctx->h_ConnectionAbortedError = _py2h(PyExc_ConnectionAbortedError);
        ctx->h_ConnectionRefusedError = _py2h(PyExc_ConnectionRefusedError);
        ctx->h_ConnectionResetError = _py2h(PyExc_ConnectionResetError);
        ctx->h_FileExistsError = _py2h(PyExc_FileExistsError);
        ctx->h_FileNotFoundError = _py2h(PyExc_FileNotFoundError);
        ctx->h_InterruptedError = _py2h(PyExc_InterruptedError);
        ctx->h_IsADirectoryError = _py2h(PyExc_IsADirectoryError);
        ctx->h_NotADirectoryError = _py2h(PyExc_NotADirectoryError);
        ctx->h_PermissionError = _py2h(PyExc_PermissionError);
        ctx->h_ProcessLookupError = _py2h(PyExc_ProcessLookupError);
        ctx->h_TimeoutError = _py2h(PyExc_TimeoutError);
        /* Warnings */
        ctx->h_Warning = _py2h(PyExc_Warning);
        ctx->h_UserWarning = _py2h(PyExc_UserWarning);
        ctx->h_DeprecationWarning = _py2h(PyExc_DeprecationWarning);
        ctx->h_PendingDeprecationWarning = _py2h(PyExc_PendingDeprecationWarning);
        ctx->h_SyntaxWarning = _py2h(PyExc_SyntaxWarning);
        ctx->h_RuntimeWarning = _py2h(PyExc_RuntimeWarning);
        ctx->h_FutureWarning = _py2h(PyExc_FutureWarning);
        ctx->h_ImportWarning = _py2h(PyExc_ImportWarning);
        ctx->h_UnicodeWarning = _py2h(PyExc_UnicodeWarning);
        ctx->h_BytesWarning = _py2h(PyExc_BytesWarning);
        ctx->h_ResourceWarning = _py2h(PyExc_ResourceWarning);
        /* Types */
        ctx->h_BaseObjectType = _py2h((PyObject *)&PyBaseObject_Type);
        ctx->h_TypeType = _py2h((PyObject *)&PyType_Type);
        ctx->h_BoolType = _py2h((PyObject *)&PyBool_Type);
        ctx->h_LongType = _py2h((PyObject *)&PyLong_Type);
        ctx->h_FloatType = _py2h((PyObject *)&PyFloat_Type);
        ctx->h_UnicodeType = _py2h((PyObject *)&PyUnicode_Type);
        ctx->h_TupleType = _py2h((PyObject *)&PyTuple_Type);
        ctx->h_ListType = _py2h((PyObject *)&PyList_Type);
        ctx->h_ComplexType = _py2h((PyObject *)&PyComplex_Type);
        ctx->h_BytesType = _py2h((PyObject *)&PyBytes_Type);
        ctx->h_MemoryViewType = _py2h((PyObject *)&PyMemoryView_Type);
        ctx->h_CapsuleType = _py2h((PyObject *)&PyCapsule_Type);
        ctx->h_SliceType = _py2h((PyObject *)&PySlice_Type);
        ctx->h_DictType = _py2h((PyObject *)&PyDict_Type);
        /* Reflection */
        ctx->h_Builtins = _py2h(PyEval_GetBuiltins());
    }
    return ctx;
}

HPyAPI_FUNC HPy HPy_Dup(HPyContext *ctx, HPy handle)
{
    Py_XINCREF(_h2py(handle));
    return handle;
}

HPyAPI_FUNC void HPy_Close(HPyContext *ctx, HPy handle)
{
    Py_XDECREF(_h2py(handle));
}

HPyAPI_FUNC void HPyField_Store(HPyContext *ctx, HPy target_obj,
                                HPyField *target_field, HPy h)
{
    PyObject *obj = _h2py(h);
    PyObject *target_py_obj = _hf2py(*target_field);
    Py_XINCREF(obj);
    *target_field = _py2hf(obj);
    Py_XDECREF(target_py_obj);
}

HPyAPI_FUNC HPy HPyField_Load(HPyContext *ctx, HPy source_obj, HPyField source_field)
{
    PyObject *obj = _hf2py(source_field);
    Py_INCREF(obj);
    return _py2h(obj);
}

HPyAPI_FUNC void HPyGlobal_Store(HPyContext *ctx, HPyGlobal *global, HPy h)
{
    PyObject *obj = _h2py(h);
    Py_XDECREF(_hg2py(*global));
    Py_XINCREF(obj);
    *global = _py2hg(obj);
}

HPyAPI_FUNC HPy HPyGlobal_Load(HPyContext *ctx, HPyGlobal global)
{
    PyObject *obj = _hg2py(global);
    Py_INCREF(obj);
    return _py2h(obj);
}

HPyAPI_FUNC HPy HPy_FromPyObject(HPyContext *ctx, PyObject *obj)
{
    Py_XINCREF(obj);
    return _py2h(obj);
}

HPyAPI_FUNC PyObject * HPy_AsPyObject(HPyContext *ctx, HPy h)
{
    PyObject *result = _h2py(h);
    Py_XINCREF(result);
    return result;
}

HPyAPI_FUNC HPy HPyModule_Create(HPyContext *ctx, HPyModuleDef *mdef)
{
    return ctx_Module_Create(ctx, mdef);
}

HPyAPI_FUNC HPy HPyType_FromSpec(HPyContext *ctx, HPyType_Spec *spec, HPyType_SpecParam *params)
{
    return ctx_Type_FromSpec(ctx, spec, params);
}

HPyAPI_FUNC HPy _HPy_New(HPyContext *ctx, HPy h, void **data)
{
    return ctx_New(ctx, h, data);
}

HPyAPI_FUNC _HPy_NO_RETURN void HPy_FatalError(HPyContext *ctx, const char *message)
{
    Py_FatalError(message);
}

HPyAPI_FUNC HPy HPyType_GenericNew(HPyContext *ctx, HPy type, const HPy *args, HPy_ssize_t nargs, HPy kw)
{
    return ctx_Type_GenericNew(ctx, type, args, nargs, kw);
}

HPyAPI_FUNC void* _HPy_AsStruct_Object(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Object(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Legacy(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Legacy(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Type(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Type(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Long(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Long(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Float(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Float(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Unicode(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Unicode(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Tuple(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Tuple(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_List(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_List(ctx, h);
}

HPyAPI_FUNC void* _HPy_AsStruct_Dict(HPyContext *ctx, HPy h)
{
    return ctx_AsStruct_Dict(ctx, h);
}

HPyAPI_FUNC HPy HPy_CallTupleDict(HPyContext *ctx, HPy callable, HPy args, HPy kw)
{
    return ctx_CallTupleDict(ctx, callable, args, kw);
}

#if PY_VERSION_HEX < 0x03090000
#    define PyObject_Vectorcall _PyObject_Vectorcall
#endif

HPyAPI_FUNC HPy HPy_Call(HPyContext *ctx, HPy callable, const HPy *args, size_t nargs, HPy kwnames)
{
    assert(sizeof(HPy) == sizeof(PyObject *));
    return _py2h(PyObject_Vectorcall(_h2py(callable), (PyObject *const *)args, nargs, _h2py(kwnames)));
}

#if PY_VERSION_HEX < 0x03090000
#    undef PyObject_Vectorcall
#endif

HPyAPI_FUNC HPy HPy_CallMethod(HPyContext *ctx, HPy name, const HPy *args, size_t nargs, HPy kwnames)
{
#if PY_VERSION_HEX >= 0x03090000
    assert(sizeof(HPy) == sizeof(PyObject *));
    return _py2h(PyObject_VectorcallMethod(_h2py(name), (PyObject *const *)args, nargs, _h2py(kwnames)));
#else
    return ctx_CallMethod(ctx, name, args, nargs, kwnames);
#endif
}

HPyAPI_FUNC void _HPy_Dump(HPyContext *ctx, HPy h)
{
    ctx_Dump(ctx, h);
}

HPyAPI_FUNC HPy HPy_Type(HPyContext *ctx, HPy h_obj)
{
    PyTypeObject *tp = Py_TYPE(_h2py(h_obj));
    Py_INCREF(tp);
    return _py2h((PyObject *)tp);
}

HPyAPI_FUNC int HPy_TypeCheck(HPyContext *ctx, HPy h_obj, HPy h_type)
{
    return ctx_TypeCheck(ctx, h_obj, h_type);
}

HPyAPI_FUNC int HPy_Is(HPyContext *ctx, HPy h_obj, HPy h_other)
{
    return _h2py(h_obj) == _h2py(h_other);
}

HPyAPI_FUNC HPyListBuilder HPyListBuilder_New(HPyContext *ctx, HPy_ssize_t initial_size)
{
    return ctx_ListBuilder_New(ctx, initial_size);
}

HPyAPI_FUNC void HPyListBuilder_Set(HPyContext *ctx, HPyListBuilder builder,
                   HPy_ssize_t index, HPy h_item)
{
    ctx_ListBuilder_Set(ctx, builder, index, h_item);
}

HPyAPI_FUNC HPy HPyListBuilder_Build(HPyContext *ctx, HPyListBuilder builder)
{
    return ctx_ListBuilder_Build(ctx, builder);
}

HPyAPI_FUNC void HPyListBuilder_Cancel(HPyContext *ctx, HPyListBuilder builder)
{
    ctx_ListBuilder_Cancel(ctx, builder);
}

HPyAPI_FUNC HPyTupleBuilder HPyTupleBuilder_New(HPyContext *ctx, HPy_ssize_t initial_size)
{
    return ctx_TupleBuilder_New(ctx, initial_size);
}

HPyAPI_FUNC void HPyTupleBuilder_Set(HPyContext *ctx, HPyTupleBuilder builder,
                    HPy_ssize_t index, HPy h_item)
{
    ctx_TupleBuilder_Set(ctx, builder, index, h_item);
}

HPyAPI_FUNC HPy HPyTupleBuilder_Build(HPyContext *ctx, HPyTupleBuilder builder)
{
    return ctx_TupleBuilder_Build(ctx, builder);
}

HPyAPI_FUNC void HPyTupleBuilder_Cancel(HPyContext *ctx, HPyTupleBuilder builder)
{
    ctx_TupleBuilder_Cancel(ctx, builder);
}

HPyAPI_FUNC HPy HPyTuple_FromArray(HPyContext *ctx, HPy items[], HPy_ssize_t n)
{
    return ctx_Tuple_FromArray(ctx, items, n);
}

HPyAPI_FUNC HPyTracker HPyTracker_New(HPyContext *ctx, HPy_ssize_t size)
{
    return ctx_Tracker_New(ctx, size);
}

HPyAPI_FUNC int HPyTracker_Add(HPyContext *ctx, HPyTracker ht, HPy h)
{
    return ctx_Tracker_Add(ctx, ht, h);
}

HPyAPI_FUNC void HPyTracker_ForgetAll(HPyContext *ctx, HPyTracker ht)
{
    ctx_Tracker_ForgetAll(ctx, ht);
}

HPyAPI_FUNC void HPyTracker_Close(HPyContext *ctx, HPyTracker ht)
{
    ctx_Tracker_Close(ctx, ht);
}

HPyAPI_FUNC HPy HPy_GetItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx) {
    return ctx_GetItem_i(ctx, obj, idx);
}

HPyAPI_FUNC HPy HPy_GetItem_s(HPyContext *ctx, HPy obj, const char *key) {
    return ctx_GetItem_s(ctx, obj, key);
}

HPyAPI_FUNC int HPy_SetItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx, HPy value) {
    return ctx_SetItem_i(ctx, obj, idx, value);
}

HPyAPI_FUNC int HPy_SetItem_s(HPyContext *ctx, HPy obj, const char *key, HPy value) {
    return ctx_SetItem_s(ctx, obj, key, value);
}

HPyAPI_FUNC int HPy_DelItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx) {
    return ctx_DelItem_i(ctx, obj, idx);
}

HPyAPI_FUNC int HPy_DelItem_s(HPyContext *ctx, HPy obj, const char *key) {
    return ctx_DelItem_s(ctx, obj, key);
}

HPyAPI_FUNC HPy HPyBytes_FromStringAndSize(HPyContext *ctx, const char *v, HPy_ssize_t len) {
    return ctx_Bytes_FromStringAndSize(ctx, v, len);
}

HPyAPI_FUNC int HPyErr_Occurred(HPyContext *ctx) {
    return ctx_Err_Occurred(ctx);
}

HPyAPI_FUNC HPy HPyCapsule_New(HPyContext *ctx, void *pointer, const char *name, HPyCapsule_Destructor *destructor)
{
    return ctx_Capsule_New(ctx, pointer, name, destructor);
}

HPyAPI_FUNC void * HPyCapsule_GetPointer(HPyContext *ctx, HPy capsule, const char *name)
{
    return PyCapsule_GetPointer(_h2py(capsule), name);
}

HPyAPI_FUNC const char * HPyCapsule_GetName(HPyContext *ctx, HPy capsule)
{
    return PyCapsule_GetName(_h2py(capsule));
}

HPyAPI_FUNC void * HPyCapsule_GetContext(HPyContext *ctx, HPy capsule)
{
    return PyCapsule_GetContext(_h2py(capsule));
}

HPyAPI_FUNC int HPyCapsule_SetPointer(HPyContext *ctx, HPy capsule, void *pointer)
{
    return PyCapsule_SetPointer(_h2py(capsule), pointer);
}

HPyAPI_FUNC int HPyCapsule_SetName(HPyContext *ctx, HPy capsule, const char *name)
{
    return PyCapsule_SetName(_h2py(capsule), name);
}

HPyAPI_FUNC int HPyCapsule_SetContext(HPyContext *ctx, HPy capsule, void *context)
{
    return PyCapsule_SetContext(_h2py(capsule), context);
}

HPyAPI_FUNC int HPyCapsule_SetDestructor(HPyContext *ctx, HPy capsule, HPyCapsule_Destructor *destructor)
{
    return ctx_Capsule_SetDestructor(ctx, capsule, destructor);
}

// just for better readability
#define SIZEOF_INT32 4
#define SIZEOF_INT64 8

HPyAPI_FUNC HPy HPyLong_FromInt32_t(HPyContext *ctx, int32_t value) {
#if SIZEOF_LONG >= SIZEOF_INT32
     return _py2h(PyLong_FromLong((long)value));
#else
     return ctx_Long_FromInt32_t ( ctx, value );
#endif
}

HPyAPI_FUNC HPy HPyLong_FromUInt32_t(HPyContext *ctx, uint32_t value) {
#if SIZEOF_LONG >= SIZEOF_INT32
     return _py2h(PyLong_FromUnsignedLong((unsigned long)value));
#else
     return ctx_Long_FromUInt32_t ( ctx, value );
#endif
}

HPyAPI_FUNC HPy HPyLong_FromInt64_t(HPyContext *ctx, int64_t v) {
#if  SIZEOF_LONG_LONG >= SIZEOF_INT64
     return _py2h(PyLong_FromLongLong((long long)v));
#else
     return ctx_Long_FromInt64_t ( ctx, v );
#endif
}

HPyAPI_FUNC HPy HPyLong_FromUInt64_t(HPyContext *ctx, uint64_t v) {
#if  SIZEOF_LONG_LONG >= SIZEOF_INT64
     return _py2h(PyLong_FromUnsignedLongLong((unsigned long long)v));
#else
     return ctx_Long_FromUInt64_t ( ctx, v );
#endif
}

HPyAPI_FUNC int32_t HPyLong_AsInt32_t(HPyContext *ctx, HPy h) {
#if SIZEOF_LONG == SIZEOF_INT32
     return (int32_t) PyLong_AsLong(_h2py(h));
#else
     return ctx_Long_AsInt32_t ( ctx, h );
#endif
}

HPyAPI_FUNC uint32_t HPyLong_AsUInt32_t(HPyContext *ctx, HPy h) {
#if SIZEOF_LONG == SIZEOF_INT32
     return (uint32_t) PyLong_AsUnsignedLong(_h2py(h));
#else
     return ctx_Long_AsUInt32_t ( ctx, h );
#endif
}

HPyAPI_FUNC uint32_t HPyLong_AsUInt32_tMask(HPyContext *ctx, HPy h) {
     return (uint32_t) PyLong_AsUnsignedLongMask(_h2py(h));
}

HPyAPI_FUNC int64_t HPyLong_AsInt64_t(HPyContext *ctx, HPy h) {
#if SIZEOF_LONG_LONG == SIZEOF_INT64
     return (int64_t) PyLong_AsLongLong(_h2py(h));
#else
     return ctx_Long_AsInt64_t ( ctx, h );
#endif
}

HPyAPI_FUNC uint64_t HPyLong_AsUInt64_t(HPyContext *ctx, HPy h) {
#if SIZEOF_LONG_LONG == SIZEOF_INT64
     return (uint64_t) PyLong_AsUnsignedLongLong(_h2py(h));
#else
     return ctx_Long_AsUInt64_t ( ctx, h );
#endif
}

HPyAPI_FUNC uint64_t HPyLong_AsUInt64_tMask(HPyContext *ctx, HPy h) {
     return (uint64_t) PyLong_AsUnsignedLongLongMask(_h2py(h));
}

#undef SIZEOF_INT32
#undef SIZEOF_INT64

HPyAPI_FUNC HPy HPy_Compile_s(HPyContext *ctx, const char *utf8_source, const char *utf8_filename, HPy_SourceKind kind) {
    return ctx_Compile_s(ctx, utf8_source, utf8_filename, kind);
}

HPyAPI_FUNC int32_t
HPyContextVar_Get(HPyContext *ctx, HPy context_var, HPy default_value, HPy *result) {
    return ctx_ContextVar_Get(ctx, context_var, default_value, result);
}

HPyAPI_FUNC const char *
HPyType_GetName(HPyContext *ctx, HPy type)
{
    return ctx_Type_GetName(ctx, type);
}

HPyAPI_FUNC int HPyType_IsSubtype(HPyContext *ctx, HPy sub, HPy type)
{
    return PyType_IsSubtype((PyTypeObject *)_h2py(sub),
            (PyTypeObject *)_h2py(type));
}

HPyAPI_FUNC int HPy_SetCallFunction(HPyContext *ctx, HPy h, HPyCallFunction *func)
{
    return ctx_SetCallFunction(ctx, h, func);
}

#endif /* !HPY_CPYTHON_MISC_H */
