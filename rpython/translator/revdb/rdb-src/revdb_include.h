#include <string.h>
#include <stdint.h>

/* By default, this makes an executable which supports both recording
   and replaying.  It should help avoid troubles like using for
   replaying an executable that is slightly different than the one
   used for recording.  In theory you can compile with
   -DRPY_RDB_REPLAY=0 or -DRPY_RDB_REPLAY=1 to get only one version
   compiled for it, which should be slightly faster (not tested so
   far).
*/

typedef struct {
#ifndef RPY_RDB_REPLAY
    bool_t replay;
#define RPY_RDB_REPLAY   rpy_revdb.replay
#define RPY_RDB_DYNAMIC_REPLAY
#endif
    char *buf_p, *buf_limit;
    uint64_t stop_point_seen, stop_point_break;
} rpy_revdb_t;

RPY_EXTERN rpy_revdb_t rpy_revdb;


/* ------------------------------------------------------------ */

RPY_EXTERN void rpy_reverse_db_setup(int *argc_p, char **argv_p[]);
RPY_EXTERN void rpy_reverse_db_teardown(void);


#define RPY_REVDB_EMIT(normal_code, decl_e, variable)                   \
    if (!RPY_RDB_REPLAY) {                                              \
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
    if (!RPY_RDB_REPLAY) { normal_code } else { }

#define OP_REVDB_STOP_POINT(stop_point, r)                              \
    if (++rpy_revdb.stop_point_seen == rpy_revdb.stop_point_break)      \
        rpy_reverse_db_break(stop_point)

#define OP_REVDB_SEND_OUTPUT(ll_string, r)                              \
    rpy_reverse_db_send_output(ll_string)

RPY_EXTERN void rpy_reverse_db_flush(void);
RPY_EXTERN char *rpy_reverse_db_fetch(int expected_size);
RPY_EXTERN void rpy_reverse_db_break(long stop_point);
RPY_EXTERN void rpy_reverse_db_send_output(RPyString *output);


/* ------------------------------------------------------------ */
