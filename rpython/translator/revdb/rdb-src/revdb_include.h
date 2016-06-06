#include <string.h>

RPY_EXTERN void rpy_reverse_db_setup(int *argc_p, char **argv_p[]);
RPY_EXTERN void rpy_reverse_db_teardown(void);

typedef struct { char *buf_p, *buf_limit; } rpy_revdb_t;
RPY_EXTERN rpy_revdb_t rpy_revdb;


/* ------------------------------------------------------------ */
#ifndef RPY_RDB_REPLAY
/* ------------------------------------------------------------ */


/* recording version of the macros */
#define RPY_REVDB_EMIT(normal_code, decl_e, variable)                   \
        normal_code                                                     \
        do {                                                            \
            decl_e = variable;                                          \
            memcpy(rpy_revdb.buf_p, &_e, sizeof(_e));                   \
            if ((rpy_revdb.buf_p += sizeof(_e)) > rpy_revdb.buf_limit)  \
                rpy_reverse_db_flush();                                 \
        } while (0)
#define RPY_REVDB_EMIT_VOID(normal_code)                                \
        normal_code

RPY_EXTERN void rpy_reverse_db_flush(void);


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


/* replaying version of the macros */
#define RPY_REVDB_EMIT(normal_code, decl_e, variable)           \
        do {                                                    \
            decl_e;                                             \
            char *_src = rpy_revdb.buf_p;                       \
            char *_end1 = _src + sizeof(_e);                    \
            if (_end1 > rpy_revdb.buf_limit) {                  \
                _src = rpy_reverse_db_fetch(sizeof(_e));        \
                _end1 = _src + sizeof(_e);                      \
            }                                                   \
            rpy_revdb.buf_p = _end1;                            \
            memcpy(&_e, _src, sizeof(_e));                      \
            variable = _e;                                      \
        } while (0)
#define RPY_REVDB_EMIT_VOID(normal_code)                        \
        /* nothing */

RPY_EXTERN char *rpy_reverse_db_fetch(int expected_size);


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */
