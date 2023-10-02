#ifndef HPY_UNIVERSAL_HPYDEF_H
#define HPY_UNIVERSAL_HPYDEF_H
#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h> /* to make sure "offsetof" is available for our users */

#include "hpy/hpyfunc.h"
#include "hpy/autogen_hpyslot.h"
#include "hpy/cpy_types.h"

typedef void* (*HPyCFunction)(void);
typedef void (*HPyFunc_Capsule_Destructor)(const char *name, void *pointer, void *context);

/**
 * C structure to define an HPy slot.
 *
 * It is perfectly fine to fill this structure manually. However, the
 * recommended and easier way is to use macro :c:macro:`HPyDef_SLOT`.
 */
typedef struct {
    /**
     * The slot to fill.
     */
    HPySlot_Slot slot;

    /** Function pointer to the slot's implementation */
    HPyCFunction impl;

    /**
     * Function pointer to the CPython trampoline function which is used by
     * CPython to call the actual HPy function ``impl``.
     */
    cpy_PyCFunction cpy_trampoline;
} HPySlot;

/**
 * C structure to define an HPy method.
 *
 * It is perfectly fine to fill this structure manually. However, the
 * recommended and easier way is to use macro :c:macro:`HPyDef_METH`.
 */
typedef struct {
    /** The name of Python attribute (UTF-8 encoded) */
    const char *name;

    /** Function pointer of the C function implementation */
    HPyCFunction impl;

    /**
     * Function pointer to the CPython trampoline function which is used by
     * CPython to call the actual HPy function ``impl``.
     */
    cpy_PyCFunction cpy_trampoline;

    /** Indicates the C function's expected signature */
    HPyFunc_Signature signature;

    /** Docstring of the method (UTF-8 encoded; may be ``NULL``) */
    const char *doc;

} HPyMeth;

/**
 * Describes the type (and therefore also the size) of an HPy member.
 */
typedef enum {
    HPyMember_SHORT = 0,
    HPyMember_INT = 1,
    HPyMember_LONG = 2,
    HPyMember_FLOAT = 3,
    HPyMember_DOUBLE = 4,
    HPyMember_STRING = 5,
    HPyMember_OBJECT = 6,
    HPyMember_CHAR = 7,   /* 1-character string */
    HPyMember_BYTE = 8,   /* 8-bit signed int */
    /* unsigned variants: */
    HPyMember_UBYTE = 9,
    HPyMember_USHORT = 10,
    HPyMember_UINT = 11,
    HPyMember_ULONG = 12,

    /* Added by Jack: strings contained in the structure */
    HPyMember_STRING_INPLACE = 13,

    /* Added by Lillo: bools contained in the structure (assumed char) */
    HPyMember_BOOL = 14,
    HPyMember_OBJECT_EX = 16,  /* Like T_OBJECT, but raises AttributeError
                                  when the value is NULL, instead of
                                  converting to None. */
    HPyMember_LONGLONG = 17,
    HPyMember_ULONGLONG = 18,

    HPyMember_HPYSSIZET = 19,  /* HPy_ssize_t */
    HPyMember_NONE = 20,       /* Value is always None */

} HPyMember_FieldType;

/**
 * C structure to define an HPy member.
 *
 * It is perfectly fine to fill this structure manually. However, the
 * recommended and easier way is to use macro :c:macro:`HPyDef_MEMBER`.
 */
typedef struct {
    /** The name of Python attribute (UTF-8 encoded) */
    const char *name;

    /** The type of the HPy member (see enum ``HPyMember_FieldType``). */
    HPyMember_FieldType type;

    /**
     * The location (byte offset) of the member. Usually computed with
     * ``offsetof(type, field)``.
     */
    HPy_ssize_t offset;

    /** Flag indicating if the member is read-only */
    int readonly;

    /** Docstring of the member (UTF-8 encoded; may be ``NULL``) */
    const char *doc;
} HPyMember;

/**
 * C structure to define an HPy get/set descriptor.
 *
 * It is perfectly fine to fill this structure manually. However, the
 * recommended and easier way is to use macros :c:macro:`HPyDef_GET` (to create
 * a get descriptor only), :c:macro:`HPyDef_SET` (to create a set descriptor
 * only), or :c:macro:`HPyDef_GETSET` (to create both).
 */
