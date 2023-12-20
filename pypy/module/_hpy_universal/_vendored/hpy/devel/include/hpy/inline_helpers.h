#ifndef HPY_INLINE_HELPERS_H
#define HPY_INLINE_HELPERS_H

#if defined(_MSC_VER)
# include <malloc.h>  /* for alloca() */
#endif

#include <assert.h>

/**
 * Same as :c:func:`HPyErr_SetFromErrnoWithFilenameObjects` but passes
 * ``HPy_NULL`` to the optional arguments.
 *
 * :param ctx:
 *     The execution context.
 * :param h_type:
 *     The exception type to raise.
 *
 * :return:
 *     always returns ``HPy_NULL``
 */
HPyAPI_INLINE_HELPER HPy
HPyErr_SetFromErrno(HPyContext *ctx, HPy h_type)
{
    return HPyErr_SetFromErrnoWithFilenameObjects(ctx, h_type, HPy_NULL, HPy_NULL);
}

/**
 * Same as :c:func:`HPyErr_SetFromErrnoWithFilenameObjects` but passes
 * ``HPy_NULL`` to the last (optional) argument.
 *
 * :param ctx:
 *     The execution context.
 * :param h_type:
 *     The exception type to raise.
 * :param filename:
 *     a filename; may be ``HPy_NULL``
 *
 * :return:
 *     always returns ``HPy_NULL``
 */
HPyAPI_INLINE_HELPER HPy
HPyErr_SetFromErrnoWithFilenameObject(HPyContext *ctx, HPy h_type, HPy filename)
{
    return HPyErr_SetFromErrnoWithFilenameObjects(ctx, h_type, filename, HPy_NULL);
}

/**
 * Create a tuple from arguments.
 *
 * A convenience function that will allocate a temporary array of ``HPy``
 * elements and use :c:func:`HPyTuple_FromArray` to create a tuple.
 *
 * :param ctx:
 *     The execution context.
 * :param n:
 *     The number of elements to pack into a tuple.
 * :param ...:
 *     Variable number of ``HPy`` arguments.
 *
 * :return:
 *     A new tuple with ``n`` elements or ``HPy_NULL`` in case of an error
 *     occurred.
 */
HPyAPI_INLINE_HELPER HPy
HPyTuple_Pack(HPyContext *ctx, HPy_ssize_t n, ...)
{
    va_list vargs;
    HPy_ssize_t i;

    if (n == 0) {
        return HPyTuple_FromArray(ctx, (HPy*)NULL, n);
    }
    HPy *array = (HPy *)alloca(n * sizeof(HPy));
    va_start(vargs, n);
    if (array == NULL) {
        va_end(vargs);
        return HPy_NULL;
    }
    for (i = 0; i < n; i++) {
        array[i] = va_arg(vargs, HPy);
    }
    va_end(vargs);
    return HPyTuple_FromArray(ctx, array, n);
}

/**
 * Delete an attribute.
 *
 * This is the equivalent of the Python statement ``del o.attr_name``.
 *
 * :param ctx:
 *     The execution context.
 * :param obj:
 *     The object with the attribute.
 * :param name:
 *     The name (an unicode object) of the attribute.
 *
 * :return:
 *     ``0`` on success; ``-1`` in case of an error.
 */
HPyAPI_INLINE_HELPER int
HPy_DelAttr(HPyContext *ctx, HPy obj, HPy name)
{
    return HPy_SetAttr(ctx, obj, name, HPy_NULL);
}

/**
 * Delete an attribute.
 *
 * This is the equivalent of the Python statement ``del o.attr_name``.
 *
 * :param ctx:
 *     The execution context.
 * :param obj:
 *     The object with the attribute.
 * :param utf8_name:
 *     The name (an UTF-8 encoded C string) of the attribute.
 *
 * :return:
 *     ``0`` on success; ``-1`` in case of an error.
 */
HPyAPI_INLINE_HELPER int
HPy_DelAttr_s(HPyContext *ctx, HPy obj, const char *utf8_name)
{
    return HPy_SetAttr_s(ctx, obj, utf8_name, HPy_NULL);
}

/**
 * Create a Python long object from a C ``long`` value.
 *
 * :param ctx:
 *     The execution context.
 * :param l:
 *     A C long value.
 *
 * :return:
 *     A Python long object with the value of ``l`` or ``HPy_NULL`` on failure.
 */
HPyAPI_INLINE_HELPER HPy
HPyLong_FromLong(HPyContext *ctx, long l)
{
    if (sizeof(long) <= sizeof(int32_t))
        return HPyLong_FromInt32_t(ctx, (int32_t)l);
    assert(sizeof(long) <= sizeof(int64_t));
    return HPyLong_FromInt64_t(ctx, (int64_t)l);
}

