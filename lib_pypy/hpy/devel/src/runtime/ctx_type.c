#include <stddef.h>
#include <Python.h>
#include "structmember.h" // for PyMemberDef
#include "hpy.h"
#include "hpy/runtime/ctx_type.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

/* Python 3.8 had "provisional" vectorcall support which was a bit different in
   some details. */
#define PROVISIONAL_VECTORCALL_SUPPORT (PY_VERSION_HEX < 0x03090000)

/* HPy_TPFLAGS_INTERNAL_IS_HPY_TYPE is set automatically on HPy types created
   with HPyType_FromSpec. This is used internally within HPy to distinguish
   HPy types.

   Note on the choice of bit: CPython uses bit 0 and all bits from 4 up in
   ver. 3.11a. Using a random currently unused bit in type flags is a temporary
   solution. Going forward, HPy may ask CPython to reserve one bit for HPy or
   find another more reliable solution.
*/
#define HPy_TPFLAGS_INTERNAL_IS_HPY_TYPE (1UL << 2)

#define HPy_TYPE_MAGIC 0xba5f

// these fields are never accessed: they are present just to ensure
// the correct alignment of payload
typedef union {
    unsigned char _m_char[1];
    unsigned short _m_short;
    unsigned int _m_int;
    unsigned long _m_long;
    unsigned long long _m_longlong;
    float _m_float;
    double _m_double;
    long double _m_longdouble;
    void *_m_pointer;
} _HPy_MaxAlign_t;

// Helper macro to align a given size to a multiple of sizeof(MAX_ALIGN_T).
#define _HPy_ALIGN(SIZE) \
        (((SIZE) + sizeof(_HPy_MaxAlign_t) - 1) & ~(sizeof(_HPy_MaxAlign_t) - 1))

/* The C structs of pure HPy (i.e. non-legacy) custom types do NOT include
 * PyObject_HEAD. So, the CPython implementation of HPy_New must allocate a
 * memory region which is big enough to contain PyObject_HEAD + any eventual
 * extra padding + the actual user struct. We use union alignment to ensure
 * that the payload is correctly aligned for every possible struct.
 *
 * Legacy custom types already include PyObject_HEAD and so do not need to
 * allocate extra memory region or use _HPy_PyObject_HEAD_SIZE.
 */
typedef struct {
    PyObject_HEAD
    _HPy_MaxAlign_t payload;
} _HPy_FullyAlignedSpaceForPyObject_HEAD;

/* Similar to the case above, if a pure HPy custom type inherits from a
 * built-in type, the pure HPy type does not embed the built-in type's struct.
 * The CPython implementation of HPy_New must allocate memory that is big
 * enough to contain the built-in type's struct + any eventual extra padding +
 * the actual user struct.
 */
#define FULLY_ALIGNED_SPACE(TYPE) \
    typedef struct { \
        TYPE ob_base; \
        _HPy_MaxAlign_t payload; \
    } _HPy_FullyAlignedSpaceFor##TYPE;

FULLY_ALIGNED_SPACE(PyHeapTypeObject)
FULLY_ALIGNED_SPACE(PyLongObject)
FULLY_ALIGNED_SPACE(PyFloatObject)
FULLY_ALIGNED_SPACE(PyUnicodeObject)
FULLY_ALIGNED_SPACE(PyTupleObject)
FULLY_ALIGNED_SPACE(PyListObject)
FULLY_ALIGNED_SPACE(PyDictObject)

#define _HPy_HEAD_SIZE(HEAD) (offsetof(_HPy_FullyAlignedSpaceFor##HEAD, payload))


static inline HPy_ssize_t
_HPy_GetHeaderSize(HPyType_BuiltinShape shape)
{
    switch (shape)
    {
    case HPyType_BuiltinShape_Legacy:
        return 0;
    case HPyType_BuiltinShape_Object:
        return _HPy_HEAD_SIZE(PyObject_HEAD);
    case HPyType_BuiltinShape_Type:
        return _HPy_HEAD_SIZE(PyHeapTypeObject);
    case HPyType_BuiltinShape_Long:
        return _HPy_HEAD_SIZE(PyLongObject);
    case HPyType_BuiltinShape_Float:
        return _HPy_HEAD_SIZE(PyFloatObject);
    case HPyType_BuiltinShape_Unicode:
        return _HPy_HEAD_SIZE(PyUnicodeObject);
    case HPyType_BuiltinShape_Tuple:
        return _HPy_HEAD_SIZE(PyTupleObject);
    case HPyType_BuiltinShape_List:
        return _HPy_HEAD_SIZE(PyListObject);
    case HPyType_BuiltinShape_Dict:
        return _HPy_HEAD_SIZE(PyDictObject);
    }
    return -1;
}

#define _HPy_OFFSET(OBJ, OFFSET) ((void*) ((char*) (OBJ) + (OFFSET)))

// Return a pointer to the area of memory AFTER the header
static inline void* _HPy_Payload(PyObject *obj, const HPyType_BuiltinShape shape)
{
    const HPy_ssize_t header_size = _HPy_GetHeaderSize(shape);
    /* Here we may assume that the shape is valid because it is provided from a
       trusted source. The shape is validated when creating the type from the
       specification. */
    assert(header_size >= 0);
    return _HPy_OFFSET(obj, header_size);
}

static bool has_tp_traverse(HPyType_Spec *hpyspec);
static bool needs_hpytype_dealloc(HPyType_Spec *hpyspec);

/* This is a hack: we need some extra space to store random data on the
   type objects created by HPyType_FromSpec().  We allocate a structure
   of type HPyType_Extra_t, which we never free for now.  We can access
   it because tp->tp_name points to the "name" field at the end... */
typedef struct {
    uint16_t magic;
    HPyFunc_traverseproc tp_traverse_impl;
    HPyFunc_destroyfunc tp_destroy_impl;
    cpy_vectorcallfunc tp_vectorcall_default_trampoline;
    HPyType_BuiltinShape shape;
    char name[];
} HPyType_Extra_t;

static inline bool _is_HPyType(PyTypeObject *tp) {
    return tp->tp_flags & HPy_TPFLAGS_INTERNAL_IS_HPY_TYPE;
}

static inline HPyType_Extra_t *_HPyType_EXTRA(PyTypeObject *tp) {
    assert(_is_HPyType(tp));
    HPyType_Extra_t *result = (HPyType_Extra_t *)(tp->tp_name - offsetof(HPyType_Extra_t, name));
    assert(result->magic == HPy_TYPE_MAGIC);
    return result;
}

static inline bool _is_pure_HPyType(PyTypeObject *tp) {
    return _is_HPyType(tp) && _HPyType_EXTRA(tp)->shape != HPyType_BuiltinShape_Legacy;
}

static inline HPyType_BuiltinShape _HPyType_Get_Shape(PyTypeObject *tp) {
    return _is_HPyType(tp) ? _HPyType_EXTRA(tp)->shape : HPyType_BuiltinShape_Legacy;
}

static inline cpy_vectorcallfunc _HPyType_get_vectorcall_default(PyTypeObject *tp) {
    return _is_HPyType(tp) ?
            _HPyType_EXTRA(tp)->tp_vectorcall_default_trampoline : NULL;
}

static inline void _HPy_set_vectorcall_func(PyTypeObject *tp, PyObject *o, cpy_vectorcallfunc f) {
    const Py_ssize_t offset = tp->tp_vectorcall_offset;
    assert(offset > 0);
    memcpy((char *) o + offset, &f, sizeof(f));
}

/*
 * If type 'tp' supports the vectorcall protocol, then retrieve the default
 * vectorcall function from the 'HPyType_Extra_t' struct and write it to the
 * appropriate offset of 'o'.
 */
