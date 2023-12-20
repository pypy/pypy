#ifndef HPY_COMMON_RUNTIME_STRUCTSEQ_H
#define HPY_COMMON_RUNTIME_STRUCTSEQ_H

#include "hpy.h"

/*
 * Struct sequences are subclasses of tuple, so we provide a simplified API to
 * create them here. This maps closely to the CPython limited API for creating
 * struct sequences. However, in universal mode we use the
 * collections.namedtuple type to implement this, which behaves a bit
 * differently w.r.t. hidden elements. Thus, the n_in_sequence field available
 * in CPython's PyStructSequence_Desc is not available. Also, we use a builder
 * API like for tuples and lists so that the struct sequence is guaranteed not
 * to be written after it is created.
 */

/**
 * Describes a field of a struct sequence.
 */
typedef struct {
    /**
     * Name (UTF-8 encoded) for the field or ``NULL`` to end the list of named
     * fields. Set the name to :c:var:`HPyStructSequence_UnnamedField` to leave
     * it unnamed.
     */
    const char *name;

    /**
     * Docstring of the field (UTF-8 encoded); may be ``NULL``.
     */
    const char *doc;
} HPyStructSequence_Field;

/**
 * Contains the meta information of a struct sequence type to create.
 * Struct sequences are subclasses of tuple. The index in the :c:member:`fields`
 * array of the descriptor determines which field of the struct sequence is
 * described.
 */
typedef struct {
    /**
     * Name of the struct sequence type (UTF-8 encoded; must not be ``NULL``).
     */
    const char *name;

    /** Docstring of the type (UTF-8 encoded); may be ``NULL``. */
    const char *doc;

    /**
     * Pointer to ``NULL``-terminated array with field names of the new type
     * (must not be ``NULL``).
     */
    HPyStructSequence_Field *fields;
} HPyStructSequence_Desc;

/**
 * A marker that can be used as struct sequence field name to indicate that a
 * field should be anonymous (i.e. cannot be accessed by a name but only by
 * numeric index).
 */
extern const char * const HPyStructSequence_UnnamedField;

/**
 * Create a new struct sequence type from a descriptor. Instances of the
 * resulting type can be created with :c:func:`HPyStructSequence_New`.
 *
 * :param ctx:
 *     The execution context.
 * :param desc:
 *     The descriptor of the struct sequence type to create (must not be
 *     ``NULL``):
 *
 * :returns:
 *     A handle to the new struct sequence type or ``HPy_NULL`` in case of
 *     errors.
 */
HPyAPI_HELPER HPy
HPyStructSequence_NewType(HPyContext *ctx, HPyStructSequence_Desc *desc);

/**
 * Creates a new instance of ``type`` initializing it with the given arguments.
 *
 * Since struct sequences are immutable objects, they need to be initialized at
 * instantiation. This function will create a fresh instance of the provided
 * struct sequence type. The type must have been created with
 * :c:func:`HPyStructSequence_NewType`.
 *
 * :param ctx:
 *     The execution context.
 * :param type:
 *     A struct sequence type (must not be ``HPy_NULL``). If the passed object
 *     is not a type, the behavior is undefined. If the given type is not
 *     appropriate, a ``TypeError`` will be raised.
 * :param nargs:
 *     The number of arguments in ``args``. If this argument is not exactly the
 *     number of fields of the struct sequence, a ``TypeError`` will be raised.
 * :param args:
 *     An array of HPy handles to Python objects to be used for initializing
 *     the struct sequence. If ``nargs > 0`` then this argument must not be
 *     ``NULL``.
 *
 * :returns:
 *     A new instance of ``type`` or ``HPy_NULL`` if an error occurred.
 */
HPyAPI_HELPER HPy
HPyStructSequence_New(HPyContext *ctx, HPy type, HPy_ssize_t nargs, HPy *args);

#endif /* HPY_COMMON_RUNTIME_STRUCTSEQ_H */
