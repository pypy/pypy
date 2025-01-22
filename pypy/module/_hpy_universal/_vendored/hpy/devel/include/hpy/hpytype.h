#ifndef HPY_UNIVERSAL_HPYTYPE_H
#define HPY_UNIVERSAL_HPYTYPE_H

#include <stdbool.h>
#ifdef __GNUC__
#define HPyAPI_UNUSED __attribute__((unused)) static inline
#else
#define HPyAPI_UNUSED static inline
#endif /* __GNUC__ */

// NOTE: HPyType_BuiltinShape_Object == 0, which means it's the default
// if it's not specified in HPyType_spec
typedef enum {
    /**
     * A type whose struct starts with ``PyObject_HEAD`` or equivalent is a
     * legacy type. A legacy type must set
     * ``.builtin_shape = HPyType_BuiltinShape_Legacy`` in its
     * :c:struct:`HPyType_Spec`.
     *
     * A type is a non-legacy type, also called HPy pure type, if its struct does
     * not include ``PyObject_HEAD``. Using pure types should be preferred.
     * Legacy types are available to allow gradual porting of existing CPython
     * extensions.
     *
     * A type with ``.legacy_slots != NULL``
     * (see :c:member:`HPyType_Spec.legacy_slots`) is required to have
     * ``HPyType_BuiltinShape_Legacy`` and to include ``PyObject_HEAD`` at the
     * start of its struct. It would be easy to relax this requirement on
     * CPython (where the ``PyObject_HEAD`` fields are always present) but a
     * large burden on other implementations (e.g. PyPy, GraalPy) where a
     * struct starting with ``PyObject_HEAD`` might not exist.
     *
     * Types created via the old Python C API are automatically legacy types.
     */
    HPyType_BuiltinShape_Legacy = -1,

    /** The type inherits from built-in type ``object`` (default). */
    HPyType_BuiltinShape_Object = 0,

    /**
     * The type inherits from built-in type ``type``. This can be used to
     * create metaclasses. If using this shape, you need to specify base class
     * ``ctx->h_TypeType``.
     */
    HPyType_BuiltinShape_Type = 1,

    /**
     * The type inherits from built-in type ``int`` (aka. long object). If using
     * this shape, you need to specify base class ``ctx->h_LongType``.
     */
    HPyType_BuiltinShape_Long = 2,

    /**
     * The type inherits from built-in type ``float``. If using this shape, you
     * need to specify base class ``ctx->h_FloatType``.
     */
    HPyType_BuiltinShape_Float = 3,

    /**
     * The type inherits from built-in type ``str`` (aka. unicode object). If
     * using this shape, you need to specify base class ``ctx->h_UnicodeType``.
     */
    HPyType_BuiltinShape_Unicode = 4,

    /**
     * The type inherits from built-in type ``tuple``. If using this shape, you
     * need to specify base class ``ctx->h_TupleType``.
     */
    HPyType_BuiltinShape_Tuple = 5,

    /**
     * The type inherits from built-in type ``list``. If using this shape, you
     * need to specify base class ``ctx->h_ListType``.
     */
    HPyType_BuiltinShape_List = 6,

    /**
     * The type inherits from built-in type ``dict``. If using this shape, you
     * need to specify base class ``ctx->h_DictType``.
     */
    HPyType_BuiltinShape_Dict = 7,
} HPyType_BuiltinShape;

typedef struct {
    cpy_vectorcallfunc cpy_trampoline;
    HPyCallFunction impl;
} HPyType_Vectorcall;