static inline void _HPy_vectorcall_init(PyTypeObject *tp, PyObject *o) {
    if (PyType_HasFeature(tp, _Py_TPFLAGS_HAVE_VECTORCALL)) {
        cpy_vectorcallfunc vectorcall_default = _HPyType_get_vectorcall_default(tp);
        _HPy_set_vectorcall_func(tp, o, vectorcall_default);
    }
}

static HPyType_Extra_t *_HPyType_Extra_Alloc(const char *name, HPyType_BuiltinShape shape)
{
    size_t name_size = strlen(name) + 1;
    size_t size = offsetof(HPyType_Extra_t, name) + name_size;
    HPyType_Extra_t *result = (HPyType_Extra_t*)PyMem_Calloc(1, size);
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    memcpy(result->name, name, name_size);
    result->shape = shape;
    result->magic = HPy_TYPE_MAGIC;
    /* XXX On Python 3.10 and older, the returned struct is never freed */
    return result;
}

static inline void *_pyobj_as_struct(PyObject *obj)
{
    return _HPy_Payload(obj, _HPyType_Get_Shape(Py_TYPE(obj)));
}

static int _decref_visitor(HPyField *pf, void *arg)
{
    PyObject *old_object = _hf2py(*pf);
    *pf = HPyField_NULL;
    Py_XDECREF(old_object);
    return 0;
}

static void hpytype_clear(PyObject *self)
{
    // call tp_traverse on all the HPy types of the hierarchy
    PyTypeObject *tp = Py_TYPE(self);
    PyTypeObject *base = tp;
    while(base) {
        if (_is_HPyType(base)) {
            HPyType_Extra_t *extra = _HPyType_EXTRA(base);
            assert(extra != NULL);
            if (extra->tp_traverse_impl != NULL) {
                extra->tp_traverse_impl(_pyobj_as_struct(self), _decref_visitor, NULL);
            }
        }
        base = base->tp_base;
    }
}

/* this is a generic tp_dealloc which we use for all the user-defined HPy
   types created by HPyType_FromSpec */
static void hpytype_dealloc(PyObject *self)
{
    PyTypeObject *tp = Py_TYPE(self);
    // Call finalizer if it exists
    if (tp->tp_finalize) {
        // Exit early if resurrected
        if (PyObject_CallFinalizerFromDealloc(self) < 0) {
            return;
        }
    }
    if (PyType_IS_GC(tp))
        PyObject_GC_UnTrack(self);

    // decref and clear all the HPyFields
    hpytype_clear(self);

    // call tp_destroy on all the HPy types of the hierarchy
    PyTypeObject *base = tp;
    while(base) {
        if (_is_HPyType(base)) {
            HPyType_Extra_t *extra = _HPyType_EXTRA(base);
            assert(extra != NULL);
            if (extra->tp_destroy_impl != NULL) {
                extra->tp_destroy_impl(_pyobj_as_struct(self));
            }
        }
        base = base->tp_base;
    }

    // deallocate
    tp->tp_free(self);

    // decref the type
    assert(tp->tp_flags & Py_TPFLAGS_HEAPTYPE);
    Py_DECREF(tp);
}

/*
 * A thin decorator around the type base's 'tp_new' function, that will
 * initialize the vectorcall member (if appropriate).
 */
static PyObject *
hpyobject_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyTypeObject *base = type->tp_base;
    PyObject *result = base->tp_new(type, args, kwds);
    if (result != NULL)
        _HPy_vectorcall_init(type, result);
    return result;
}

static int
sig2flags(HPyFunc_Signature sig)
{
    switch(sig) {
        case HPyFunc_VARARGS:  return METH_FASTCALL;
        case HPyFunc_KEYWORDS: return METH_FASTCALL | METH_KEYWORDS;
        case HPyFunc_NOARGS:   return METH_NOARGS;
        case HPyFunc_O:        return METH_O;
        default:               return -1;
    }
}

static inline bool
is_bf_slot(HPyDef *def)
{
    return def->kind == HPyDef_Kind_Slot && (
        def->slot.slot == HPy_bf_getbuffer || def->slot.slot == HPy_bf_releasebuffer);
}

static inline bool
is_slot(HPyDef *def, HPySlot_Slot id)
{
    return def->kind == HPyDef_Kind_Slot && def->slot.slot == id;
}

static inline bool
is_vectorcalloffset_member(const char *name)
{
    return name[0] == '_' && name[1] == '_' &&
            strcmp(name, "__vectorcalloffset__") == 0;
}

static HPy_ssize_t
HPyDef_count(HPyDef *defs[], HPyDef_Kind kind)
{
    HPy_ssize_t res = 0;
    if (defs == NULL)
        return res;
    for(int i=0; defs[i] != NULL; i++)
        if (defs[i]->kind == kind
                && !is_bf_slot(defs[i])
                && !is_slot(defs[i], HPy_tp_destroy)
                && !is_slot(defs[i], HPy_tp_call))
            res++;
    return res;
}

static void
legacy_slots_count(PyType_Slot slots[], HPy_ssize_t *slot_count,
                   PyMethodDef **method_defs, PyMemberDef **member_defs,
                   PyGetSetDef **getset_defs)
{
    *slot_count = 0;
    *method_defs = NULL;
    *member_defs = NULL;
    *getset_defs = NULL;
    if (slots == NULL)
        return;
    for(int i=0; slots[i].slot != 0; i++)
        switch(slots[i].slot) {
        case Py_tp_methods:
            *method_defs = (PyMethodDef *)slots[i].pfunc;
            break;
        case Py_tp_members:
            *member_defs = (PyMemberDef *)slots[i].pfunc;
            break;
        case Py_tp_getset:
            *getset_defs = (PyGetSetDef *)slots[i].pfunc;
            break;
        default:
            (*slot_count)++;
            break;
        }
}

static int
hpy_slot_to_cpy_slot(HPySlot_Slot src)
{
    switch (src) {
        case HPy_tp_destroy: return Py_tp_dealloc;
        default: return src;   /* same numeric value by default */
    }
}


/*
 * Create a PyMethodDef which contains:
 *     1. All HPyMeth contained in hpyspec->defines
 *     2. All the PyMethodDef contained inside legacy_methods
 *
 * Notes:
 *     - This function is also called from ctx_module.c.
 *     - This malloc()s a result which will never be freed. Too bad
 */
_HPy_HIDDEN PyMethodDef *
create_method_defs(HPyDef *hpydefs[], PyMethodDef *legacy_methods)
{
    HPy_ssize_t hpymeth_count = HPyDef_count(hpydefs, HPyDef_Kind_Meth);
    // count the legacy methods
    HPy_ssize_t legacy_count = 0;
    if (legacy_methods != NULL) {
        while (legacy_methods[legacy_count].ml_name != NULL)
            legacy_count++;
    }
    HPy_ssize_t total_count = hpymeth_count + legacy_count;

    // allocate&fill the result
    PyMethodDef *result = (PyMethodDef*)PyMem_Calloc(total_count+1, sizeof(PyMethodDef));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    // copy the HPy methods
    int dst_idx = 0;
    if (hpydefs != NULL) {
        for(int i=0; hpydefs[i] != NULL; i++) {
            HPyDef *src = hpydefs[i];
            if (src->kind != HPyDef_Kind_Meth)
                continue;
            PyMethodDef *dst = &result[dst_idx++];
            dst->ml_name = src->meth.name;
            dst->ml_meth = (PyCFunction)src->meth.cpy_trampoline;
            dst->ml_flags = sig2flags(src->meth.signature);
            if (dst->ml_flags == -1) {
                PyMem_Free(result);
                PyErr_SetString(PyExc_ValueError,
                                "Unsupported HPyMeth signature");
                return NULL;
            }
            dst->ml_doc = src->meth.doc;
        }
    }
    // copy the legacy methods
    for(int i=0; i<legacy_count; i++)
        result[dst_idx++] = legacy_methods[i];
    result[dst_idx++] = (PyMethodDef){NULL, NULL, 0, NULL};
    if (dst_idx != total_count + 1)
        Py_FatalError("bogus count in create_method_defs");
    return result;
}

