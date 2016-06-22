#include "common_header.h"
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <ctype.h>
#include <setjmp.h>
#include <signal.h>

#include "structdef.h"
#include "forwarddecl.h"
#include "preimpl.h"
#include "src/rtyper.h"
#include "src-revdb/revdb_include.h"

#define RDB_SIGNATURE   "RevDB:"
#define RDB_VERSION     0x00FF0001


typedef struct {
    Signed version;
    Signed reserved1, reserved2;
    int argc;
    char **argv;
} rdb_header_t;


rpy_revdb_t rpy_revdb;
static char rpy_rev_buffer[16384];
static int rpy_rev_fileno = -1;
static unsigned char flag_io_disabled;


static void setup_record_mode(int argc, char *argv[]);
static void setup_replay_mode(int *argc_p, char **argv_p[]);
static void check_at_end(uint64_t stop_points);

RPY_EXTERN
void rpy_reverse_db_setup(int *argc_p, char **argv_p[])
{
    /* init-time setup */

    int replay_asked = (*argc_p >= 2 && !strcmp((*argv_p)[1],"--revdb-replay"));

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


static void write_all(const void *buf, ssize_t count)
{
    while (count > 0) {
        ssize_t wsize = write(rpy_rev_fileno, buf, count);
        if (wsize <= 0) {
            if (wsize == 0)
                fprintf(stderr, "writing to RevDB file: "
                                "unexpected non-blocking mode\n");
            else
                fprintf(stderr, "Fatal error: writing to RevDB file: %m\n");
            abort();
        }
        buf += wsize;
        count -= wsize;
    }
}

static void setup_record_mode(int argc, char *argv[])
{
    char *filename = getenv("PYPYRDB");
    rdb_header_t h;
    int i;

    assert(RPY_RDB_REPLAY == 0);
    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer + sizeof(rpy_rev_buffer) - 32;
    rpy_revdb.unique_id_seen = 1;

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

        write_all(RDB_SIGNATURE, strlen(RDB_SIGNATURE));
        for (i = 0; i < argc; i++) {
            write_all("\t", 1);
            write_all(argv[i], strlen(argv[i]));
        }
        write_all("\n\0", 2);

        memset(&h, 0, sizeof(h));
        h.version = RDB_VERSION;
        h.argc = argc;
        h.argv = argv;
        write_all((const char *)&h, sizeof(h));
    }
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

    write_all(rpy_rev_buffer, size);
}

RPY_EXTERN
Signed rpy_reverse_db_identityhash(struct pypy_header0 *obj)
{
    /* Boehm only */
    if (obj->h_hash == 0) {
        Signed h;
        if (flag_io_disabled) {
            /* This is when running debug commands.  Don't cache the
               hash on the object at all. */
            return ~((Signed)obj);
        }
        /* When recording, we get the hash the normal way from the
           pointer casted to an int, and record that.  When replaying,
           we read it from the record.  In both cases, we cache the
           hash in the object, so that we record/replay only once per
           object. */
        RPY_REVDB_EMIT(h = ~((Signed)obj);, Signed _e, h);
        assert(h != 0);
        obj->h_hash = h;
    }
    return obj->h_hash;
}


/* ------------------------------------------------------------ */
/* Replaying mode                                               */
/* ------------------------------------------------------------ */


/* How it works: we run the same executable with different flags to
   run it in "replay" mode.  In this mode, it reads commands from
   stdin (in binary format) and writes the results to stdout.
   Notably, there is a command to ask it to fork, passing a new pair
   of pipes to the forked copy as its new stdin/stdout.  This is how
   we implement the illusion of going backward: we throw away the
   current fork, start from an earlier fork, make a new fork again,
   and go forward by the correct number of steps.  This is all
   controlled by a pure Python wrapper that is roughly generic
   (i.e. able to act as a debugger for any language).
*/

#include "src-revdb/fd_recv.c"

#define INIT_VERSION_NUMBER   0xd80100

#define CMD_FORK      (-1)
#define CMD_QUIT      (-2)
#define CMD_FORWARD   (-3)
#define CMD_FUTUREIDS (-4)

#define ANSWER_INIT       (-20)
#define ANSWER_READY      (-21)
#define ANSWER_FORKED     (-22)
#define ANSWER_AT_END     (-23)
#define ANSWER_BREAKPOINT (-24)

typedef void (*rpy_revdb_command_fn)(rpy_revdb_command_t *, RPyString *);