/**
 * Create a Python long object from a C ``unsigned long`` value.
 *
 * :param ctx:
 *     The execution context.
 * :param l:
 *     A C ``unsigned long`` value.
 *
 * :return:
 *     A Python long object with the value of ``l`` or ``HPy_NULL`` on failure.
 */
HPyAPI_INLINE_HELPER HPy
HPyLong_FromUnsignedLong(HPyContext *ctx, unsigned long l)
{
    if (sizeof(unsigned long) <= sizeof(uint32_t))
        return HPyLong_FromUInt32_t(ctx, (uint32_t)l);
    assert(sizeof(unsigned long) <= sizeof(uint64_t));
    return HPyLong_FromUInt64_t(ctx, (uint64_t)l);
}

/**
 * Create a Python long object from a C ``long long`` value.
 *
 * :param ctx:
 *     The execution context.
 * :param l:
 *     A C ``long long`` value.
 *
 * :return:
 *     A Python long object with the value of ``l`` or ``HPy_NULL`` on failure.
 */
HPyAPI_INLINE_HELPER HPy
HPyLong_FromLongLong(HPyContext *ctx, long long l)
{
    assert(sizeof(long long) <= sizeof(int64_t));
    return HPyLong_FromInt64_t(ctx, (int64_t)l);
}

/**
 * Create a Python long object from a C ``unsigned long long`` value.
 *
 * :param ctx:
 *     The execution context.
 * :param l:
 *     A C ``unsigned long long`` value.
 *
 * :return:
 *     A Python long object with the value of ``l`` or ``HPy_NULL`` on failure.
 */
HPyAPI_INLINE_HELPER HPy
HPyLong_FromUnsignedLongLong(HPyContext *ctx, unsigned long long l)
{
    assert(sizeof(unsigned long long) <= sizeof(uint64_t));
    return HPyLong_FromUInt64_t(ctx, (uint64_t)l);
}

/**
 * Return a C ``long`` representation of the given Python long object. If the
 * object is not an instance of Python long, the object's ``__index__`` method
 * (if present) will be used to convert it to a Python long object.
 *
 * This function will raise an ``OverflowError`` if the value of the object is
 * out of range for a C ``long``.
 *
 * This function will raise a ``TypeError`` if:
 *
 * * The object is neither an instance of Python long nor it provides an
 *   ``__index__`` method.
 * * If the ``__index__`` method does not return an instance of Python long.
 *
 * :param ctx:
 *     The execution context.
 * :param h:
 *     Either an instance of Python long or an object that provides an
 *     ``__index__`` method (which returns a Python long).
 *
 * :return:
 *     A C ``long`` value. Errors will be indicated with return value ``-1``.
 *     In this case, use :c:func:`HPyErr_Occurred` to disambiguate.
 */
HPyAPI_INLINE_HELPER long
HPyLong_AsLong(HPyContext *ctx, HPy h)
{
    if (sizeof(long) <= sizeof(int32_t))
        return (long) HPyLong_AsInt32_t(ctx, h);
    else if (sizeof(long) <= sizeof(int64_t))
        return (long) HPyLong_AsInt64_t(ctx, h);
}

/**
 * Return a C ``unsigned long`` representation of the given Python long object.
 *
 * This function will raise a ``TypeError`` if the object is not an instance of
 * Python long and it will raise an ``OverflowError`` if the object's value is
 * negative or out of range for a C ``unsigned long``.
 *
 * :param ctx:
 *     The execution context.
 * :param h:
 *     The object to convert to C ``unsigned long`` (must be an instance of
 *     Python long).
 *
 * :return:
 *     A C ``unsigned long`` value. Errors will be indicated with return value
 *     ``(unsigned long)-1``. In this case, use :c:func:`HPyErr_Occurred` to
 *     disambiguate.
 */
HPyAPI_INLINE_HELPER unsigned long
HPyLong_AsUnsignedLong(HPyContext *ctx, HPy h)
{
    if (sizeof(unsigned long) <= sizeof(uint32_t))
        return (unsigned long) HPyLong_AsUInt32_t(ctx, h);
    else if (sizeof(unsigned long) <= sizeof(uint64_t))
        return (unsigned long) HPyLong_AsUInt64_t(ctx, h);
}