// see the comment in create_member_defs below
#ifndef HPY_ABI_CPYTHON
static PyObject *member_object_get(PyObject *self, void *closure)
{
    HPyMember *member = (HPyMember *)closure;
    HPy_ssize_t offset = member->offset;
    HPyField *field = (HPyField *)(((char *)self) + offset);
    if (HPyField_IsNull(*field)) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    PyObject *value = _hf2py(*field);
    Py_INCREF(value);
    return value;
}

static PyObject *member_object_ex_get(PyObject *self, void *closure)
{
    HPyMember *member = (HPyMember *)closure;
    HPy_ssize_t offset = member->offset;
    HPyField *field = (HPyField *)(((char *)self) + offset);
    if (HPyField_IsNull(*field)) {
        PyErr_Format(PyExc_AttributeError,
                     "'%.50s' object has no attribute '%s'",
                     Py_TYPE(self)->tp_name, member->name);
        return NULL;
    }
    PyObject *value = _hf2py(*field);
    Py_INCREF(value);
    return value;
}

static int member_object_set(PyObject *self, PyObject *value, void *closure)
{
    HPyMember *member = (HPyMember *)closure;
    HPy_ssize_t offset = member->offset;
    HPyField *field = (HPyField *)(((char *)self) + offset);
    PyObject *old_value = _hf2py(*field);
    Py_XINCREF(value);
    *field = _py2hf(value);
    Py_XDECREF(old_value);
    return 0;
}
#endif

static PyMemberDef *
create_member_defs(HPyDef *hpydefs[], PyMemberDef *legacy_members,
                   HPy_ssize_t base_member_offset, PyGetSetDef **getsets,
                   size_t *vectorcalloffset, HPy_ssize_t basicsize)
{
    /* Will be set to true if '__vectorcalloffset__' was explicitly specified as
       HPy or legacy member. */
    bool explicit_vectorcalloffset = false;
    /* Will be true if HPy_tp_call was specified and we therefore have an
       implicit vectorcall offset. */
    bool implicit_vectorcalloffset = *vectorcalloffset > 0;
    HPy_ssize_t hpymember_count = HPyDef_count(hpydefs, HPyDef_Kind_Member);

    // count the legacy members
    HPy_ssize_t legacy_count = 0;
    if (legacy_members != NULL) {
        while (legacy_members[legacy_count].name != NULL)
            legacy_count++;
    }
    HPy_ssize_t total_count = hpymember_count + legacy_count;

    // account for member '__vectorcalloffset__'
    if (implicit_vectorcalloffset)
        total_count++;

    // Sanity check: the type cannot have members if 'basicsize == 0'
    if (basicsize == 0 && total_count > 0) {
        PyErr_SetString(PyExc_TypeError,
                "Type claims to have basicsize==0 but defines members");
        return NULL;
    }

    // allocate&fill the result
    PyMemberDef *result = (PyMemberDef*)PyMem_Calloc(total_count+1, sizeof(PyMemberDef));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    int dst_idx = 0;

    // add vectorcalloffset if 'HPy_tp_call' was specified
    if (implicit_vectorcalloffset) {
        PyMemberDef *dst = &result[dst_idx++];
        dst->name = "__vectorcalloffset__";
        dst->type = T_PYSSIZET;
        dst->offset = *vectorcalloffset;
        dst->flags = READONLY;
    }

    // copy the HPy members
    if (hpydefs != NULL) {
        for(int i=0; hpydefs[i] != NULL; i++) {
            HPyDef *src = hpydefs[i];
            if (src->kind != HPyDef_Kind_Member)
                continue;
#ifndef HPY_ABI_CPYTHON
            // for the universal mode, we need to do load the HPyField that is
            // stored in the object properly. In CPython ABI mode, these can be
            // safely read as PyObject* directly without the overhead of getset.
            if (src->member.type == HPyMember_OBJECT || src->member.type == HPyMember_OBJECT_EX) {
                int getsetcnt = 0;
                while ((*getsets)[getsetcnt].name) {
                    getsetcnt++;
                }
                *getsets = (PyGetSetDef*)PyMem_Realloc(*getsets, (getsetcnt + 2) * sizeof(PyGetSetDef));
                if (!*getsets) {
                    return NULL;
                }
                PyGetSetDef *dst = &(*getsets)[getsetcnt++];
                dst->name = src->member.name;
                if (src->member.type == HPyMember_OBJECT_EX) {
                    dst->get = member_object_ex_get;
                } else {
                    dst->get = member_object_get;
                }
                if (!src->member.readonly) {
                    dst->set = member_object_set;
                } else {
                    dst->set = NULL;
                }
                dst->doc = src->member.doc;
                src->member.offset = src->member.offset + base_member_offset;
                dst->closure = (void *)&src->member;
                (*getsets)[getsetcnt] = (PyGetSetDef){NULL};
                total_count--;
                continue;
            }
#endif
            PyMemberDef *dst = &result[dst_idx++];
            dst->name = src->member.name;
            dst->type = src->member.type;
            dst->offset = src->member.offset + base_member_offset;
            dst->doc = src->member.doc;
            if (src->member.readonly)
                dst->flags = READONLY;
            else
                dst->flags = 0; // read-write
            // test if this HPy member was '__vectorcalloffset__'
            if (is_vectorcalloffset_member(src->member.name)) {
                explicit_vectorcalloffset = true;
                *vectorcalloffset = dst->offset;
            }
        }
    }
    // copy the legacy members
    for(int i=0; i<legacy_count; i++) {
        result[dst_idx++] = legacy_members[i];
        // test if this legacy member was '__vectorcalloffset__'
        if (is_vectorcalloffset_member(legacy_members[i].name)) {
            explicit_vectorcalloffset = true;
            assert(legacy_members[i].offset > 0);
            *vectorcalloffset = legacy_members[i].offset;
        }
    }

    /* Enforce constraint that we cannot have slot 'HPy_tp_call' and an explicit
       member '__vectorcalloffset__'. */
    if (implicit_vectorcalloffset && explicit_vectorcalloffset) {
        PyErr_SetString(PyExc_TypeError,
                "Cannot have HPy_tp_call and explicit member"
                "'__vectorcalloffset__'. Specify just one of them.");
        return NULL;
    }

    result[dst_idx++] = (PyMemberDef){NULL};
    if (dst_idx != total_count + 1)
        Py_FatalError("bogus count in create_member_defs");
    return result;
}

static PyGetSetDef *
create_getset_defs(HPyDef *hpydefs[], PyGetSetDef *legacy_getsets)
{
    HPy_ssize_t hpygetset_count = HPyDef_count(hpydefs, HPyDef_Kind_GetSet);
    // count the legacy members
    HPy_ssize_t legacy_count = 0;
    if (legacy_getsets != NULL) {
        while (legacy_getsets[legacy_count].name != NULL)
            legacy_count++;
    }
    HPy_ssize_t total_count = hpygetset_count + legacy_count;

    // allocate&fill the result
    PyGetSetDef *result = (PyGetSetDef*)PyMem_Calloc(total_count+1, sizeof(PyGetSetDef));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    // copy the HPy members
    int dst_idx = 0;
    if (hpydefs != NULL) {
        for(int i=0; hpydefs[i] != NULL; i++) {
            HPyDef *src = hpydefs[i];
            if (src->kind != HPyDef_Kind_GetSet)
                continue;
            PyGetSetDef *dst = &result[dst_idx++];
            dst->name = src->getset.name;
            dst->get = src->getset.getter_cpy_trampoline;
            dst->set = src->getset.setter_cpy_trampoline;
            dst->doc = src->getset.doc;
            dst->closure = src->getset.closure;
        }
    }
    // copy the legacy members
    for(int i=0; i<legacy_count; i++)
        result[dst_idx++] = legacy_getsets[i];
    result[dst_idx++] = (PyGetSetDef){NULL};
    if (dst_idx != total_count + 1)
        Py_FatalError("bogus count in create_getset_defs");
    return result;
}