static int rpy_rev_sockfd;
static const char *rpy_rev_filename;
static uint64_t stopped_time;
static uint64_t stopped_uid;
static uint64_t total_stop_points;
static jmp_buf jmp_buf_cancel_execution;
static void (*pending_after_forward)(void);
static RPyString *empty_string;
static uint64_t last_recorded_breakpoint_loc;
static int last_recorded_breakpoint_num;
static char breakpoint_mode;
static uint64_t *future_ids, *future_next_id;

static void attach_gdb(void)
{
    char cmdline[80];
    sprintf(cmdline, "term -c \"gdb --pid=%d\"", getpid());
    system(cmdline);
    sleep(1);
}

static ssize_t read_at_least(void *buf, ssize_t count_min, ssize_t count_max)
{
    ssize_t result = 0;
    assert(count_min <= count_max);
    while (result < count_min) {
        ssize_t rsize = read(rpy_rev_fileno, buf + result, count_max - result);
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

static void read_all(void *buf, ssize_t count)
{
    (void)read_at_least(buf, count, count);
}

static void read_sock(void *buf, ssize_t count)
{
    while (count > 0) {
        ssize_t got = read(rpy_rev_sockfd, buf, count);
        if (got <= 0) {
            fprintf(stderr, "subprocess: cannot read from control socket\n");
            exit(1);
        }
        count -= got;
        buf += got;
    }
}

static void write_sock(const void *buf, ssize_t count)
{
    while (count > 0) {
        ssize_t wrote = write(rpy_rev_sockfd, buf, count);
        if (wrote <= 0) {
            fprintf(stderr, "subprocess: cannot write to control socket\n");
            exit(1);
        }
        count -= wrote;
        buf += wrote;
    }
}

static void write_answer(int cmd, int64_t arg1, int64_t arg2, int64_t arg3)
{
    rpy_revdb_command_t c;
    memset(&c, 0, sizeof(c));
    c.cmd = cmd;
    c.arg1 = arg1;
    c.arg2 = arg2;
    c.arg3 = arg3;
    write_sock(&c, sizeof(c));
}

static RPyString *make_rpy_string(size_t length)
{
    RPyString *s = malloc(sizeof(RPyString) + length);
    if (s == NULL) {
        fprintf(stderr, "out of memory for a string of %llu chars\n",
                (unsigned long long)length);
        exit(1);
    }
    /* xxx assumes Boehm here for now */
    memset(s, 0, sizeof(RPyString));
    RPyString_Size(s) = length;
    return s;
}

static void reopen_revdb_file(const char *filename)
{
    rpy_rev_fileno = open(filename, O_RDONLY | O_NOCTTY);
    if (rpy_rev_fileno < 0) {
        fprintf(stderr, "Can't open file '%s': %m\n", filename);
        exit(1);
    }
}

static void setup_replay_mode(int *argc_p, char **argv_p[])
{
    int argc = *argc_p;
    char **argv = *argv_p;
    rdb_header_t h;
    char input[16];
    ssize_t count;

    if (argc != 4) {
        fprintf(stderr, "syntax: %s --revdb-replay <RevDB-file> <socket_fd>\n",
                argv[0]);
        exit(2);
    }
    rpy_rev_filename = argv[2];
    reopen_revdb_file(rpy_rev_filename);
    rpy_rev_sockfd = atoi(argv[3]);

    assert(RPY_RDB_REPLAY == 1);

    read_all(input, strlen(RDB_SIGNATURE));
    if (strncmp(input, RDB_SIGNATURE, strlen(RDB_SIGNATURE)) != 0) {
        fprintf(stderr, "'%s' is not a RevDB file (or wrong platform)\n",
                rpy_rev_filename);
        exit(1);
    }
    fprintf(stderr, "%s", RDB_SIGNATURE);
    while ((read_all(input, 1), input[0] != 0))
        fputc(input[0] == '\t' ? ' ' : input[0], stderr);

    read_all(&h, sizeof(h));
    if (h.version != RDB_VERSION) {
        fprintf(stderr, "RevDB file version mismatch (got %lx, expected %lx)\n",
                (long)h.version, (long)RDB_VERSION);
        exit(1);
    }
    *argc_p = h.argc;
    *argv_p = h.argv;

    count = lseek(rpy_rev_fileno, 0, SEEK_CUR);
    if (count < 0 ||
            lseek(rpy_rev_fileno, -sizeof(uint64_t), SEEK_END) < 0 ||
            read(rpy_rev_fileno, &total_stop_points,
                 sizeof(uint64_t)) != sizeof(uint64_t) ||
            lseek(rpy_rev_fileno, count, SEEK_SET) != count) {
        fprintf(stderr, "%s: %m\n", rpy_rev_filename);
        exit(1);
    }

    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer;
    rpy_revdb.stop_point_break = 1;
    rpy_revdb.unique_id_seen = 1;

    empty_string = make_rpy_string(0);

    write_answer(ANSWER_INIT, INIT_VERSION_NUMBER, total_stop_points, 0);

    /* ignore the SIGCHLD signals so that child processes don't become
       zombies */
    signal(SIGCHLD, SIG_IGN);
}

RPY_EXTERN
char *rpy_reverse_db_fetch(int expected_size, const char *file, int line)
{
    if (!flag_io_disabled) {
        ssize_t rsize, keep = rpy_revdb.buf_limit - rpy_revdb.buf_p;
        assert(keep >= 0);
        memmove(rpy_rev_buffer, rpy_revdb.buf_p, keep);
        rsize = read_at_least(rpy_rev_buffer + keep,
                              expected_size - keep,
                              sizeof(rpy_rev_buffer) - keep);
        rpy_revdb.buf_p = rpy_rev_buffer;
        rpy_revdb.buf_limit = rpy_rev_buffer + keep + rsize;
        return rpy_rev_buffer;
    }
    else {
        /* this is called when we are in execute_rpy_command(): we are
           running some custom code now, and we can't just perform I/O
           or access raw memory---because there is no raw memory! 
        */
        fprintf(stderr, "%s:%d: Attempted to do I/O or access raw memory\n",
                file, line);
        longjmp(jmp_buf_cancel_execution, 1);
    }
}

static rpy_revdb_t disabled_state;
static void *disabled_exc[2];

static void disable_io(void)
{
    if (flag_io_disabled) {
        fprintf(stderr, "unexpected recursive disable_io()\n");
        exit(1);
    }
    disabled_state = rpy_revdb;   /* save the complete struct */
    disabled_exc[0] = pypy_g_ExcData.ed_exc_type;
    disabled_exc[1] = pypy_g_ExcData.ed_exc_value;
    pypy_g_ExcData.ed_exc_type = NULL;
    pypy_g_ExcData.ed_exc_value = NULL;
    rpy_revdb.buf_p = NULL;
    rpy_revdb.buf_limit = NULL;
    flag_io_disabled = 1;
}

static void enable_io(int restore_breaks)
{
    uint64_t v1, v2;
    if (!flag_io_disabled) {
        fprintf(stderr, "unexpected enable_io()\n");
        exit(1);
    }
    flag_io_disabled = 0;

    if (pypy_g_ExcData.ed_exc_type != NULL) {
        fprintf(stderr, "Command crashed with %.*s\n",
                (int)(pypy_g_ExcData.ed_exc_type->ov_name->rs_chars.length),
                pypy_g_ExcData.ed_exc_type->ov_name->rs_chars.items);
        exit(1);
    }
    /* restore the complete struct, with the exception of '*_break' */
    v1 = rpy_revdb.stop_point_break;
    v2 = rpy_revdb.unique_id_break;
    rpy_revdb = disabled_state;
    if (!restore_breaks) {
        rpy_revdb.stop_point_break = v1;
        rpy_revdb.unique_id_break = v2;
    }
    pypy_g_ExcData.ed_exc_type = disabled_exc[0];
    pypy_g_ExcData.ed_exc_value = disabled_exc[1];
}

static void execute_rpy_function(rpy_revdb_command_fn func,
                                 rpy_revdb_command_t *cmd,
                                 RPyString *extra)
{
    disable_io();
    if (setjmp(jmp_buf_cancel_execution) == 0)
        func(cmd, extra);
    enable_io(0);
}

static void check_at_end(uint64_t stop_points)
{
    char dummy[1];
    if (stop_points != rpy_revdb.stop_point_seen) {
        fprintf(stderr, "Bad number of stop points "
                "(seen %lld, recorded %lld)\n",
                (long long)rpy_revdb.stop_point_seen,
                (long long)stop_points);
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

    write_answer(ANSWER_AT_END, 0, 0, 0);
    exit(0);
}

static void command_fork(void)
{
    int child_sockfd;
    int child_pid;
    off_t rev_offset = lseek(rpy_rev_fileno, 0, SEEK_CUR);

    if (ancil_recv_fd(rpy_rev_sockfd, &child_sockfd) < 0) {
        fprintf(stderr, "cannot fetch child control socket: %m\n");
        exit(1);
    }
    child_pid = fork();
    if (child_pid == -1) {
        perror("fork");
        exit(1);
    }
    if (child_pid == 0) {
        /* in the child */
        if (close(rpy_rev_sockfd) < 0) {
            perror("close");
            exit(1);
        }
        rpy_rev_sockfd = child_sockfd;

        /* Close and re-open the revdb log file in the child process.
           This is the simplest way I found to give 'rpy_rev_fileno'
           its own offset, independent from the parent.  It assumes
           that the revdb log file is still the same.  So for Linux,
           we try to open "/proc/self/fd/%d" instead. */
        char fd_filename[48];
        struct stat st;
        const char *filename;
        int old_fd = rpy_rev_fileno;

        sprintf(fd_filename, "/proc/self/fd/%d", old_fd);
        if (lstat(fd_filename, &st) == 0)
            filename = fd_filename;
        else
            filename = rpy_rev_filename;
        reopen_revdb_file(filename);

        if (close(old_fd) < 0) {
            perror("close");
            exit(1);
        }
        if (lseek(rpy_rev_fileno, rev_offset, SEEK_SET) < 0) {
            perror("lseek");
            exit(1);
        }
    }
    else {
        /* in the parent */
        write_answer(ANSWER_FORKED, child_pid, 0, 0);
        close(child_sockfd);
    }
}

static void answer_recorded_breakpoint(void)
{
    if (last_recorded_breakpoint_loc != 0) {
        write_answer(ANSWER_BREAKPOINT, last_recorded_breakpoint_loc,
                     0, last_recorded_breakpoint_num);
    }
}

static void command_forward(rpy_revdb_command_t *cmd)
{
    if (cmd->arg1 < 0) {
        fprintf(stderr, "CMD_FORWARD: negative step\n");
        exit(1);
    }
    rpy_revdb.stop_point_break = stopped_time + cmd->arg1;
    breakpoint_mode = (char)cmd->arg2;
    if (breakpoint_mode == 'r') {
        last_recorded_breakpoint_loc = 0;
        pending_after_forward = &answer_recorded_breakpoint;
    }
}

static void command_future_ids(rpy_revdb_command_t *cmd, char *extra)
{
    free(future_ids);
    if (cmd->extra_size == 0) {
        future_ids = NULL;
        rpy_revdb.unique_id_break = 0;
    }
    else {
        assert(cmd->extra_size % sizeof(uint64_t) == 0);
        future_ids = malloc(cmd->extra_size + sizeof(uint64_t));
        if (future_ids == NULL) {
            fprintf(stderr, "out of memory for a buffer of %llu chars\n",
                    (unsigned long long)cmd->extra_size);
            exit(1);
        }
        memcpy(future_ids, extra, cmd->extra_size);
        future_ids[cmd->extra_size / sizeof(uint64_t)] = 0;
        rpy_revdb.unique_id_break = *future_ids;
    }
    future_next_id = future_ids;
}

static void command_default(rpy_revdb_command_t *cmd, char *extra)
{
    RPyString *s;
    int i;
    for (i = 0; rpy_revdb_commands.rp_names[i] != cmd->cmd; i++) {
        if (rpy_revdb_commands.rp_names[i] == 0) {
            fprintf(stderr, "unknown command %d\n", cmd->cmd);
            exit(1);
        }
    }

    if (cmd->extra_size == 0) {
        s = empty_string;
    }
    else {
        s = make_rpy_string(cmd->extra_size);
        memcpy(_RPyString_AsString(s), extra, cmd->extra_size);
    }
    execute_rpy_function(rpy_revdb_commands.rp_funcs[i], cmd, s);
}

static void save_state(void)
{
    stopped_time = rpy_revdb.stop_point_seen;
    stopped_uid = rpy_revdb.unique_id_seen;
    rpy_revdb.unique_id_seen = (-1ULL) << 63;
}

static void restore_state(void)
{
    rpy_revdb.stop_point_seen = stopped_time;
    rpy_revdb.unique_id_seen = stopped_uid;
    stopped_time = 0;
    stopped_uid = 0;
}

RPY_EXTERN
bool_t rpy_reverse_db_save_state(void)
{
    if (stopped_time == 0) {
        save_state();
        disable_io();
        rpy_revdb.stop_point_break = 0;
        rpy_revdb.unique_id_break = 0;
        return 1;
    }
    else
        return 0;
}

RPY_EXTERN
void rpy_reverse_db_restore_state(void)
{
    enable_io(1);
    restore_state();
}

RPY_EXTERN
void rpy_reverse_db_stop_point(void)
{
    while (rpy_revdb.stop_point_break == rpy_revdb.stop_point_seen) {
        save_state();
        breakpoint_mode = 0;

        if (pending_after_forward) {
            void (*fn)(void) = pending_after_forward;
            pending_after_forward = NULL;
            fn();
        }
        else {
            rpy_revdb_command_t cmd;
            if (((int64_t)stopped_uid) < 0)
                attach_gdb();
            write_answer(ANSWER_READY, stopped_time, stopped_uid, 0);
            read_sock(&cmd, sizeof(cmd));

            char extra[cmd.extra_size + 1];
            extra[cmd.extra_size] = 0;
            if (cmd.extra_size > 0)
                read_sock(extra, cmd.extra_size);

            switch (cmd.cmd) {

            case CMD_FORK:
                command_fork();
                break;

            case CMD_QUIT:
                exit(0);
                break;

            case CMD_FORWARD:
                command_forward(&cmd);
                break;

            case CMD_FUTUREIDS:
                command_future_ids(&cmd, extra);
                break;

            default:
                command_default(&cmd, extra);
                break;
            }
        }
        restore_state();
    }
}

RPY_EXTERN
void rpy_reverse_db_send_answer(int cmd, int64_t arg1, int64_t arg2,
                                int64_t arg3, RPyString *extra)
{
    rpy_revdb_command_t c;
    size_t extra_size = RPyString_Size(extra);
    c.cmd = cmd;
    c.extra_size = extra_size;
    if (c.extra_size != extra_size) {
        fprintf(stderr, "string too large (more than 4GB)\n");
        exit(1);
    }
    c.arg1 = arg1;
    c.arg2 = arg2;
    c.arg3 = arg3;
    write_sock(&c, sizeof(c));
    if (extra_size > 0)
        write_sock(_RPyString_AsString(extra), extra_size);
}

RPY_EXTERN
void rpy_reverse_db_breakpoint(int64_t num)
{
    if (stopped_time != 0) {
        fprintf(stderr, "revdb.breakpoint(): cannot be called from a "
                        "debug command\n");
        exit(1);
    }

    switch (breakpoint_mode) {
    case 'i':
        return;   /* ignored breakpoints */

    case 'r':     /* record the breakpoint but continue */
        last_recorded_breakpoint_loc = rpy_revdb.stop_point_seen + 1;
        last_recorded_breakpoint_num = num;
        return;

    default:      /* 'b' or '\0' for default handling of breakpoints */
        rpy_revdb.stop_point_break = rpy_revdb.stop_point_seen + 1;
        write_answer(ANSWER_BREAKPOINT, rpy_revdb.stop_point_break, 0, num);
    }
}

RPY_EXTERN
long long rpy_reverse_db_get_value(char value_id)
{
    switch (value_id) {
    case 'c':       /* current_time() */
        return stopped_time ? stopped_time : rpy_revdb.stop_point_seen;
    case 't':       /* total_time() */
        return total_stop_points;
    case 'b':       /* current_break_time() */
        return rpy_revdb.stop_point_break;
    case 'u':       /* currently_created_objects() */
        return stopped_uid ? stopped_uid : rpy_revdb.unique_id_seen;
    default:
        return -1;
    }
}

RPY_EXTERN
uint64_t rpy_reverse_db_unique_id_break(void *new_object)
{
    uint64_t uid = rpy_revdb.unique_id_seen;
    if (!new_object) {
        fprintf(stderr, "out of memory: allocation failed, cannot continue\n");
        exit(1);
    }
    if (rpy_revdb_commands.rp_alloc) {
        if (!rpy_reverse_db_save_state()) {
            fprintf(stderr, "unexpected recursive unique_id_break\n");
            exit(1);
        }
        if (setjmp(jmp_buf_cancel_execution) == 0)
            rpy_revdb_commands.rp_alloc(uid, new_object);
        rpy_reverse_db_restore_state();
    }
    rpy_revdb.unique_id_break = *future_next_id++;
    return uid;
}


/* ------------------------------------------------------------ */