typedef struct {
    /** The name of Python attribute (UTF-8 encoded) */
    const char *name;

    /** Function pointer of the C getter function (may be ``NULL``) */
    HPyCFunction getter_impl;

    /** Function pointer of the C setter function (may be ``NULL``) */
    HPyCFunction setter_impl;

    /**
     * Function pointer to the CPython trampoline function for the getter (may
     * be ``NULL`` if (and only if) ``getter_impl == NULL``)
     */
    cpy_getter getter_cpy_trampoline;

    /**
     * Function pointer to the CPython trampoline function for the setter (may
     * be ``NULL`` if (and only if) ``setter_impl == NULL``)
     */
    cpy_setter setter_cpy_trampoline;

    /** Docstring of the get/set descriptor (UTF-8 encoded; may be ``NULL``) */
    const char *doc;

    /**
     * A value that will be passed to the ``getter_impl``/``setter_impl``
     * functions.
     */
    void *closure;

} HPyGetSet;

/**
 * Enum to identify an HPy definition's kind.
 */
typedef enum {
    HPyDef_Kind_Slot = 1,
    HPyDef_Kind_Meth = 2,
    HPyDef_Kind_Member = 3,
    HPyDef_Kind_GetSet = 4,
} HPyDef_Kind;

/**
 * Generic structure of an HPy definition.
 *
 * This struct can be used to define a slot, method, member, or get/set
 * descriptor. For details, see embedded structures :c:struct:`HPySlot`,
 * :c:struct:`HPyMeth`, :c:struct:`HPyMember`, or :c:struct:`HPyGetSet`.
 */
typedef struct {
    /**
     * The kind of this definition.
     * The value of this field determines which one of the embedded members
     * ``slot``, ``meth``, ``member``, or ``getset`` is used. Since those are
     * combined in a union, only one can be used at a time.
     */
    HPyDef_Kind kind;

    union {
        HPySlot slot;
        HPyMeth meth;
        HPyMember member;
        HPyGetSet getset;
    };
} HPyDef;

typedef struct {
    cpy_PyCapsule_Destructor cpy_trampoline;
    HPyFunc_Capsule_Destructor impl;
} HPyCapsule_Destructor;

typedef struct {
    cpy_vectorcallfunc cpy_trampoline;
    HPyFunc_keywords impl;
} HPyCallFunction;

// macros to automatically define HPyDefs of various kinds

/* ~~~ HPySlot_SIG ~~~

  Macro-magic to automatically determine the HPyFunc_Signature from a
  symbolic slot name such as HPy_tp_repr, HPy_nb_add, etc.
 */

#define HPySlot_SIG(SLOT) _HPySlot_SIG__##SLOT
// Macros such as _HPySlot_SIG__HPy_tp_add &co. are defined in autogen_hpyslot.h