static PyType_Slot *
create_slot_defs(HPyType_Spec *hpyspec, HPyType_Extra_t *extra,
                 HPy_ssize_t head_size, HPy_ssize_t *basicsize,
                 unsigned long *flags)
{
    HPy_ssize_t base_member_offset;
    HPy_ssize_t hpyslot_count = HPyDef_count(hpyspec->defines, HPyDef_Kind_Slot);
    // add the legacy slots
    HPy_ssize_t legacy_slot_count = 0;
    PyMethodDef *legacy_method_defs = NULL;
    PyMemberDef *legacy_member_defs = NULL;
    PyGetSetDef *legacy_getset_defs = NULL;
    legacy_slots_count((PyType_Slot*)hpyspec->legacy_slots, &legacy_slot_count,
                       &legacy_method_defs, &legacy_member_defs,
                       &legacy_getset_defs);
    bool needs_dealloc = needs_hpytype_dealloc(hpyspec);
    size_t vectorcalloffset = 0;
    bool has_tp_new = false;
#define ADDITIONAL_SLOTS 3
    /* This accounts for the sentinel and maybe additional slots that HPy
       installs automatically for some reason. For example, in case of the
       vectorcall protocol is used, we will additionally install 'tp_call' if
       the user did not provide it. */
    HPy_ssize_t additional_slots = 1;

    if (hpyspec->doc != NULL)
        hpyslot_count++;    // Py_tp_doc
    hpyslot_count++;        // Py_tp_methods
    hpyslot_count++;        // Py_tp_members
    hpyslot_count++;        // Py_tp_getset
    if (needs_dealloc)
        hpyslot_count++;        // Py_tp_dealloc
    if (has_tp_traverse(hpyspec))
        hpyslot_count++;    // Py_tp_clear

    // allocate the result PyType_Slot array
    HPy_ssize_t total_slot_count = hpyslot_count + legacy_slot_count;
    PyType_Slot *result = (PyType_Slot*)PyMem_Calloc(
            total_slot_count+ADDITIONAL_SLOTS, sizeof(PyType_Slot));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    // fill the result with non-meth, non-member, non-getset slots
    int dst_idx = 0;
    if (hpyspec->defines != NULL) {
        for (int i = 0; hpyspec->defines[i] != NULL; i++) {
            HPyDef *src = hpyspec->defines[i];
            if (src->kind != HPyDef_Kind_Slot || is_bf_slot(src))
                continue;
            if (is_slot(src, HPy_tp_destroy)) {
                extra->tp_destroy_impl = (HPyFunc_destroyfunc)src->slot.impl;
                continue;   /* we don't have a trampoline for tp_destroy */
            }
            if (is_slot(src, HPy_tp_call)) {
                /* Slot 'HPy_tp_call' will add a hidden field to
                   the type's struct. The field can only be appended which
                   conflicts with var objects. So, we don't allow this if
                   itemsize != 0. */
                if (hpyspec->itemsize) {
                    PyMem_Free(result);
                    PyErr_SetString(PyExc_TypeError,
                            "Cannot use HPy call protocol with var objects");
                    return NULL;
                }
                // we only need to remember the CPython trampoline
                extra->tp_vectorcall_default_trampoline =
                        (cpy_vectorcallfunc)src->slot.cpy_trampoline;
                /* Adding the hidden field means we increase the CPython type
                   spec's basic by 'sizeof(vectorcallfunc)'. In case that HPy
                   type spec's basic size was 0, we now need to adjust the
                   base_member_offset since that will no longer be inherited
                   automatically. */
                vectorcalloffset = _HPy_ALIGN(*basicsize == 0 ? head_size : *basicsize);
                if (vectorcalloffset > 0) {
                    *basicsize = vectorcalloffset + sizeof(cpy_vectorcallfunc);
                } else {
                    /* We cannot safely add the hidden field in case of a legacy
                       type that inherits the basicsize since we don't know it.
                       In this case, we reject to use HPy_tp_call but since it
                       is a legacy type, legacy slot Py_tp_call can be used. */
                    assert(hpyspec->builtin_shape == HPyType_BuiltinShape_Legacy);
                    assert(hpyspec->basicsize == 0);
                    PyMem_Free(result);
                    PyErr_SetString(PyExc_TypeError,
                            "Cannot use HPy call protocol with legacy types that"
                            " inherit the struct. Either set the basicsize to a"
                            "non-zero value or use legacy slot 'Py_tp_call'.");
                    return NULL;
                }
                /* Although there is a corresponding C API slot, we actually
                   implement HPy_tp_call using CPython's vectorcall protocol. */
                continue;
            }
            if (is_slot(src, HPy_tp_new)) {
                has_tp_new = true;
            } else if (is_slot(src, HPy_tp_traverse)) {
                extra->tp_traverse_impl = (HPyFunc_traverseproc)src->slot.impl;
                /* no 'continue' here: we have a trampoline too */
            }
            PyType_Slot *dst = &result[dst_idx++];
            dst->slot = hpy_slot_to_cpy_slot(src->slot.slot);
            dst->pfunc = (void*)src->slot.cpy_trampoline;
        }
    }

    /* Since the basicsize may be modified depending on special HPy slots, we
       defer determination of the base_member_offset to this point. */
    base_member_offset = (*basicsize != 0) ? head_size : 0;

    // add a slot for the doc string if present
    if (hpyspec->doc != NULL) {
        result[dst_idx++] = (PyType_Slot){Py_tp_doc, (void *) hpyspec->doc};
    }

    // add the legacy slots (non-methods, non-members, non-getsets)
    if (hpyspec->legacy_slots != NULL) {
        PyType_Slot *legacy_slots = (PyType_Slot *)hpyspec->legacy_slots;
        for (int i = 0; legacy_slots[i].slot != 0; i++) {
            PyType_Slot *src = &legacy_slots[i];
            if (src->slot == Py_tp_methods || src->slot == Py_tp_members ||
                src->slot == Py_tp_getset)
                continue;
            PyType_Slot *dst = &result[dst_idx++];
            *dst = *src;
        }
    }

    // add the "real" methods
    PyMethodDef *pymethods = create_method_defs(hpyspec->defines, legacy_method_defs);
    if (pymethods == NULL) {
        PyMem_Free(result);
        return NULL;
    }
    result[dst_idx++] = (PyType_Slot){Py_tp_methods, pymethods};

    // prepare the "real" getsets
    PyGetSetDef *pygetsets = create_getset_defs(hpyspec->defines, legacy_getset_defs);
    if (pygetsets == NULL) {
        PyMem_Free(pymethods);
        PyMem_Free(result);
        return NULL;
    }

    // prepare the "real" members, which may introduce getsetdefs in universal mode
    PyMemberDef *pymembers = create_member_defs(hpyspec->defines, legacy_member_defs, base_member_offset, &pygetsets, &vectorcalloffset, *basicsize);
    if (pymembers == NULL) {
        PyMem_Free(pygetsets);
        PyMem_Free(pymethods);
        PyMem_Free(result);
        return NULL;
    }

    // if we have seen HPy_tp_call or an explicit member '__vectorcalloffset__'
    if (vectorcalloffset > 0) {
        /* Since there is no way to set Py_tp_call directly from HPy, we also
           always need to specify it if HPy_tp_call is there or a
           '__vectorcalloffset__' was specified. */
        additional_slots++;
        PyType_Slot *dst = &result[dst_idx++];
        dst->slot = Py_tp_call;
        dst->pfunc = (void*)PyVectorcall_Call;

        /* If the user did not provide the new function, we need to install a
           special new function that will delegate to the inherited tp_new but
           additionally sets the default call function. This is not necessary if
           the user provides the new function because he will use 'HPy_New' to
           allocate the object which already takes care of that. */
        if (!has_tp_new) {
            additional_slots++;
            PyType_Slot *dst = &result[dst_idx++];
            dst->slot = Py_tp_new;
            dst->pfunc = (void*)hpyobject_new;
        }

        *flags |= _Py_TPFLAGS_HAVE_VECTORCALL;
    }

    // add both members and getsets
    result[dst_idx++] = (PyType_Slot){Py_tp_members, pymembers};
    result[dst_idx++] = (PyType_Slot){Py_tp_getset, pygetsets};

    // add a dealloc function, if needed
    if (needs_dealloc) {
        result[dst_idx++] = (PyType_Slot){Py_tp_dealloc, (void*)hpytype_dealloc};
    }

    // add a tp_clear, if the user provided a tp_traverse
    if (has_tp_traverse(hpyspec)) {
        result[dst_idx++] = (PyType_Slot){Py_tp_clear, (void*)hpytype_clear};
    }

    // add the NULL sentinel at the end
    result[dst_idx++] = (PyType_Slot){0, NULL};
    if (dst_idx != total_slot_count + additional_slots)
        Py_FatalError("bogus slot count in create_slot_defs");
    return result;
}

