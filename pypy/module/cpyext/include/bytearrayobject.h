/* ByteArray object interface */

#ifndef Py_BYTEARRAYOBJECT_H
#define Py_BYTEARRAYOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include <stdarg.h>

/* Type PyByteArrayObject represents a mutable array of bytes.
 * The Python API is that of a sequence;
 * the bytes are mapped to ints in [0, 256).
 * Bytes are not characters; they may be used to encode characters.
 * The only way to go between bytes and str/unicode is via encoding
 * and decoding.
 * For the convenience of C programmers, the bytes type is considered
 * to contain a char pointer, not an unsigned char pointer.
 */

/* Object layout */
typedef struct {
    PyObject_VAR_HEAD
    /* XXX(nnorwitz): should ob_exports be Py_ssize_t? */
    int ob_exports; /* how many buffer exports */
    Py_ssize_t ob_alloc; /* How many bytes allocated */
    char *ob_bytes;
} PyByteArrayObject;

#ifdef __cplusplus
}
#endif
#endif /* !Py_BYTEARRAYOBJECT_H */