/**
 * Return a C ``unsigned long`` representation of the given Python long object. If the
 * object is not an instance of Python long, the object's ``__index__`` method
 * (if present) will be used to convert it to a Python long object.
 *
 * If the object's value is out of range for an ``unsigned long``, return the
 * reduction of that value modulo ``ULONG_MAX + 1``. Therefore, this function
 * will **NOT** raise an ``OverflowError`` if the value of the object is out of
 * range for a C ``unsigned long``.
 *
 * :param ctx:
 *     The execution context.
 * :param h:
 *     Either an instance of Python long or an object that provides an
 *     ``__index__`` method (which returns a Python long).
 *
 * :return:
 *     A C ``unsigned long`` value. Errors will be indicated with return value
 *     ``(unsigned long)-1``. In this case, use :c:func:`HPyErr_Occurred` to
 *     disambiguate.
 */
HPyAPI_INLINE_HELPER unsigned long
HPyLong_AsUnsignedLongMask(HPyContext *ctx, HPy h)
{
    if (sizeof(unsigned long) <= sizeof(uint32_t))
        return (unsigned long) HPyLong_AsUInt32_tMask(ctx, h);
    else if (sizeof(unsigned long) <= sizeof(uint64_t))
        return (unsigned long) HPyLong_AsUInt64_tMask(ctx, h);
}

/**
 * Return a C ``long long`` representation of the given Python long object. If
 * the object is not an instance of Python long, the object's ``__index__``
 * method (if present) will be used to convert it to a Python long object.
 *
 * This function will raise an ``OverflowError`` if the value of the object is
 * out of range for a C ``long long``.
 *
 * This function will raise a ``TypeError`` if:
 *
 * * The object is neither an instance of Python long nor it provides an
 *   ``__index__`` method.
 * * If the ``__index__`` method does not return an instance of Python long.
 *
 * :param ctx:
 *     The execution context.
 * :param h:
 *     Either an instance of Python long or an object that provides an
 *     ``__index__`` method (which returns a Python long).
 *
 * :return:
 *     A C ``long long`` value. Errors will be indicated with return value
 *     ``-1``. In this case, use :c:func:`HPyErr_Occurred` to disambiguate.
 */
HPyAPI_INLINE_HELPER long long
HPyLong_AsLongLong(HPyContext *ctx, HPy h)
{
    assert(sizeof(long long) <= sizeof(int64_t));
    return (long long) HPyLong_AsInt64_t(ctx, h);
}

/**
 * Return a C ``unsigned long long`` representation of the given Python long
 * object.
 *
 * This function will raise a ``TypeError`` if the object is not an instance of
 * Python long and it will raise an ``OverflowError`` if the object's value is
 * negative or out of range for a C ``unsigned long``.
 *
 * :param ctx:
 *     The execution context.
 * :param h:
 *     The object to convert to C ``unsigned long long`` (must be an instance of
 *     Python long).
 *
 * :return:
 *     A C ``unsigned long long`` value. Errors will be indicated with return
 *     value ``(unsigned long long)-1``. In this case, use
 *     :c:func:`HPyErr_Occurred` to disambiguate.
 */
HPyAPI_INLINE_HELPER unsigned long long
HPyLong_AsUnsignedLongLong(HPyContext *ctx, HPy h)
{
    assert(sizeof(unsigned long long) <= sizeof(uint64_t));
    return (unsigned long long) HPyLong_AsUInt64_t(ctx, h);
}

/**
 * Return a C ``unsigned long long`` representation of the given Python long
 * object. If the object is not an instance of Python long, the object's
 * ``__index__`` method (if present) will be used to convert it to a Python long
 * object.
 *
 * If the object's value is out of range for an ``unsigned long long``, return
 * the reduction of that value modulo ``ULLONG_MAX + 1``. Therefore, this
 * function will **NOT** raise an ``OverflowError`` if the value of the object
 * is out of range for a C ``unsigned long long``.
 *
 * :param ctx:
 *     The execution context.
 * :param h:
 *     Either an instance of Python long or an object that provides an
 *     ``__index__`` method (which returns a Python long).
 *
 * :return:
 *     A C ``unsigned long`` value. Errors will be indicated with return value
 *     ``(unsigned long long)-1``. In this case, use :c:func:`HPyErr_Occurred`
 *     to disambiguate.
 */
HPyAPI_INLINE_HELPER unsigned long long
HPyLong_AsUnsignedLongLongMask(HPyContext *ctx, HPy h)
{
    assert(sizeof(unsigned long long) <= sizeof(uint64_t));
    return (unsigned long long) HPyLong_AsUInt64_tMask(ctx, h);
}

/**
 * Returns Python ``True`` or ``False`` depending on the truth value of ``v``.
 *
 * :param ctx:
 *     The execution context.
 * :param v:
 *     A C ``long`` value.
 *
 * :return:
 *     Python ``True`` if ``v != 0``; Python ``False`` otherwise.
 */
HPyAPI_INLINE_HELPER HPy
HPyBool_FromLong(HPyContext *ctx, long v)
{
    return HPyBool_FromBool(ctx, (v ? true : false));
}