/* Python 3.8 and older is the missing Py_bf_getbuffer and Py_bf_releasebuffer
   so we need to define those functions here. Since Python 3.9, we can just use
   the function pointer types from Python. */
#if PY_VERSION_HEX < 0x03009000
typedef int (*cpy_getbufferproc)(cpy_PyObject *, cpy_Py_buffer *, int);
typedef void (*cpy_releasebufferproc)(cpy_PyObject *, cpy_Py_buffer *);
#else
typedef getbufferproc cpy_getbufferproc;
typedef releasebufferproc cpy_releasebufferproc;
#endif
static PyBufferProcs*
create_buffer_procs(HPyType_Spec *hpyspec)
{
    PyBufferProcs *buffer_procs = NULL;
    if (hpyspec->defines != NULL) {
        for (int i = 0; hpyspec->defines[i] != NULL; i++) {
            HPyDef *src = hpyspec->defines[i];
            if (src->kind != HPyDef_Kind_Slot)
                continue;
            switch (src->slot.slot) {
                case HPy_bf_getbuffer:
                    if (buffer_procs == NULL) {
                        buffer_procs = (PyBufferProcs*)PyMem_Calloc(1, sizeof(PyBufferProcs));
                        if (buffer_procs == NULL) {
                            PyErr_NoMemory();
                            return NULL;
                        }
                    }
                    buffer_procs->bf_getbuffer = (cpy_getbufferproc)src->slot.cpy_trampoline;
                    break;
                case HPy_bf_releasebuffer:
                    if (buffer_procs == NULL) {
                        buffer_procs = (PyBufferProcs*)PyMem_Calloc(1, sizeof(PyBufferProcs));
                        if (buffer_procs == NULL) {
                            PyErr_NoMemory();
                            return NULL;
                        }
                    }
                    buffer_procs->bf_releasebuffer = (cpy_releasebufferproc)src->slot.cpy_trampoline;
                    break;
                default:
                    break;
            }
        }
    }
    return buffer_procs;
}

static int check_unknown_params(HPyType_SpecParam *params, const char *name)
{
    if (params == NULL)
        return 0;

    int found_base = 0, found_basestuple = 0;
    for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
        switch (p->kind) {
            case HPyType_SpecParam_Base:
                found_base++;
                break;
            case HPyType_SpecParam_BasesTuple:
                found_basestuple++;
                break;
            case HPyType_SpecParam_Metaclass:
                break;

            default:
                PyErr_Format(PyExc_TypeError,
                    "unknown HPyType_SpecParam specification for '%s'",
                    name);
                return -1;
        }
    }
    if (found_basestuple > 1) {
        PyErr_SetString(PyExc_TypeError,
            "multiple specifications of HPyType_SpecParam_BasesTuple");
        return -1;
    }
    if (found_base && found_basestuple) {
        PyErr_SetString(PyExc_TypeError,
            "cannot specify both HPyType_SpecParam_Base and "
            "HPytype_SpecParam_BasesTuple");
        return -1;
    }
    return 0;
}

static int check_legacy_consistent(HPyType_Spec *hpyspec)
{
    if (hpyspec->legacy_slots && hpyspec->builtin_shape != HPyType_BuiltinShape_Legacy) {
        PyErr_SetString(PyExc_TypeError,
            "cannot specify .legacy_slots without setting .builtin_shape=HPyType_BuiltinShape_Legacy");
        return -1;
    }
    if (hpyspec->legacy_slots && needs_hpytype_dealloc(hpyspec)) {
        PyType_Slot *legacy_slots = (PyType_Slot *)hpyspec->legacy_slots;
        for (int i = 0; legacy_slots[i].slot != 0; i++) {
            if (legacy_slots[i].slot == Py_tp_dealloc) {
                PyErr_SetString(PyExc_TypeError,
                    "legacy tp_dealloc is incompatible with HPy_tp_traverse"
                    " or HPy_tp_destroy.");
                return -1;
            }
        }
    }
    return 0;
}

static bool has_tp_traverse(HPyType_Spec *hpyspec)
{
    if (hpyspec->defines != NULL)
        for (int i = 0; hpyspec->defines[i] != NULL; i++) {
            HPyDef *def = hpyspec->defines[i];
            if (def->kind == HPyDef_Kind_Slot && def->slot.slot == HPy_tp_traverse)
                return true;
        }
    return false;
}

static bool needs_hpytype_dealloc(HPyType_Spec *hpyspec)
{
    if (hpyspec->defines != NULL)
        for (int i = 0; hpyspec->defines[i] != NULL; i++) {
            HPyDef *def = hpyspec->defines[i];
            if (def->kind == HPyDef_Kind_Slot &&
                    (def->slot.slot == HPy_tp_destroy || def->slot.slot == HPy_tp_traverse))
                return true;
        }
    return false;
}

static int check_have_gc_and_tp_traverse(HPyContext *ctx, HPyType_Spec *hpyspec)
{
    // if we specify HPy_TPFLAGS_HAVE_GC, we must provide a tp_traverse
    if (hpyspec->flags & HPy_TPFLAGS_HAVE_GC && !has_tp_traverse(hpyspec)) {
        HPyErr_SetString(ctx, ctx->h_ValueError,
                         "You must provide an HPy_tp_traverse slot if you specify "
                         "HPy_TPFLAGS_HAVE_GC");
        return -1;
    }
    return 0;
}

static int check_inheritance_constraints(PyTypeObject *tp)
{
    int tp_pure = _is_pure_HPyType(tp);
    int tp_base_pure = _is_pure_HPyType(tp->tp_base);
    if (tp_pure) {
        // Pure types may inherit from:
        //
        // * pure types, or
        // * PyBaseObject_Type, or
        // * other builtin or legacy types as long as long as they do not
        //   access the struct layout (e.g. by using HPy_AsStruct or defining
        //   a deallocator with HPy_tp_destroy).
        //
        // It would be nice to relax these restrictions or check them here.
        // See https://github.com/hpyproject/hpy/issues/169 for details.
    }
    else {
        if (tp_base_pure) {
            PyErr_SetString(PyExc_TypeError,
                "A legacy type should not inherit its memory layout from a"
                " pure type");
            return -1;
        }
    }
    return 0;
}

