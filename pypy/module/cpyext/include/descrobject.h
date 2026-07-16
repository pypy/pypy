#ifndef Py_DESCROBJECT_H
#define Py_DESCROBJECT_H

#include "cpyext_descrobject.h"

// These constants used to be in structmember.h, not prefixed by Py_.
// (structmember.h now has aliases to the new names.)

/* Types */
#define Py_T_SHORT     0
#define Py_T_INT       1
#define Py_T_LONG      2
#define Py_T_FLOAT     3
#define Py_T_DOUBLE    4
#define Py_T_STRING    5
#define _Py_T_OBJECT   6  // Deprecated, use Py_T_OBJECT_EX instead
/* the ordering here is weird for binary compatibility */
#define Py_T_CHAR      7   /* 1-character string */
#define Py_T_BYTE      8   /* 8-bit signed int */
/* unsigned variants: */
#define Py_T_UBYTE     9
#define Py_T_USHORT    10
#define Py_T_UINT      11
#define Py_T_ULONG     12

/* Added by Jack: strings contained in the structure */
#define Py_T_STRING_INPLACE    13

/* Added by Lillo: bools contained in the structure (assumed char) */
#define Py_T_BOOL      14

#define Py_T_OBJECT_EX 16
#define Py_T_LONGLONG  17
#define Py_T_ULONGLONG 18

#define Py_T_PYSSIZET  19      /* Py_ssize_t */
#define _Py_T_NONE     20 // Deprecated. Value is always None.

/* Flags */
#define Py_READONLY            1
#define Py_AUDIT_READ          2 // Added in 3.10, harmless no-op before that
#define _Py_WRITE_RESTRICTED   4 // Deprecated, no-op. Do not reuse the value.
#define Py_RELATIVE_OFFSET     8

#endif
