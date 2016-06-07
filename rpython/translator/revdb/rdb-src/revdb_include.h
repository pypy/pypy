#include <string.h>

RPY_EXTERN void rpy_reverse_db_setup(int *argc_p, char **argv_p[]);
RPY_EXTERN void rpy_reverse_db_teardown(void);

typedef struct { char *buf_p, *buf_limit; } rpy_revdb_t;
RPY_EXTERN rpy_revdb_t rpy_revdb;


/* By default, this makes an executable which supports both recording
   and replaying.  It should help avoid troubles like using for
   replaying an executable that is slightly different than the one
   used for recording.  In theory you can compile with 
   -Drpy_rdb_replay=0 or -Drpy_rdb_replay=1 to get only one version
   compiled it (not tested so far).
*/
#ifndef rpy_rdb_replay
RPY_EXTERN bool_t rpy_rdb_replay;
#endif


/* ------------------------------------------------------------ */


#define RPY_REVDB_EMIT(normal_code, decl_e, variable)                   \
    if (!rpy_rdb_replay) {                                              \
        normal_code                                                     \
        {                                                               \
            decl_e = variable;                                          \
            memcpy(rpy_revdb.buf_p, &_e, sizeof(_e));                   \
            if ((rpy_revdb.buf_p += sizeof(_e)) > rpy_revdb.buf_limit)  \
                rpy_reverse_db_flush();                                 \
        }                                                               \
    } else {                                                            \
            decl_e;                                                     \
            char *_src = rpy_revdb.buf_p;                               \
            char *_end1 = _src + sizeof(_e);                            \
            if (_end1 > rpy_revdb.buf_limit) {                          \
                _src = rpy_reverse_db_fetch(sizeof(_e));                \
                _end1 = _src + sizeof(_e);                              \
            }                                                           \
            rpy_revdb.buf_p = _end1;                                    \
            memcpy(&_e, _src, sizeof(_e));                              \
            variable = _e;                                              \
    }

#define RPY_REVDB_EMIT_VOID(normal_code)                                \
    if (!rpy_rdb_replay) { normal_code } else { }

RPY_EXTERN void rpy_reverse_db_flush(void);
RPY_EXTERN char *rpy_reverse_db_fetch(int expected_size);


/* ------------------------------------------------------------ */