static PyObject *build_bases_from_params(HPyType_SpecParam *params)
{
    if (params == NULL)
        return NULL;

    PyObject *tup;
    int found_base = 0;
    for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
        switch (p->kind) {
            case HPyType_SpecParam_Base:
                /* count the base entries (multiple entries are fine) */
                found_base++;
                break;
            case HPyType_SpecParam_BasesTuple:
                /* if there is instead a complete base tuple, just return it */
                /* we increment the reference count of the tuple here to match
                   the reference counting on the tuple we create below when
                   there is no HPyType_SpecParam_BasesTuple */
                tup = _h2py(p->object);
                Py_INCREF(tup);
                return tup;
            case HPyType_SpecParam_Metaclass:
                // intentionally ignored
                break;
        }
    }
    if (found_base == 0)
        return NULL;

    tup = PyTuple_New(found_base);
    if (tup == NULL)
        return NULL;

    found_base = 0;
    for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
        if (p->kind == HPyType_SpecParam_Base) {
            PyObject *base = _h2py(p->object);
            Py_INCREF(base);
            PyTuple_SET_ITEM(tup, found_base, base);
            found_base++;
        }
    }
    return tup;
}

_HPy_HIDDEN struct _typeobject *get_metatype(HPyType_SpecParam *params) {
    struct _typeobject *res = NULL;
    if (params != NULL) {
        for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
            switch (p->kind) {
                case HPyType_SpecParam_Metaclass:
                    if (res) {
                        PyErr_SetString(PyExc_ValueError, "metaclass was specified multiple times");
                        return NULL;
                    }
                    res = (struct _typeobject*) _h2py(p->object);
                    if (!PyType_Check(res)) {
                        PyErr_Format(PyExc_TypeError,
                                "Metaclass '%R' is not a subclass of 'type'.",
                                res);
                        return NULL;
                    }
                    break;
                default:
                    // other values are intentionally ignored
                    break;
            }
        }
    }
    /* Returning NULL here does not indicate an error but that the metaclass
       has not explicitly been specified. We could default here to &PyType_Type
       but we actually want to use the bare 'PyType_FromSpecWithBases' if
       nothing was specified. */
    return res;
}

#define HAVE_FROM_METACLASS (PY_VERSION_HEX >= 0x030C0000)

#if !HAVE_FROM_METACLASS

static inline Py_ssize_t count_members(PyType_Spec *spec, Py_ssize_t *vectorcalloffset) {
    Py_ssize_t nmembers = 0;
#if PROVISIONAL_VECTORCALL_SUPPORT
    *vectorcalloffset = 0;
#endif /* Python 3.8.x */
    const PyType_Slot *slot;
    for (slot = spec->slots; slot->slot; slot++) {
        if (slot->slot == Py_tp_members) {
            nmembers = 0;
            for (const PyMemberDef *memb = (const PyMemberDef *)slot->pfunc; memb->name != NULL; memb++) {
                nmembers++;
#if PROVISIONAL_VECTORCALL_SUPPORT
                /* Python 3.8 already supports vectorcalls but does not
                   consider the '__vectorcalloffset__' member. So we need to do
                   it manually. */
                if (strcmp(memb->name, "__vectorcalloffset__") == 0) {
                    // The PyMemberDef must be a Py_ssize_t and readonly
                    assert(memb->type == T_PYSSIZET);
                    assert(memb->flags == READONLY);
                    *vectorcalloffset = memb->offset;
                }
#endif /* Python 3.8.x */
            }
        }
    }
    return nmembers;
}

/* On older Python versions (before 3.12), we need to workaround the missing
   support for metaclasses. We create a temporary heap type using
   'PyType_FromSpecWithBases' and if a metaclass was provided, we use it to
   allocate the appropriate type object and memcpy most of the contents from
   the heap type to the manually allocated one. Then we clear some key slots
   and call 'PyType_Ready' on it to re-initialize everything. The temporary
   heap type is then expired. */
static PyObject*
_PyType_FromMetaclass(PyType_Spec *spec, PyObject *bases,
        struct _typeobject *meta)
{
    PyObject *temp, *result;
    PyHeapTypeObject *temp_ht, *ht;
    PyTypeObject *temp_tp, *tp;
    Py_ssize_t nmembers, vectorcalloffset;
    const char *s;

#if PROVISIONAL_VECTORCALL_SUPPORT
    /* Python 3.8 does not support specifying the vectorcall offset via the
       type spec. Therefore, if the flag is set, 'PyType_Ready' will fail an
       assert later on. So, we clear the flag and set the flags manually after
       'PyType_Ready' when 'tp_vectorcall_offset' is also set. */
    unsigned int restore_vectorcall_flag = spec->flags & _Py_TPFLAGS_HAVE_VECTORCALL;
    spec->flags &= ~_Py_TPFLAGS_HAVE_VECTORCALL;
#endif /* Python 3.8.x */

    temp = PyType_FromSpecWithBases(spec, bases);
    if (!temp)
        return NULL;

    /* If no metaclass was provided, we avoid this path since it is rather
       expensive and slow. */
    if (meta) {
        result = NULL;
        /* We previously tested at this point if 'meta' is a type. That check
           was moved to function 'get_metatype'. */
        if (meta->tp_new != PyType_Type.tp_new) {
            PyErr_SetString(PyExc_TypeError,
                    "Metaclasses with custom tp_new are not supported.");
            goto fail;
        }
        temp_ht = (PyHeapTypeObject *) temp;
        temp_tp = &temp_ht->ht_type;

        Py_INCREF(temp_ht->ht_name);
        Py_INCREF(temp_ht->ht_qualname);
        Py_XINCREF(temp_ht->ht_slots);
        Py_INCREF(temp_tp->tp_base);

        /* Count the members as 'PyType_FromSpecWithBases' does such that we
           can properly allocate the size later when allocating the type. */
        nmembers = count_members(spec, &vectorcalloffset);

        result = meta->tp_alloc(meta, nmembers);
        if (!result)
            goto fail;

        ht = (PyHeapTypeObject *) result;
        tp = &ht->ht_type;

        /* IMPORTANT: CPython debug builds may store additional information in
           the object header (i.e. before 'ob_refcnt') for tracing references
           or whatever. In this case, we MUST NOT copy the object header. So we
           don't copy the whole embedded 'PyVarObject' chunk at the beginning
           of the 'PyHeapTypeObject'. The appropriate 'PyVarObject' fields are
           set explicitly right below. */
        memcpy(_HPy_OFFSET(tp, sizeof(PyVarObject)),
                _HPy_OFFSET(temp_tp, sizeof(PyVarObject)),
                sizeof(PyHeapTypeObject) - sizeof(PyVarObject));

        tp->ob_base.ob_base.ob_type = meta;
        tp->ob_base.ob_base.ob_refcnt = 1;
        tp->ob_base.ob_size = 0;
        tp->tp_as_async = &ht->as_async;
        tp->tp_as_number = &ht->as_number;
        tp->tp_as_sequence = &ht->as_sequence;
        tp->tp_as_mapping = &ht->as_mapping;
        tp->tp_as_buffer = &ht->as_buffer;
        tp->tp_flags = spec->flags | Py_TPFLAGS_HEAPTYPE;

        tp->tp_dict = NULL;
        tp->tp_bases = NULL;
        tp->tp_mro = NULL;
        tp->tp_cache = NULL;
        tp->tp_subclasses = NULL;
        tp->tp_weaklist = NULL;
        ht->ht_cached_keys = NULL;
        tp->tp_version_tag = 0;

        /* Refresh 'tp_doc'. This is necessary because
           'PyType_FromSpecWithBases' allocates its own buffer which will be
           free'd. */
        if (temp_tp->tp_doc) {
            size_t len = strlen(temp_tp->tp_doc)+1;
            char *tp_doc = (char *)PyObject_MALLOC(len);
            if (!tp_doc)
                goto fail;
            memcpy(tp_doc, temp_tp->tp_doc, len);
            tp->tp_doc = tp_doc;
        }

        /* Sanity check: GC objects need to provide 'tp_traverse' and
           'tp_clear'. */
        assert(!PyType_IS_GC(tp) || tp->tp_traverse != NULL || tp->tp_clear != NULL);

        if (PyType_Ready(tp) < 0)
            goto fail;

        /* Restore 'ht_cached_keys' after call to 'PyType_Ready' */
        if (temp_ht->ht_cached_keys) {
            Py_INCREF(temp_ht->ht_cached_keys);
            ht->ht_cached_keys = temp_ht->ht_cached_keys;
        }

        /* The following is the tail of 'PyType_FromSpecWithBases'. */

        /* Set type.__module__ */
        s = strrchr(spec->name, '.');
        if (s != NULL) {
            int err;
            PyObject *modname = PyUnicode_FromStringAndSize(
                    spec->name, (Py_ssize_t)(s - spec->name));
            if (!modname) {
                goto fail;
            }
            err = PyDict_SetItemString(tp->tp_dict, "__module__", modname);
            Py_DECREF(modname);
            if (err != 0)
                goto fail;
        }
        return result;
fail:
        Py_DECREF(temp);
        Py_XDECREF(result);
        return NULL;
#if PROVISIONAL_VECTORCALL_SUPPORT
    } else {
        tp = (PyTypeObject *) temp;
        nmembers = count_members(spec, &vectorcalloffset);
    }