typedef struct {
    /** The Python name of type (UTF-8 encoded) */
    const char* name;

    /**
     * The size in bytes of the types associated native structure. Usually, you
     * define some C structure, e.g., ``typedef struct { int a; } MyObject;``,
     * and then this field is set to ``sizeof(MyObject)``.
     */
    int basicsize;

    /** The size of embedded elements (currently not supported). */
    int itemsize;

    /**
     * Type flags (see :c:macro:`HPy_TPFLAGS_DEFAULT`,
     * :c:macro:`HPy_TPFLAGS_BASETYPE`, :c:macro:`HPy_TPFLAGS_HAVE_GC`, and
     * others if available).
     */
    unsigned long flags;

    /**
     * The internal *shape* of the type.
     *
     * The shape gives the necessary hint to compute the offset to the data
     * pointer of the object's underlying struct that should be returned when
     * calling ``MyObject_AsStruct``.
     *
     * **ATTENTION**:
     * It is also necessary to specify the right base class in
     * the type's specification parameters (see :c:struct:`HPyType_SpecParam`).
     *
     * Assuming that the type's C structure is called ``MyObject``, this field
     * should be initialized with ``.builtin_shape = SHAPE(MyObject)``. Note:
     * This requires that you use :c:macro:`HPyType_HELPERS` or
     * :c:macro:`HPyType_LEGACY_HELPERS`.
     *
     * Some more explanation: It would be possible to reduce this information
     * to a Boolean that specifies if the type is a *legacy* type or not.
     * Everything else could be determined by looking at the base classes.
     * However, with this information it is possible to do the data pointer
     * computation statically and thus is performance critical.
     *
     * Types that do not define a struct of their own, should set the value of
     * ``.builtin_shape`` to the same value as the type they inherit from. If
     * they inherit from a built-in type, they must set the corresponding
     * ``.builtin_shape``.
     */
    HPyType_BuiltinShape builtin_shape;

    /**
     * Pointer to a ``NULL``-terminated array of legacy (i.e. ``PyType_Slot``)
     * slots.
     *
     * A type with ``.legacy_slots != NULL`` is required to have
     * ``HPyType_BuiltinShape_Legacy`` and to include ``PyObject_HEAD`` at the
     * start of its struct. It would be easy to relax this requirement on
     * CPython (where the ``PyObject_HEAD`` fields are always present) but a
     * large burden on other implementations (e.g. PyPy, GraalPy) where a
     * struct starting with ``PyObject_HEAD`` might not exist.
     */
    void *legacy_slots;

    /**
     * Pointer to a ``NULL``-terminated array of pointers to HPy defines (i.e.
     * ``HPyDef *``).
     */
    HPyDef **defines;

    /** Docstring of the type (UTF-8 encoded; may be ``NULL``) */
    const char* doc;
} HPyType_Spec;

typedef enum {
    /**
     * Specify a base class. This parameter may be repeated but cannot be used
     * together with
     * :c:enumerator:`HPyType_SpecParam_Kind.HPyType_SpecParam_BasesTuple`.
     */
    HPyType_SpecParam_Base = 1,

    /**
     * Specify a tuple of base classes. Cannot be used together with
     * :c:enumerator:`HPyType_SpecParam_Kind.HPyType_SpecParam_Base`
     */
    HPyType_SpecParam_BasesTuple = 2,

    /** Specify a meta class for the type. */
    HPyType_SpecParam_Metaclass = 3,

    //HPyType_SpecParam_Module = 4,
} HPyType_SpecParam_Kind;

typedef struct {
    /** The kind of the type spec param. */
    HPyType_SpecParam_Kind kind;

    /** The value of the type spec param (an HPy handle). */
    HPy object;
} HPyType_SpecParam;

/* All types are dynamically allocated */
#define _Py_TPFLAGS_HEAPTYPE (1UL << 9)
#define _Py_TPFLAGS_HAVE_VERSION_TAG (1UL << 18)

/** Default type flags for HPy types. */
#define HPy_TPFLAGS_DEFAULT (_Py_TPFLAGS_HEAPTYPE | _Py_TPFLAGS_HAVE_VERSION_TAG)

/** Set if the type implements the vectorcall protocol (PEP 590) */
#define HPy_TPFLAGS_HAVE_VECTORCALL (1UL << 11)

/** Set if the type allows subclassing */
#define HPy_TPFLAGS_BASETYPE (1UL << 10)

/** Set if the type allows subclassing */
#define HPy_TPFLAGS_BASETYPE (1UL << 10)

/** If set, the object will be tracked by CPython's GC. Probably irrelevant for
    GC-based alternative implementations. */
#define HPy_TPFLAGS_HAVE_GC (1UL << 14)

/** Convenience macro which is equivalent to:
    ``HPyType_HELPERS(TYPE, HPyType_BuiltinShape_Legacy)`` 
    For instance, HPyType_LEGACY_HELPERS(DummyMeta) will produce::

        enum { DummyMeta_SHAPE = (int)HPyType_BuiltinShape_Legacy }; 
        __attribute__((unused)) static inline 
        DummyMeta * 
        DummyMeta_AsStruct(HPyContext *ctx, HPy h) { 
            return (DummyMeta *) _HPy_AsStruct_Legacy(ctx, h); 
        }
*/
#define HPyType_LEGACY_HELPERS(TYPE) \
    HPyType_HELPERS(TYPE, HPyType_BuiltinShape_Legacy)

