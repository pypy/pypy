#include "common_header.h"
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include "rdb-src/rdb_include.h"

#define RDB_SIGNATURE   0x0A424452    /* "RDB\n" */
#define RDB_VERSION     0x00FF0001


Signed *rpy_rev_buf_p, *rpy_rev_buf_end;
static Signed rpy_rev_buffer[2048];
static int rpy_rev_fileno = -1;


RPY_EXTERN
void rpy_reverse_db_setup(int argc, char *argv[])
{
    /* init-time setup */

    char *filename = getenv("PYPYRDB");

    rpy_rev_buf_p = rpy_rev_buffer;
    rpy_rev_buf_end = rpy_rev_buffer +
        sizeof(rpy_rev_buffer) / sizeof(rpy_rev_buffer[0]);

    if (filename && *filename) {
        putenv("PYPYRDB=");
        rpy_rev_fileno = open(filename, O_WRONLY | O_CLOEXEC |
                              O_CREAT | O_NOCTTY | O_TRUNC, 0600);
        if (rpy_rev_fileno < 0) {
            fprintf(stderr, "Fatal error: can't create PYPYRDB file '%s'\n",
                    filename);
            abort();
        }
        atexit(rpy_reverse_db_flush);
    }

    rpy_reverse_db_emit(RDB_SIGNATURE);
    rpy_reverse_db_emit(RDB_VERSION);
    rpy_reverse_db_emit(0);
    rpy_reverse_db_emit(0);
    rpy_reverse_db_emit(argc);
    rpy_reverse_db_emit((Signed)argv);
}

RPY_EXTERN
void rpy_reverse_db_flush(void)
{
    /* write the current buffer content to the OS */

    ssize_t size = (rpy_rev_buf_p - rpy_rev_buffer) * sizeof(rpy_rev_buffer[0]);
    rpy_rev_buf_p = rpy_rev_buffer;
    if (size > 0 && rpy_rev_fileno >= 0) {
        if (write(rpy_rev_fileno, rpy_rev_buffer, size) != size) {
            fprintf(stderr, "Fatal error: writing to PYPYRDB file: %m\n");
            abort();
        }
    }
}