    if (vectorcalloffset) {
        tp->tp_vectorcall_offset = vectorcalloffset;
    }

    if (restore_vectorcall_flag) {
        tp->tp_flags |= _Py_TPFLAGS_HAVE_VECTORCALL;
        _PyObject_ASSERT((PyObject *)tp, tp->tp_vectorcall_offset > 0);
        _PyObject_ASSERT((PyObject *)tp, tp->tp_call != NULL);
#endif /* Python 3.8.x */
    }
    return temp;
}

#endif /* HAVE_FROM_METACLASS */

HPy
ctx_Type_FromSpec(HPyContext *ctx, HPyType_Spec *hpyspec,
                  HPyType_SpecParam *params)
{
    if (check_unknown_params(params, hpyspec->name) < 0) {
        return HPy_NULL;
    }
    if (check_legacy_consistent(hpyspec) < 0) {
        return HPy_NULL;
    }
    if (check_have_gc_and_tp_traverse(ctx, hpyspec) < 0) {
        return HPy_NULL;
    }

    PyType_Spec *spec = (PyType_Spec*)PyMem_Calloc(1, sizeof(PyType_Spec));
    if (spec == NULL) {
        PyErr_NoMemory();
        return HPy_NULL;
    }
    /* Create local copies of 'basicsize' and 'flags' because they might be
       modified and we must not write into 'hpyspec' since it is not owned by
       this function and it could be read-only memory. */
    HPy_ssize_t basicsize;
    unsigned long flags = hpyspec->flags;

    HPy_ssize_t head_size = _HPy_GetHeaderSize(hpyspec->builtin_shape);
    if (head_size < 0) {
        // an invalid shape was specified
        PyErr_Format(PyExc_ValueError, "invalid shape: %d", hpyspec->builtin_shape);
        return HPy_NULL;
    }

    /* _HPy_HEAD_SIZE(base) ensures that the custom struct is correctly
       aligned. */
    if (hpyspec->basicsize != 0) {
        basicsize = hpyspec->basicsize + head_size;
    }
    else {
        /* If basicsize is 0, it is inherited from the parent type. In this
           case, calling *_AsStruct on an inherited type only makes sense if
           the parent type is already an HPy extension type. */
        basicsize = 0;
    }

    HPyType_Extra_t *extra = _HPyType_Extra_Alloc(hpyspec->name, hpyspec->builtin_shape);
    if (extra == NULL) {
        PyMem_Free(spec);
        return HPy_NULL;
    }
    spec->name = extra->name;
    spec->itemsize = hpyspec->itemsize;
    spec->slots = create_slot_defs(hpyspec, extra, head_size, &basicsize, &flags);
    if (spec->slots == NULL) {
        PyMem_Free(spec);
        return HPy_NULL;
    }
    /* If the vectorcall protocol should be used, set the corresponding
       CPython type flag. */
    assert(extra->tp_vectorcall_default_trampoline == NULL ||
            (flags & _Py_TPFLAGS_HAVE_VECTORCALL));
    spec->flags = flags | HPy_TPFLAGS_INTERNAL_IS_HPY_TYPE;
    spec->basicsize = (int)basicsize;

    PyObject *bases = build_bases_from_params(params);
    if (PyErr_Occurred()) {
        PyMem_Free(spec->slots);
        PyMem_Free(spec);
        return HPy_NULL;
    }
    struct _typeobject *metatype = get_metatype(params);
    if (metatype == NULL && PyErr_Occurred()) {
        PyMem_Free(spec->slots);
        PyMem_Free(spec);
        return HPy_NULL;
    }

#if HAVE_FROM_METACLASS
    /* On Python 3.12 an newer, we can just use 'PyType_FromMetaclass'. */
    PyObject *result = PyType_FromMetaclass(metatype, NULL, spec, bases);
#else
    /* On Python 3.11 an older, we need to use our own
       '_PyType_FromMetaclass'. */
    PyObject *result = _PyType_FromMetaclass(spec, bases, metatype);
#endif

    /* note that we do NOT free the memory which was allocated by
       create_method_defs, because that one is referenced internally by
       CPython (which probably assumes it's statically allocated) */
    Py_XDECREF(bases);
    PyMem_Free(spec->slots);
    PyMem_Free(spec);
    if (result == NULL) {
        return HPy_NULL;
    }

#if PY_VERSION_HEX >= 0x030B0000
    /* Since Python 3.11, the name will be copied into a fresh buffer such that
       the type objects owns this buffer. Hence we need to patch the pointer
       again. The nice thing is that Python will then free out HPyType_Extra
       for us. The internal field '_ht_tpname' is only used for freeing. So, we
       can set it to 'extra'. */
    PyHeapTypeObject *ht = (PyHeapTypeObject *) result;
    PyMem_Free(ht->_ht_tpname);
    ht->_ht_tpname = (char *) extra;
    ht->ht_type.tp_name = (const char *)extra->name;
#endif

    PyBufferProcs* buffer_procs = create_buffer_procs(hpyspec);
    if (buffer_procs) {
        ((PyTypeObject*)result)->tp_as_buffer = buffer_procs;
    } else {
        if (PyErr_Occurred()) {
            Py_DECREF(result);
            return HPy_NULL;
        }
    }
    if (check_inheritance_constraints((PyTypeObject *) result) < 0) {
        Py_DECREF(result);
        return HPy_NULL;
    }
    assert(_is_HPyType((PyTypeObject*) result));
    return _py2h(result);
}

