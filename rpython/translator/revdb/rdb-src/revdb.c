#include "common_header.h"
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include "rdb-src/revdb_include.h"

#define RDB_SIGNATURE   0x0A424452    /* "RDB\n" */
#define RDB_VERSION     0x00FF0001


rpy_revdb_t rpy_revdb;
static char rpy_rev_buffer[16384];
static int rpy_rev_fileno = -1;


/* ------------------------------------------------------------ */
#ifndef RPY_RDB_REPLAY
/* ------------------------------------------------------------ */


RPY_EXTERN
void rpy_reverse_db_setup(int *argc_p, char **argv_p[])
{
    /* init-time setup */

    char *filename = getenv("PYPYREVDB");
    Signed x;

    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer + sizeof(rpy_rev_buffer) - 32;

    if (filename && *filename) {
        putenv("PYPYREVDB=");
        rpy_rev_fileno = open(filename, O_WRONLY | O_CLOEXEC |
                              O_CREAT | O_NOCTTY | O_TRUNC, 0600);
        if (rpy_rev_fileno < 0) {
            fprintf(stderr, "Fatal error: can't create PYPYREVDB file '%s'\n",
                    filename);
            abort();
        }
        atexit(rpy_reverse_db_flush);
    }

    RPY_REVDB_EMIT(x = RDB_SIGNATURE;,   Signed _e, x);
    RPY_REVDB_EMIT(x = RDB_VERSION;,     Signed _e, x);
    RPY_REVDB_EMIT(x = 0;,               Signed _e, x);
    RPY_REVDB_EMIT(x = 0;,               Signed _e, x);
    RPY_REVDB_EMIT(x = *argc_p;,         Signed _e, x);
    RPY_REVDB_EMIT(x = (Signed)*argv_p;, Signed _e, x);
}

RPY_EXTERN
void rpy_reverse_db_teardown(void)
{
    rpy_reverse_db_flush();
}

RPY_EXTERN
void rpy_reverse_db_flush(void)
{
    /* write the current buffer content to the OS */

    ssize_t size = rpy_revdb.buf_p - rpy_rev_buffer;
    rpy_revdb.buf_p = rpy_rev_buffer;
    if (size > 0 && rpy_rev_fileno >= 0) {
        if (write(rpy_rev_fileno, rpy_rev_buffer, size) != size) {
            fprintf(stderr, "Fatal error: writing to PYPYREVDB file: %m\n");
            abort();
        }
    }
}


/* ------------------------------------------------------------ */
#else
/* ------------------------------------------------------------ */


RPY_EXTERN
void rpy_reverse_db_setup(int *argc_p, char **argv_p[])
{
    Signed x;

    if (*argc_p <= 1) {
        rpy_rev_fileno = 0;   /* stdin */
    }
    else {
        char *filename = (*argv_p)[1];
        rpy_rev_fileno = open(filename, O_RDONLY | O_NOCTTY);
        if (rpy_rev_fileno < 0) {
            fprintf(stderr, "Can't open file '%s': %m\n", filename);
            exit(1);
        }
    }
    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer;

    RPY_REVDB_EMIT(*, Signed _e, x);
    if (x != RDB_SIGNATURE) {
        fprintf(stderr, "stdin is not a RevDB file (or wrong platform)\n");
        exit(1);
    }
    RPY_REVDB_EMIT(*, Signed _e, x);
    if (x != RDB_VERSION) {
        fprintf(stderr, "RevDB file version mismatch (got %lx, expected %lx)\n",
                (long)x, (long)RDB_VERSION);
        exit(1);
    }
    RPY_REVDB_EMIT(*, Signed _e, x);   /* ignored */
    RPY_REVDB_EMIT(*, Signed _e, x);   /* ignored */

    RPY_REVDB_EMIT(*, Signed _e, x);
    if (x <= 0) {
        fprintf(stderr, "RevDB file is bogus\n");
        exit(1);
    }
    *argc_p = x;

    RPY_REVDB_EMIT(*, Signed _e, x);
    *argv_p = (char **)x;
}

RPY_EXTERN
void rpy_reverse_db_teardown(void)
{
    char dummy[1];
    if (rpy_revdb.buf_p != rpy_revdb.buf_limit ||
            read(rpy_rev_fileno, dummy, 1) > 0) {
        fprintf(stderr, "RevDB file error: corrupted file (too much data?)\n");
        exit(1);
    }
}

RPY_EXTERN
char *rpy_reverse_db_fetch(int expected_size)
{
    ssize_t rsize, keep = rpy_revdb.buf_limit - rpy_revdb.buf_p;
    assert(keep >= 0);
    memmove(rpy_rev_buffer, rpy_revdb.buf_p, keep);

 retry:
    rsize = read(rpy_rev_fileno, rpy_rev_buffer + keep,
                 sizeof(rpy_rev_buffer) - keep);
    if (rsize <= 0) {
        if (rsize == 0)
            fprintf(stderr, "RevDB file appears truncated\n");
        else
            fprintf(stderr, "RevDB file read error: %m\n");
        exit(1);
    }
    keep += rsize;

    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer + keep;

    if (rpy_revdb.buf_limit - rpy_revdb.buf_p < expected_size)
        goto retry;

    return rpy_rev_buffer;
}


/* ------------------------------------------------------------ */
#endif
/* ------------------------------------------------------------ */
