#ifndef Py_STRUCTMEMBER_H
#define Py_STRUCTMEMBER_H
#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h> /* For offsetof */
#ifndef offsetof
#define offsetof(type, member) ( (int) & ((type*)0) -> member )
#endif


typedef struct PyMemberDef {
	/* Current version, use this */
	char *name;
	int type;
	Py_ssize_t offset;
	int flags;
	char *doc;
} PyMemberDef;


/* Types. These constants are also in structmemberdefs.py. */
#define T_SHORT		0
#define T_INT		1
#define T_LONG		2
#define T_FLOAT		3
#define T_DOUBLE	4
#define T_STRING	5
#define T_OBJECT	6
#define T_CHAR		7	/* 1-character string */
#define T_BYTE		8	/* 8-bit signed int */
#define T_UBYTE		9
#define T_USHORT	10
#define T_UINT		11
#define T_ULONG		12
#define T_STRING_INPLACE 13	/* Strings contained in the structure */
#define T_BOOL		14
#define T_OBJECT_EX	16	/* Like T_OBJECT, but raises AttributeError
				   when the value is NULL, instead of
				   converting to None. */
#define T_LONGLONG	17
#define T_ULONGLONG	18
#define T_PYSSIZET	19

/* Flags. These constants are also in structmemberdefs.py. */
#define READONLY      1
#define RO            READONLY                /* Shorthand */
#define READ_RESTRICTED 2
#define PY_WRITE_RESTRICTED 4
#define RESTRICTED    (READ_RESTRICTED | PY_WRITE_RESTRICTED)


#ifdef __cplusplus
}
#endif
#endif /* !Py_STRUCTMEMBER_H */
