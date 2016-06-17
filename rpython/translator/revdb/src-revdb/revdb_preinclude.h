#include <stdint.h>

typedef struct rpy_revdb_command_s {
    int cmd;      /* neg for standard commands, pos for interp-specific */
    size_t extra_size;
    int64_t arg1;
    int64_t arg2;
    int64_t arg3;
} rpy_revdb_command_t;