/* ~~~ HPyDef_SLOT ~~~

   This is the official version of HPyDef_SLOT, which automatically determines
   the SIG from the SLOT. The anonymous enum is needed to get a nice
   compile-time error in case we pass a SLOT which does not exist, see the
   more detailed explanation in the comments around HPyFunc_DECLARE in
   hpyfunc.h
*/
#define HPyDef_SLOT_IMPL(SYM, IMPL, SLOT)            \
    enum { SYM##_slot = SLOT };                      \
    _HPyDef_SLOT(SYM, IMPL, SLOT, HPySlot_SIG(SLOT))

/**
 * A convenience macro and recommended way to create a definition for an HPy
 * slot.
 *
 * The macro generates a C global variable and an appropriate CPython
 * trampoline function. It will fill an :c:struct:`HPyDef` structure appropriately
 * and store it in the global variable.
 *
 * This macro expects a C function ``SYM_impl`` that will be used as the
 * implementing slot function.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated HPy definition. The variable is defined
 *             as ``static``.
 * :param SLOT: The HPy slot identifier.
 */
#define HPyDef_SLOT(SYM, SLOT) \
    HPyDef_SLOT_IMPL(SYM, SYM##_impl, SLOT)

// this is the actual implementation, after we determined the SIG
#define _HPyDef_SLOT(SYM, IMPL, SLOT, SIG)                              \
    HPyFunc_DECLARE(IMPL, SIG);                                         \
    HPyFunc_TRAMPOLINE(SYM##_trampoline, IMPL, SIG);                    \
    HPyDef SYM = {                                                      \
        .kind = HPyDef_Kind_Slot,                                       \
        .slot = {                                                       \
            .slot = SLOT,                                               \
            .impl = (HPyCFunction)IMPL,                                 \
            .cpy_trampoline = (cpy_PyCFunction)SYM##_trampoline         \
        }                                                               \
    };


#define HPyDef_METH_IMPL(SYM, NAME, IMPL, SIG, ...)                     \
    HPyFunc_DECLARE(IMPL, SIG);                                         \
    HPyFunc_TRAMPOLINE(SYM##_trampoline, IMPL, SIG)                     \
    HPyDef SYM = {                                                      \
        .kind = HPyDef_Kind_Meth,                                       \
        .meth = {                                                       \
            .name = NAME,                                               \
            .impl = (HPyCFunction)IMPL,                                 \
            .cpy_trampoline = (cpy_PyCFunction)SYM##_trampoline,        \
            .signature = SIG,                                           \
            __VA_ARGS__                                                 \
        }                                                               \
    };

/**
 * A convenience macro and recommended way to create a definition for an HPy
 * method.
 *
 * The macro generates a C global variable and an appropriate CPython
 * trampoline function. It will fill an :c:struct:`HPyDef` structure appropriately
 * and store it in the global variable.
 *
 * This macro expects a C function ``SYM_impl`` that will be used as the
 * implementing C function.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated HPy definition. The variable is defined
 *             as ``static``.
 * :param NAME: The Python attribute name (UTF-8 encoded).
 * :param SIG: The implementation's C signature (see
 *             :c:enum:`HPyFunc_Signature`).
 */
#define HPyDef_METH(SYM, NAME, SIG, ...) \
    HPyDef_METH_IMPL(SYM, NAME, SYM##_impl, SIG, __VA_ARGS__)

/**
 * A convenience macro and recommended way to create a definition for an HPy
 * member.
 *
 * The macro generates a C global variable. It will fill an :c:struct:`HPyDef`
 * structure appropriately and store it in the global variable.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated HPy definition. The variable is defined
 *             as ``static``.
 * :param NAME: The Python attribute name (UTF-8 encoded).
 * :param TYPE: The implementation's C signature (see
 *             :c:enum:`HPyFunc_Signature`).
 * :param OFFSET: The Python attribute name (UTF-8 encoded).
 * :param .readonly: Optional flag indicating if the member is read-only.
 * :param .doc: Optional docstring (UTF-8 encoded).
 */
#define HPyDef_MEMBER(SYM, NAME, TYPE, OFFSET, ...) \
    HPyDef SYM = {                                  \
        .kind = HPyDef_Kind_Member,                 \
        .member = {                                 \
            .name = NAME,                           \
            .type = TYPE,                           \
            .offset = OFFSET,                       \
            __VA_ARGS__                             \
        }                                           \
    };

#define HPyDef_GET_IMPL(SYM, NAME, GETIMPL, ...)                                \
    HPyFunc_DECLARE(GETIMPL, HPyFunc_GETTER);                                   \
    HPyFunc_TRAMPOLINE(SYM##_get_trampoline, GETIMPL, HPyFunc_GETTER);          \
    HPyDef SYM = {                                                              \
        .kind = HPyDef_Kind_GetSet,                                             \
        .getset = {                                                             \
            .name = NAME,                                                       \
            .getter_impl = (HPyCFunction)GETIMPL,                               \
            .getter_cpy_trampoline = (cpy_getter)SYM##_get_trampoline,          \
            __VA_ARGS__                                                         \
        }                                                                       \
    };

/**
 * A convenience macro and recommended way to create a definition for an HPy
 * get descriptor.
 *
 * The macro generates a C global variable. It will fill an :c:struct:`HPyDef`
 * structure appropriately and store it in the global variable.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated HPy definition. The variable is defined
 *             as ``static``.
 * :param NAME: The Python attribute name (UTF-8 encoded).
 * :param .doc: Optional docstring (UTF-8 encoded).
 * :param .closure: Optional pointer, providing additional data for the getter.
 */
#define HPyDef_GET(SYM, NAME, ...) \
    HPyDef_GET_IMPL(SYM, NAME, SYM##_get, __VA_ARGS__)

#define HPyDef_SET_IMPL(SYM, NAME, SETIMPL, ...)                                \
    HPyFunc_DECLARE(SETIMPL, HPyFunc_SETTER);                                   \
    HPyFunc_TRAMPOLINE(SYM##_set_trampoline, SETIMPL, HPyFunc_SETTER);          \
    HPyDef SYM = {                                                              \
        .kind = HPyDef_Kind_GetSet,                                             \
        .getset = {                                                             \
            .name = NAME,                                                       \
            .setter_impl = (HPyCFunction)SETIMPL,                               \
            .setter_cpy_trampoline = (cpy_setter)SYM##_set_trampoline,          \
            __VA_ARGS__                                                         \
        }                                                                       \
    };

/**
 * A convenience macro and recommended way to create a definition for an HPy
 * set descriptor.
 *
 * The macro generates a C global variable. It will fill an :c:struct:`HPyDef`
 * structure appropriately and store it in the global variable.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated HPy definition. The variable is defined
 *             as ``static``.
 * :param NAME: The Python attribute name (UTF-8 encoded).
 * :param .doc: Optional docstring (UTF-8 encoded).
 * :param .closure: Optional pointer, providing additional data for the setter.
 */
#define HPyDef_SET(SYM, NAME, ...) \
    HPyDef_SET_IMPL(SYM, NAME, SYM##_set, __VA_ARGS__)

#define HPyDef_GETSET_IMPL(SYM, NAME, GETIMPL, SETIMPL, ...)                    \
    HPyFunc_DECLARE(GETIMPL, HPyFunc_GETTER);                                   \
    HPyFunc_TRAMPOLINE(SYM##_get_trampoline, GETIMPL, HPyFunc_GETTER);          \
    HPyFunc_DECLARE(SETIMPL, HPyFunc_SETTER);                                   \
    HPyFunc_TRAMPOLINE(SYM##_set_trampoline, SETIMPL, HPyFunc_SETTER);          \
    HPyDef SYM = {                                                              \
        .kind = HPyDef_Kind_GetSet,                                             \
        .getset = {                                                             \
            .name = NAME,                                                       \
            .getter_impl = (HPyCFunction)GETIMPL,                               \
            .setter_impl = (HPyCFunction)SETIMPL,                               \
            .getter_cpy_trampoline = (cpy_getter)SYM##_get_trampoline,          \
            .setter_cpy_trampoline = (cpy_setter)SYM##_set_trampoline,          \
            __VA_ARGS__                                                         \
        }                                                                       \
    };

/**
 * A convenience macro and recommended way to create a definition for an HPy
 * get/set descriptor.
 *
 * The macro generates a C global variable. It will fill an :c:struct:`HPyDef`
 * structure appropriately and store it in the global variable.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated HPy definition. The variable is defined
 *             as ``static``.
 * :param NAME: The Python attribute name (UTF-8 encoded).
 * :param .doc: Optional docstring (UTF-8 encoded).
 * :param .closure: Optional pointer, providing additional data for the getter
 *                  and setter.
 */
#define HPyDef_GETSET(SYM, NAME, ...) \
    HPyDef_GETSET_IMPL(SYM, NAME, SYM##_get, SYM##_set, __VA_ARGS__)

#define HPyCapsule_DESTRUCTOR(SYM)                                             \
    static void SYM##_impl(const char *name, void *pointer, void *context);    \
    HPyCapsule_DESTRUCTOR_TRAMPOLINE(SYM##_trampoline, SYM##_impl);            \
    static HPyCapsule_Destructor SYM = {                                       \
        .cpy_trampoline = SYM##_trampoline,                                    \
        .impl = SYM##_impl                                                     \
    };

/**
 * A convenience macro and the recommended way to create a call function
 * definition.
 *
 * The macro generates a C global variable with name ``SYM``. It will fill an
 * :c:struct:`HPyCallFunction` structure appropriately and store it in the
 * global variable.
 *
 * This macro expects a C function ``SYM_impl`` that will be used as the
 * implementing C function.
 *
 * :param SYM: A C symbol name of the resulting global variable that will
 *             contain the generated call function definition. The variable is
 *             defined as ``static``.
 */
#define HPyDef_CALL_FUNCTION(SYM)                                             \
    HPyFunc_DECLARE(SYM##_impl, HPyFunc_KEYWORDS);                            \
    HPyFunc_TRAMPOLINE(SYM##_trampoline, SYM##_impl, HPyFunc_KEYWORDS);       \
    static HPyCallFunction SYM = {                                            \
        .cpy_trampoline = SYM##_trampoline,                                   \
        .impl = SYM##_impl                                                    \
    };

#ifdef __cplusplus
}
#endif
#endif /* HPY_UNIVERSAL_HPYDEF_H */
