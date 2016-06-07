#include "common_header.h"
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>

#include "rdb-src/revdb_include.h"

#define RDB_SIGNATURE   0x0A424452    /* "RDB\n" */
#define RDB_VERSION     0x00FF0001


typedef struct {
    Signed signature, version;
    Signed reserved1, reserved2;
    int argc;
    char **argv;
} rdb_header_t;


rpy_revdb_t rpy_revdb;
static char rpy_rev_buffer[16384];
static int rpy_rev_fileno = -1;


static void setup_record_mode(int argc, char *argv[]);
static void setup_replay_mode(int *argc_p, char **argv_p[]);
static void check_at_end(uint64_t stop_points);

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
void rpy_reverse_db_teardown(void)
{
    uint64_t stop_points;
    RPY_REVDB_EMIT(stop_points = rpy_revdb.stop_point_seen; ,
                   uint64_t _e, stop_points);

    if (!RPY_RDB_REPLAY)
        rpy_reverse_db_flush();
    else
        check_at_end(stop_points);
}


/* ------------------------------------------------------------ */
/* Recording mode                                               */
/* ------------------------------------------------------------ */


static void write_all(int fd, const char *buf, ssize_t count)
{
    while (count > 0) {
        ssize_t wsize = write(fd, buf, count);
        if (wsize <= 0) {
            if (wsize == 0)
                fprintf(stderr, "Writing to PYPYREVDB file: "
                                "unexpected non-blocking mode\n");
            else
                fprintf(stderr, "Fatal error: writing to PYPYREVDB file: %m\n");
            abort();
        }
        buf += wsize;
        count -= wsize;
    }
}

static void setup_record_mode(int argc, char *argv[])
{
    char *filename = getenv("PYPYREVDB");
    rdb_header_t h;

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

    memset(&h, 0, sizeof(h));
    h.signature = RDB_SIGNATURE;
    h.version = RDB_VERSION;
    h.argc = argc;
    h.argv = argv;
    write_all(rpy_rev_fileno, (const char *)&h, sizeof(h));
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

    write_all(rpy_rev_fileno, rpy_rev_buffer, size);
}


/* ------------------------------------------------------------ */
/* Replaying mode                                               */
/* ------------------------------------------------------------ */


/* How it works: the main process reads the RevDB file and
   reconstructs the GC objects, in effect replaying their content, for
   the complete duration of the original program.  During this
   replaying, it forks a fixed number of frozen processes which sit
   around, each keeping the version of the GC objects contents at some
   known version.  We have one pipe for every frozen process, which
   the frozen process is blocked reading.

    [main process]
        [frozen process 1]
        [frozen process 2]
            [debugging process]
        [frozen process 3]
        [frozen process 4]
        ...
        [frozen process n]

   When all frozen processes are made, the main process enters
   interactive mode.  In interactive mode, the main process reads from
   stdin a version number to go to.  It picks the correct frozen
   process (the closest one that is before in time); let's say it is
   process #p.  It sends the version number to it by writing to pipe
   #p.  The corresponding frozen process wakes up, and forks again
   into a debugging process.  The main and the frozen process then
   block.

   The debugging process first goes forward in time until it reaches
   the right version number.  Then it interacts with the user (or a
   pdb-like program outside) on stdin/stdout.  This goes on until an
   "exit" command is received and the debugging process dies.  At that
   point its parent (the frozen process) continues and signals its own
   parent (the main process) by writing to a separate signalling pipe.
   The main process then wakes up again, and the loop closes: it reads
   on stdin the next version number that we're interested in, and asks
   the right frozen process to make a debugging process again.

   Note how we have, over time, several processes that read and
   process stdin; it should work because they are strictly doing that
   in sequence, never concurrently.  To avoid the case where stdin is
   buffered inside one process but a different process should read it,
   we write markers to stdout when such switches occur.  The outside
   controlling program must wait until it sees these markers before
   writing more data.
*/

#define FROZEN_PROCESSES   30
#define GOLDEN_RATIO       0.618034

static uint64_t total_stop_points;


static ssize_t read_at_least(int fd, char *buf,
                             ssize_t count_min, ssize_t count_max)
{
    ssize_t result = 0;
    assert(count_min <= count_max);
    while (result < count_min) {
        ssize_t rsize = read(fd, buf + result, count_max - result);
        if (rsize <= 0) {
            if (rsize == 0)
                fprintf(stderr, "RevDB file appears truncated\n");
            else
                fprintf(stderr, "RevDB file read error: %m\n");
            exit(1);
        }
        result += rsize;
    }
    return result;
}

static void read_all(int fd, char *buf, ssize_t count)
{
    (void)read_at_least(fd, buf, count, count);
}

static void setup_replay_mode(int *argc_p, char **argv_p[])
{
    int argc = *argc_p;
    char **argv = *argv_p;
    char *filename;
    rdb_header_t h;

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

    read_all(rpy_rev_fileno, (char *)&h, sizeof(h));

    if (h.signature != RDB_SIGNATURE) {
        fprintf(stderr, "'%s' is not a RevDB file (or wrong platform)\n",
                filename);
        exit(1);
    }
    if (h.version != RDB_VERSION) {
        fprintf(stderr, "RevDB file version mismatch (got %lx, expected %lx)\n",
                (long)h.version, (long)RDB_VERSION);
        exit(1);
    }
    *argc_p = h.argc;
    *argv_p = h.argv;

    if (lseek(rpy_rev_fileno, -sizeof(uint64_t), SEEK_END) < 0 ||
            read(rpy_rev_fileno, &total_stop_points,
                 sizeof(uint64_t)) != sizeof(uint64_t) ||
            lseek(rpy_rev_fileno, sizeof(h), SEEK_SET) != sizeof(h)) {
        fprintf(stderr, "%s: %m\n", filename);
        exit(1);
    }

    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer;
    rpy_revdb.stop_point_break = 1;
}

RPY_EXTERN
char *rpy_reverse_db_fetch(int expected_size)
{
    ssize_t rsize, keep = rpy_revdb.buf_limit - rpy_revdb.buf_p;
    assert(keep >= 0);
    memmove(rpy_rev_buffer, rpy_revdb.buf_p, keep);
    rsize = read_at_least(rpy_rev_fileno,
                          rpy_rev_buffer + keep,
                          expected_size - keep,
                          sizeof(rpy_rev_buffer) - keep);
    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer + keep + rsize;
    return rpy_rev_buffer;
}

static void check_at_end(uint64_t stop_points)
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
    if (stop_points != total_stop_points) {
        fprintf(stderr, "RevDB file modified while reading?\n");
        exit(1);
    }
    printf("Replaying finished, %lld stop points\n", (long long)stop_points);
    exit(0);
}

RPY_EXTERN
void rpy_reverse_db_break(long stop_point)
{
    printf("break #%ld after %lld stop points\n", stop_point,
           (long long)rpy_revdb.stop_point_seen);
}


/* ------------------------------------------------------------ */
