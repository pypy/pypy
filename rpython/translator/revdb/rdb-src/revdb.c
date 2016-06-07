#include "common_header.h"
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include "rdb-src/revdb_include.h"

#define RDB_SIGNATURE   0x0A424452    /* "RDB\n" */
#define RDB_VERSION     0x00FF0001


rpy_revdb_t rpy_revdb;
static char rpy_rev_buffer[16384];
static int rpy_rev_fileno = -1;

#ifndef rpy_rdb_replay
bool_t rpy_rdb_replay;
#endif


static void setup_record_mode(int argc, char *argv[]);
static void setup_replay_mode(int *argc_p, char **argv_p[]);
static void check_at_end(int exitcode, int *exitcode_p);

RPY_EXTERN
void rpy_reverse_db_setup(int *argc_p, char **argv_p[])
{
    /* init-time setup */

    int replay_asked = (*argc_p >= 2 && !strcmp((*argv_p)[1], "--replay"));

#ifdef rpy_rdb_replay
    if (replay_asked != rpy_rdb_replay) {
        fprintf(stderr, "This executable was only compiled for %s mode.",
                rpy_rdb_replay ? "replay" : "record");
        exit(1);
    }
#else
    rpy_rdb_replay = replay_asked;
#endif

    if (rpy_rdb_replay)
        setup_replay_mode(argc_p, argv_p);
    else
        setup_record_mode(*argc_p, *argv_p);
}

RPY_EXTERN
void rpy_reverse_db_teardown(int *exitcode_p)
{
    int exitcode;
    RPY_REVDB_EMIT(exitcode = *exitcode_p; , int _e, exitcode);

    if (!rpy_rdb_replay)
        rpy_reverse_db_flush();
    else
        check_at_end(exitcode, exitcode_p);
}


/* ------------------------------------------------------------ */
/* Recording mode                                               */
/* ------------------------------------------------------------ */


static void setup_record_mode(int argc, char *argv[])
{
    char *filename = getenv("PYPYREVDB");
    Signed x;

    assert(!rpy_rdb_replay);
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

    RPY_REVDB_EMIT(x = RDB_SIGNATURE; , Signed _e, x);
    RPY_REVDB_EMIT(x = RDB_VERSION;   , Signed _e, x);
    RPY_REVDB_EMIT(x = 0;             , Signed _e, x);
    RPY_REVDB_EMIT(x = 0;             , Signed _e, x);
    RPY_REVDB_EMIT(x = argc;          , Signed _e, x);
    RPY_REVDB_EMIT(x = (Signed)argv;  , Signed _e, x);
}

RPY_EXTERN
void rpy_reverse_db_flush(void)
{
    /* write the current buffer content to the OS */

    ssize_t wsize, size = rpy_revdb.buf_p - rpy_rev_buffer;
    char *p;
    rpy_revdb.buf_p = rpy_rev_buffer;
    if (size == 0 || rpy_rev_fileno < 0)
        return;

    p = rpy_rev_buffer;
 retry:
    wsize = write(rpy_rev_fileno, p, size);
    if (wsize >= size)
        return;
    if (wsize <= 0) {
        if (wsize == 0)
            fprintf(stderr, "Writing to PYPYREVDB file: "
                            "unexpected non-blocking mode\n");
        else
            fprintf(stderr, "Fatal error: writing to PYPYREVDB file: %m\n");
        abort();
    }
    p += wsize;
    size -= wsize;
    goto retry;
}


/* ------------------------------------------------------------ */
/* Replaying mode                                               */
/* ------------------------------------------------------------ */


static void setup_replay_mode(int *argc_p, char **argv_p[])
{
    Signed x;
    char *filename = (*argc_p) <= 2 ? "-" : (*argv_p)[2];

    if (!strcmp(filename, "-")) {
        rpy_rev_fileno = 0;   /* stdin */
    }
    else {
        rpy_rev_fileno = open(filename, O_RDONLY | O_NOCTTY);
        if (rpy_rev_fileno < 0) {
            fprintf(stderr, "Can't open file '%s': %m\n", filename);
            exit(1);
        }
    }
    assert(rpy_rdb_replay);
    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer;

    RPY_REVDB_EMIT(abort();, Signed _e, x);
    if (x != RDB_SIGNATURE) {
        fprintf(stderr, "stdin is not a RevDB file (or wrong platform)\n");
        exit(1);
    }
    RPY_REVDB_EMIT(abort();, Signed _e, x);
    if (x != RDB_VERSION) {
        fprintf(stderr, "RevDB file version mismatch (got %lx, expected %lx)\n",
                (long)x, (long)RDB_VERSION);
        exit(1);
    }
    RPY_REVDB_EMIT(abort();, Signed _e, x);   /* ignored */
    RPY_REVDB_EMIT(abort();, Signed _e, x);   /* ignored */

    RPY_REVDB_EMIT(abort();, Signed _e, x);
    if (x <= 0) {
        fprintf(stderr, "RevDB file is bogus\n");
        exit(1);
    }
    *argc_p = x;

    RPY_REVDB_EMIT(abort();, Signed _e, x);
    *argv_p = (char **)x;
}

static void check_at_end(int exitcode, int *exitcode_p)
{
    char dummy[1];
    if (*exitcode_p != exitcode) {
        fprintf(stderr, "Bogus exit code\n");
        exit(1);
    }
    if (rpy_revdb.buf_p != rpy_revdb.buf_limit ||
            read(rpy_rev_fileno, dummy, 1) > 0) {
        fprintf(stderr, "RevDB file error: corrupted file (too much data?)\n");
        exit(1);
    }
    printf("Replaying finished.\n");
    rpy_reverse_db_stop_point(0);
    *exitcode_p = 0;
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

RPY_EXTERN
void rpy_reverse_db_stop_point(long stop_point)
{
    printf("stop_point %ld\n", stop_point);
}


/* ------------------------------------------------------------ */