#define _HPyType_HELPER_TYPE(TYPE, ...) TYPE *
#define _HPyType_HELPER_FNAME(TYPE, ...) TYPE##_AsStruct
#define _HPyType_HELPER_DEFINE_SHAPE(TYPE, SHAPE, ...) \
    enum { TYPE##_SHAPE = (int)SHAPE }
#define _HPyType_HELPER_AS_STRUCT(TYPE, SHAPE, ...) SHAPE##_AsStruct
// helper macro make MSVC's preprocessor work with our variadic macros
#define _HPyType_HELPER_X(X) X

/**
   A macro for creating (static inline) helper functions for custom types.

   Two versions of the helper exist. One for legacy types and one for pure
   HPy types.

   Example for a pure HPy custom type:

       ``HPyType_HELPERS(PointObject)``

   It is also possible to inherit from some built-in types. The list of
   available built-in base types is given in enum `HPyTupe_BuiltinShape`.
   In case you want to inherit from one of those, it is necessary to specify
   the base built-in type in the `HPyType_HELPERS` macro. Here is an example
   for a pure HPy custom type inheriting from a built-in type 'tuple':

       ``HPyType_HELPERS(PointObject, HPyType_BuiltinShape_Tuple)``

   This would generate the following:

   * ``PointObject * PointObject_AsStruct(HPyContext *ctx, HPy h)``: a static
     inline function that uses HPy_AsStruct to return the PointObject struct
     associated with a given handle. The behaviour is undefined if `h`
     is associated with an object that is not an instance of PointObject.
     However, debug mode will catch an incorrect usage.

   * ``SHAPE(PointObject)``: a macro that is meant to be used as static
     initializer in the corresponding HPyType_Spec. It is recommended to write
     ``.builtin_shape = SHAPE(PointObject)`` such that you don't have to
     remember to update the spec when the helpers used changes.

   Example for a legacy custom type:

       ``HPyType_LEGACY_HELPERS(PointObject)``

   This would generate the same functions and constants as above, except:

   * ``_HPy_AsStruct_Legacy`` is used instead of ``_HPy_AsStruct_Object``.

   * ``SHAPE(PointObject)`` would be ``HPyType_BuiltinShape_Legacy``.

   :param STRUCT: The C structure of the HPy type.
   :param SHAPE: Optional. The built-in shape of the type. This defaults to
                 :c:enumerator:`HPyType_BuiltinShape_Object`. Possible values
                 are all enumerators of :c:enum:`HPyType_BuiltinShape`.
*/
#define HPyType_HELPERS(...)                                                  \
                                                                              \
_HPyType_HELPER_X(                                                            \
    _HPyType_HELPER_DEFINE_SHAPE(__VA_ARGS__, HPyType_BuiltinShape_Object));  \
                                                                              \
HPyAPI_UNUSED _HPyType_HELPER_X(_HPyType_HELPER_TYPE(__VA_ARGS__))            \
_HPyType_HELPER_X(_HPyType_HELPER_FNAME(__VA_ARGS__))(HPyContext *ctx, HPy h) \
{                                                                             \
    return (_HPyType_HELPER_X(_HPyType_HELPER_TYPE(__VA_ARGS__)))             \
            _HPyType_HELPER_X(_HPyType_HELPER_AS_STRUCT(__VA_ARGS__,          \
                                      HPyType_BuiltinShape_Object))(ctx, h);  \
}

#define SHAPE(TYPE) ((HPyType_BuiltinShape)TYPE##_SHAPE)

#define HPyType_BuiltinShape_Legacy_AsStruct _HPy_AsStruct_Legacy
#define HPyType_BuiltinShape_Object_AsStruct _HPy_AsStruct_Object
#define HPyType_BuiltinShape_Type_AsStruct _HPy_AsStruct_Type
#define HPyType_BuiltinShape_Long_AsStruct _HPy_AsStruct_Long
#define HPyType_BuiltinShape_Float_AsStruct _HPy_AsStruct_Float
#define HPyType_BuiltinShape_Unicode_AsStruct _HPy_AsStruct_Unicode
#define HPyType_BuiltinShape_Tuple_AsStruct _HPy_AsStruct_Tuple
#define HPyType_BuiltinShape_List_AsStruct _HPy_AsStruct_List
#define HPyType_BuiltinShape_Dict_AsStruct _HPy_AsStruct_Dict

#endif /* HPY_UNIVERSAL_HPYTYPE_H */