/**
 * Adjust start/end slice indices assuming a sequence of the specified length.
 *
 * Out of bounds indices are clipped in a manner consistent with the handling of
 * normal slices. This function cannot fail and does not call interpreter
 * routines.
 *
 * :param ctx:
 *     The execution context.
 * :param length:
 *     The length of the sequence that should be assumed for adjusting the
 *     indices.
 * :param start:
 *     Pointer to the start value (must not be ``NULL``).
 * :param stop:
 *     Pointer to the stop value (must not be ``NULL``).
 * :param step:
 *     The step value of the slice (must not be ``0``)
 *
 * :return:
 *     Return the length of the slice. Always successful. Doesn’t call Python code.
 */
HPyAPI_INLINE_HELPER HPy_ssize_t
HPySlice_AdjustIndices(HPyContext *_HPy_UNUSED_ARG(ctx), HPy_ssize_t length,
        HPy_ssize_t *start, HPy_ssize_t *stop, HPy_ssize_t step)
{
    /* Taken from CPython: Written by Jim Hugunin and Chris Chase. */
    /* this is harder to get right than you might think */
    assert(step != 0);
    assert(step >= -HPY_SSIZE_T_MAX);

    if (*start < 0) {
        *start += length;
        if (*start < 0) {
            *start = (step < 0) ? -1 : 0;
        }
    }
    else if (*start >= length) {
        *start = (step < 0) ? length - 1 : length;
    }

    if (*stop < 0) {
        *stop += length;
        if (*stop < 0) {
            *stop = (step < 0) ? -1 : 0;
        }
    }
    else if (*stop >= length) {
        *stop = (step < 0) ? length - 1 : length;
    }

    if (step < 0) {
        if (*stop < *start) {
            return (*start - *stop - 1) / (-step) + 1;
        }
    }
    else {
        if (*start < *stop) {
            return (*stop - *start - 1) / step + 1;
        }
    }
    return 0;
}

/**
 * Call a method of a Python object.
 *
 * This is a convenience function for calling a method. It uses
 * :c:func:`HPy_GetAttr_s` and :c:func:`HPy_CallTupleDict` to perform the method
 * call.
 *
 * :param ctx:
 *     The execution context.
 * :param utf8_name:
 *     The name (UTF-8 encoded C string) of the method. Must not be ``NULL``.
 * :param receiver:
 *     A handle to the receiver of the call (i.e. the ``self``). Must not be
 *     ``HPy_NULL``.
 * :param args:
 *     A handle to a tuple containing the positional arguments (must not be
 *     ``HPy_NULL`` but can, of course, be empty).
 * :param kw:
 *     A handle to a Python dictionary containing the keyword arguments (may be
 *     ``HPy_NULL``).
 *
 * :returns:
 *     The result of the call on success, or ``HPy_NULL`` in case of an error.
 */
HPyAPI_INLINE_HELPER HPy
HPy_CallMethodTupleDict_s(HPyContext *ctx, const char *utf8_name, HPy receiver, HPy args, HPy kw)
{
    HPy method = HPy_GetAttr_s(ctx, receiver, utf8_name);
    if (HPy_IsNull(method)) {
        return HPy_NULL;
    }

    HPy result = HPy_CallTupleDict(ctx, method, args, kw);
    HPy_Close(ctx, method);
    return result;
}

/**
 * Call a method of a Python object.
 *
 * This is a convenience function for calling a method. It uses
 * :c:func:`HPy_GetAttr` and :c:func:`HPy_CallTupleDict` to perform the method
 * call.
 *
 * :param ctx:
 *     The execution context.
 * :param name:
 *     A handle to the name (a Unicode object) of the method. Must not be
 *     ``HPy_NULL``.
 * :param receiver:
 *     A handle to the receiver of the call (i.e. the ``self``). Must not be
 *     ``HPy_NULL``.
 * :param args:
 *     A handle to a tuple containing the positional arguments (must not be
 *     ``HPy_NULL`` but can, of course, be empty).
 * :param kw:
 *     A handle to a Python dictionary containing the keyword arguments (may be
 *     ``HPy_NULL``).
 *
 * :returns:
 *     The result of the call on success, or ``HPy_NULL`` in case of an error.
 */
HPyAPI_INLINE_HELPER HPy
HPy_CallMethodTupleDict(HPyContext *ctx, HPy name, HPy receiver, HPy args, HPy kw)
{
    HPy method = HPy_GetAttr(ctx, receiver, name);
    if (HPy_IsNull(method)) {
        return HPy_NULL;
    }

    HPy result = HPy_CallTupleDict(ctx, method, args, kw);
    HPy_Close(ctx, method);
    return result;
}

#endif //HPY_INLINE_HELPERS_H
