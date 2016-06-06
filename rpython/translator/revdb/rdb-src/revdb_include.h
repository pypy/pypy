#include <string.h>

RPY_EXTERN void rpy_reverse_db_setup(int argc, char *argv[]);
RPY_EXTERN void rpy_reverse_db_flush(void);


typedef struct { char *buf_p, *buf_limit; } rpy_revdb_t;
RPY_EXTERN rpy_revdb_t rpy_revdb;

#define rpy_reverse_db_EMIT(decl_e)   do {                              \
        decl_e;                                                         \
        memcpy(rpy_revdb.buf_p, &_e, sizeof(_e));                       \
        if ((rpy_revdb.buf_p += sizeof(_e)) > rpy_revdb.buf_limit)      \
            rpy_reverse_db_flush();                                     \
} while (0)
