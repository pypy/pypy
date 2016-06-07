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


static void setup_record_mode(int argc, char *argv[]);
static void setup_replay_mode(int *argc_p, char **argv_p[]);
static void check_at_end(int exitcode, int *exitcode_p, uint64_t stop_points);

RPY_EXTERN
void rpy_reverse_db_setup(int *argc_p, char **argv_p[])
{
    /* init-time setup */

    int replay_asked = (*argc_p >= 2 && !strcmp((*argv_p)[1], "--replay"));

#ifdef RPY_RDB_DYNAMIC_REPLAY
    RPY_RDB_REPLAY = replay_asked;
#else
    if (replay_asked != RPY_RDB_REPLAY) {
        fprintf(stderr, "This executable was only compiled for %s mode.",
                RPY_RDB_REPLAY ? "replay" : "record");
        exit(1);
    }
#endif

    if (RPY_RDB_REPLAY)
        setup_replay_mode(argc_p, argv_p);
    else
        setup_record_mode(*argc_p, *argv_p);
}

RPY_EXTERN
void rpy_reverse_db_teardown(int *exitcode_p)
{
    int exitcode;
    uint64_t stop_points;
    RPY_REVDB_EMIT(exitcode = *exitcode_p; , int _e, exitcode);
    RPY_REVDB_EMIT(stop_points = rpy_revdb.stop_point_seen; ,
                   uint64_t _e, stop_points);

    if (!RPY_RDB_REPLAY)
        rpy_reverse_db_flush();
    else
        check_at_end(exitcode, exitcode_p, stop_points);
}


/* ------------------------------------------------------------ */
/* Recording mode                                               */
/* ------------------------------------------------------------ */


static void setup_record_mode(int argc, char *argv[])
{
    char *filename = getenv("PYPYREVDB");
    Signed x;

    assert(RPY_RDB_REPLAY == 0);
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
    int argc = *argc_p;
    char **argv = *argv_p;
    char *filename;

    if (argc != 3) {
        fprintf(stderr, "syntax: %s --replay <RevDB-file>\n", argv[0]);
        exit(2);
    }
    filename = argv[2];

    rpy_rev_fileno = open(filename, O_RDONLY | O_NOCTTY);
    if (rpy_rev_fileno < 0) {
        fprintf(stderr, "Can't open file '%s': %m\n", filename);
        exit(1);
    }

    assert(RPY_RDB_REPLAY == 1);
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

    rpy_revdb.stop_point_break = 1;
}

static void check_at_end(int exitcode, int *exitcode_p, uint64_t stop_points)
{
    char dummy[1];
    if (stop_points != rpy_revdb.stop_point_seen) {
        fprintf(stderr, "Bad number of stop points\n");
        exit(1);
    }
    if (rpy_revdb.buf_p != rpy_revdb.buf_limit ||
            read(rpy_rev_fileno, dummy, 1) > 0) {
        fprintf(stderr, "RevDB file error: corrupted file (too much data?)\n");
        exit(1);
    }
    if (*exitcode_p != exitcode) {
        fprintf(stderr, "Bogus exit code\n");
        exit(1);
    }
    printf("Replaying finished (exit code %d)\n", exitcode);
    rpy_reverse_db_break(0);
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
void rpy_reverse_db_break(long stop_point)
{
    printf("break #%ld after %lld stop points\n", stop_point,
           (long long)rpy_revdb.stop_point_seen);
}


/* ------------------------------------------------------------ */
