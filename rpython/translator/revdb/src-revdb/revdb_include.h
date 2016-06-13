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

#if 0    /* enable to print locations to stderr of all the EMITs */
#  define _RPY_REVDB_PRINT(args)  fprintf args
#else
#  define _RPY_REVDB_PRINT(args)  /* nothing */
#endif


#define RPY_REVDB_EMIT(normal_code, decl_e, variable)                   \
    if (!RPY_RDB_REPLAY) {                                              \
        normal_code                                                     \
        {                                                               \
            decl_e = variable;                                          \
            _RPY_REVDB_PRINT((stderr, "%s:%d: write %0*llx\n",          \
                              __FILE__, __LINE__,                       \
                              2 * sizeof(_e), (unsigned long long)_e)); \
            memcpy(rpy_revdb.buf_p, &_e, sizeof(_e));                   \
            if ((rpy_revdb.buf_p += sizeof(_e)) > rpy_revdb.buf_limit)  \
                rpy_reverse_db_flush();                                 \
        }                                                               \
    } else {                                                            \
            decl_e;                                                     \
            char *_src = rpy_revdb.buf_p;                               \
            char *_end1 = _src + sizeof(_e);                            \
            if (_end1 > rpy_revdb.buf_limit) {                          \
                _src = rpy_reverse_db_fetch(sizeof(_e),                 \
                                            __FILE__, __LINE__);        \
                _end1 = _src + sizeof(_e);                              \
            }                                                           \
            rpy_revdb.buf_p = _end1;                                    \
            memcpy(&_e, _src, sizeof(_e));                              \
            _RPY_REVDB_PRINT((stderr, "%s:%d: read %0*llx\n",           \
                              __FILE__, __LINE__,                       \
                              2 * sizeof(_e), (unsigned long long)_e)); \
            variable = _e;                                              \
    }

#define RPY_REVDB_EMIT_VOID(normal_code)                                \
    if (!RPY_RDB_REPLAY) { normal_code } else { }

#define OP_REVDB_STOP_POINT(r)                                          \
    if (++rpy_revdb.stop_point_seen == rpy_revdb.stop_point_break)      \
        rpy_reverse_db_stop_point()

#define OP_REVDB_SEND_OUTPUT(ll_string, r)                              \
    rpy_reverse_db_send_output(ll_string)

#define OP_REVDB_CHANGE_TIME(mode, time, callback, ll_string, r)   \
    rpy_reverse_db_change_time(mode, time, callback, ll_string)

#define OP_REVDB_GET_VALUE(value_id, r)                                 \
    r = rpy_reverse_db_get_value(value_id)

#define OP_REVDB_IDENTITYHASH(obj, r)                                   \
    r = rpy_reverse_db_identityhash((struct pypy_header0 *)(obj))

RPY_EXTERN void rpy_reverse_db_flush(void);
RPY_EXTERN char *rpy_reverse_db_fetch(int expected_size,
                                      const char *file, int line);
RPY_EXTERN void rpy_reverse_db_stop_point(void);
RPY_EXTERN void rpy_reverse_db_send_output(RPyString *output);
RPY_EXTERN Signed rpy_reverse_db_identityhash(struct pypy_header0 *obj);
RPY_EXTERN void rpy_reverse_db_change_time(char mode, long long time,
                                           void callback(RPyString *),
                                           RPyString *arg);
RPY_EXTERN long long rpy_reverse_db_get_value(char value_id);


/* ------------------------------------------------------------ */
