
/* this is only included from the .c files in this directory: rename
   these pypymbc-prefixed names to locally define the CPython names */
typedef pypymbc_ssize_t Py_ssize_t;
#define PY_SSIZE_T_MAX   ((Py_ssize_t)(((size_t) -1) >> 1))
typedef pypymbc_ucs4_t Py_UCS4;
typedef pypymbc_ucs2_t ucs2_t, DBCHAR;
typedef struct pypy_cjk_dec_s _PyUnicodeWriter;
