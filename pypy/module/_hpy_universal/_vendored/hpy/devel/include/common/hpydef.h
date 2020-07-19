#ifndef HPY_UNIVERSAL_HPYDEF_H
#define HPY_UNIVERSAL_HPYDEF_H

#include "common/hpyfunc.h"
#include "common/typeslots.h"

typedef struct {
    HPySlot_Slot slot;     // The slot to fill
    void *impl;            // Function pointer to the implementation
    void *cpy_trampoline;  // Used by CPython to call impl
} HPySlot;

typedef struct {
    const char *name;             // The name of the built-in function/method
    const char *doc;              // The __doc__ attribute, or NULL
    void *impl;                   // Function pointer to the implementation
    void *cpy_trampoline;         // Used by CPython to call impl
    HPyFunc_Signature signature;  // Indicates impl's expected the signature
} HPyMeth;

/*
typedef struct {
    ...
} HPyMember;

typedef struct {
    ...
} HPyGetSet;
*/

typedef enum {
    HPyDef_Kind_Slot = 1,
    HPyDef_Kind_Meth = 2
    // HPyDef_Kind_Member = 3,
    // HPyDef_Kind_GetSet = 4,
} HPyDef_Kind;

typedef struct {
    HPyDef_Kind kind;
    union {
        HPySlot slot;
        HPyMeth meth;
        // HPyMember member;
        // HPyGetSet getset;
    };
} HPyDef;

// macros to automatically define HPyDefs of various kinds

#define HPyDef_SLOT(SYM, SLOT, IMPL, SIG)                               \
    HPyFunc_DECLARE(IMPL, SIG);                                         \
    HPyFunc_TRAMPOLINE(SYM##_trampoline, IMPL, SIG);                    \
    HPyDef SYM = {                                                      \
        .kind = HPyDef_Kind_Slot,                                       \
        .slot = {                                                       \
            .slot = SLOT,                                               \
            .impl = IMPL,                                               \
            .cpy_trampoline = SYM##_trampoline                          \
        }                                                               \
    };


#define HPyDef_METH(SYM, NAME, IMPL, SIG)                               \
    HPyFunc_DECLARE(IMPL, SIG);                                         \
    HPyFunc_TRAMPOLINE(SYM##_trampoline, IMPL, SIG);                    \
    HPyDef SYM = {                                                      \
        .kind = HPyDef_Kind_Meth,                                       \
        .meth = {                                                       \
            .name = NAME,                                               \
            .impl = IMPL,                                               \
            .cpy_trampoline = SYM##_trampoline,                         \
            .signature = SIG                                            \
        }                                                               \
    };

#endif /* HPY_UNIVERSAL_HPYDEF_H */