_HPy_HIDDEN HPy
ctx_New(HPyContext *ctx, HPy h_type, void **data)
{
    PyTypeObject *tp = (PyTypeObject*) _h2py(h_type);
    assert(tp != NULL);
    if (!PyType_Check(tp)) {
        PyErr_SetString(PyExc_TypeError, "HPy_New arg 1 must be a type");
        return HPy_NULL;
    }

    PyObject *result;
    if (PyType_IS_GC(tp))
        result = PyObject_GC_New(PyObject, tp);
    else
        result = PyObject_New(PyObject, tp);

    // HPy_New guarantees that the memory is zeroed, but PyObject_{GC}_New
    // doesn't. But we need to make sure to NOT overwrite ob_refcnt and
    // ob_type. See test_HPy_New_initialize_to_zero
    const HPyType_BuiltinShape shape = _HPyType_Get_Shape(tp);
    HPy_ssize_t payload_size;
    void *payload;
    if (shape != HPyType_BuiltinShape_Legacy) {
        payload_size = tp->tp_basicsize - _HPy_GetHeaderSize(shape);
        /* For pure HPy custom types, we return a pointer to only the custom
           struct data, without the hidden PyObject header. */
        payload = _HPy_Payload(result, shape);
        memset(payload, 0, payload_size);
    } else {
        /* In case of a legacy type, we still MUST NOT overwrite the object
           header otherwise we would clear `ob_type` and `ob_refcnt`. */
        payload_size = tp->tp_basicsize - _HPy_HEAD_SIZE(PyObject_HEAD);
        memset(_HPy_Payload(result, HPyType_BuiltinShape_Object), 0, payload_size);
        payload = (void *) result;
    }

    _HPy_vectorcall_init(tp, result);

    // NOTE: The CPython docs explicitly ask to call GC_Track when all fields
    // are initialized, so it's important to do so AFTER zeroing the memory.
    if (PyType_IS_GC(tp))
        PyObject_GC_Track(result);

    if (!result)
        return HPy_NULL;

    *data = payload;

    return _py2h(result);
}

_HPy_HIDDEN HPy
ctx_Type_GenericNew(HPyContext *ctx, HPy h_type, const HPy *args,
                    HPy_ssize_t nargs, HPy kw)
{
    PyObject *tp = _h2py(h_type);
    assert(tp != NULL);
    if (!PyType_Check(tp)) {
        PyErr_SetString(PyExc_TypeError, "HPy_Type_GenericNew arg 1 must be a type");
        return HPy_NULL;
    }

    PyObject *res = ((PyTypeObject*) tp)->tp_alloc((PyTypeObject*) tp, 0);
    return _py2h(res);
}

_HPy_HIDDEN void*
ctx_AsStruct_Object(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Object);
}

_HPy_HIDDEN void*
ctx_AsStruct_Legacy(HPyContext *ctx, HPy h)
{
    return _h2py(h);
}

_HPy_HIDDEN void*
ctx_AsStruct_Type(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Type);
}

_HPy_HIDDEN void*
ctx_AsStruct_Long(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Long);
}

_HPy_HIDDEN void*
ctx_AsStruct_Float(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Float);
}

_HPy_HIDDEN void*
ctx_AsStruct_Unicode(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Unicode);
}

_HPy_HIDDEN void*
ctx_AsStruct_Tuple(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Tuple);
}

_HPy_HIDDEN void*
ctx_AsStruct_List(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_List);
}

_HPy_HIDDEN void*
ctx_AsStruct_Dict(HPyContext *ctx, HPy h)
{
    return _HPy_Payload(_h2py(h), HPyType_BuiltinShape_Dict);
}

_HPy_HIDDEN void*
ctx_AsStruct_Slow(HPyContext *ctx, HPy h)
{
    return _pyobj_as_struct(_h2py(h));
}


/* ~~~ call_traverseproc_from_trampoline ~~~
   This is used to implement tp_traverse.

   From the HPy user point of view, the visitor function passed to tp_traverse
   takes a ctx and an HPyField*:

       typedef int (*HPyFunc_visitproc)(HPyContext *, HPyField *, void *);
       ...
       static int my_traverse_impl(HPyContext *ctx, HPy self,
                                   HPyFunc_visitproc hpy_visit, void *arg)
       {
           MyCustomObject *obj = ...;
           hpy_visit(&obj->a, arg);  // obj->a is an HPyField
           hpy_visit(&obj->b, arg);
           ...
       }

   However, from the CPython point of view the visitor function passed to
   tp_traverse takes a PyObject*:

       typedef int (*visitproc)(cpy_PyObject *, void *);
       static int my_traverse(MyCustomObject *self, visitproc cpy_visit, void *arg)
       {
           cpy_visit(self->a, arg);  // self->a is a PyObject*
           cpy_visit(self->b, arg);
           ...
       }

   This is what happens:

   1. CPython calls the trampoline created by _HPyFunc_TRAMPOLINE_TRAVERSEPROC
      passing a visitor function. Let's call it cpy_visit, and remember that
      it takes a PyObject*.

   2. The trampoline invokes _HPy_CallRealFunctionFromTrampoline, which
      ultimately calls call_traverseproc_from_trampoline.

   3. call_traverseproc_from_trampoline invokes the tp_traverse_impl written
      by the HPy user, passing hpy2cpy_visit as the visitor function.

   4. tp_traverse_impl calls hpy2cpy_visit multiple times, once for every HPyField

   5. hpy2cpy_visit takes an HPyField*, converts it to a PyObject* and invokes
      the cpy_visit of point (1)
*/

typedef struct {
    cpy_visitproc cpy_visit;
    void *cpy_arg;
} hpy2cpy_visit_args_t;

static int hpy2cpy_visit(HPyField *f, void *v_args)
{
    hpy2cpy_visit_args_t *args = (hpy2cpy_visit_args_t *)v_args;
    cpy_visitproc cpy_visit = args->cpy_visit;
    void *cpy_arg = args->cpy_arg;
    PyObject *cpy_obj = _hf2py(*f);
    return cpy_visit(cpy_obj, cpy_arg);
}

_HPy_HIDDEN int call_traverseproc_from_trampoline(HPyFunc_traverseproc tp_traverse,
                                                  PyObject *self,
                                                  cpy_visitproc cpy_visit,
                                                  void *cpy_arg)
{
    hpy2cpy_visit_args_t args = { cpy_visit, cpy_arg };
    return tp_traverse(_pyobj_as_struct(self), hpy2cpy_visit, &args);
}

_HPy_HIDDEN HPyType_BuiltinShape ctx_Type_GetBuiltinShape(HPyContext *ctx, HPy h_type)
{
    PyTypeObject *tp = (PyTypeObject*) _h2py(h_type);
    assert(tp != NULL);
    if (!PyType_Check(tp)) {
        PyErr_SetString(PyExc_TypeError, "arg must be a type");
        return (HPyType_BuiltinShape) -2;
    }
    return _HPyType_Get_Shape((PyTypeObject *)tp);
}

_HPy_HIDDEN const char *ctx_Type_GetName(HPyContext *ctx, HPy type)
{
    PyTypeObject *tp = (PyTypeObject*) _h2py(type);
    assert(tp != NULL);
    if (tp->tp_flags & Py_TPFLAGS_HEAPTYPE) {
        PyHeapTypeObject* et = (PyHeapTypeObject*)tp;
        return PyUnicode_AsUTF8(et->ht_name);
    }
    else {
        // '_PyType_Name' is at least available from 3.8 to 3.12
        return _PyType_Name(tp);
    }
}

_HPy_HIDDEN int ctx_SetCallFunction(HPyContext *ctx, HPy h,
                                    HPyCallFunction *func)
{
    PyObject *obj = _h2py(h);
    assert(obj != NULL);

    PyTypeObject *tp = Py_TYPE(obj);
    assert(tp != NULL);
    if (!PyType_HasFeature(tp, _Py_TPFLAGS_HAVE_VECTORCALL)) {
        PyErr_Format(PyExc_TypeError,
                "type '%.50s does not implement the HPy call protocol",
                tp->tp_name);
        return -1;
    }
    _HPy_set_vectorcall_func(tp, obj, func->cpy_trampoline);
    return 0;
}
