#include "common_header.h"
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <ctype.h>
#include <setjmp.h>

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
            write_all(" ", 1);
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

   The main process's job, once reloading is finished, is only to
   active debugging processes, one at a time.  To go to a specific
   target time, it activates the right frozen process by sending
   'target_time' over the corresponding pipe.  The frozen process
   forks the debugging process, and the debugging process goes forward
   until it reaches 'target_time'.

   The debugging process is then interacting with the user on
   stdin/stdout.

   A few commands like 'go <target_time>' will cause the debugging
   process to send the 'target_time' back over a signalling pipe to
   the main process, and then finish.  The main process receives that
   'target_time', and the loop closes: it activates the right frozen
   process, which will go forward and re-enter interactive mode.
*/

#define NUM_FROZEN_PROCESSES   30
#define STEP_RATIO             0.25

#define RD_SIDE   0
#define WR_SIDE   1

static int frozen_num_pipes = 0;
static int frozen_pipes[NUM_FROZEN_PROCESSES][2];
static uint64_t frozen_time[NUM_FROZEN_PROCESSES];
static int frozen_pipe_signal[2];

enum { PK_MAIN_PROCESS, PK_FROZEN_PROCESS, PK_DEBUG_PROCESS };
static unsigned char process_kind = PK_MAIN_PROCESS;
static jmp_buf jmp_buf_cancel_execution;
static uint64_t most_recent_fork;
static uint64_t total_stop_points;
static uint64_t stopped_time;
static uint64_t stopped_uid;
static uint64_t first_created_uid;

static void (*invoke_after_forward)(RPyString *);
static RPyString *invoke_argument;

struct jump_in_time_s {
    uint64_t target_time;
    char mode;
    void *callback;
    size_t arg_length;
};


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
                fprintf(stderr, "[%d] RevDB file appears truncated\n",
                        process_kind);
            else
                fprintf(stderr, "[%d] RevDB file read error: %m\n",
                        process_kind);
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

static void setup_replay_mode(int *argc_p, char **argv_p[])
{
    int argc = *argc_p;
    char **argv = *argv_p;
    char *filename;
    rdb_header_t h;
    char input[16];
    ssize_t count;

    if (argc != 3) {
        fprintf(stderr, "syntax: %s --revdb-replay <RevDB-file>\n", argv[0]);
        exit(2);
    }
    filename = argv[2];

    rpy_rev_fileno = open(filename, O_RDONLY | O_NOCTTY);
    if (rpy_rev_fileno < 0) {
        fprintf(stderr, "Can't open file '%s': %m\n", filename);
        exit(1);
    }

    assert(RPY_RDB_REPLAY == 1);

    read_all(input, strlen(RDB_SIGNATURE));
    if (strncmp(input, RDB_SIGNATURE, strlen(RDB_SIGNATURE)) != 0) {
        fprintf(stderr, "'%s' is not a RevDB file (or wrong platform)\n",
                filename);
        exit(1);
    }
    fprintf(stderr, "%s", RDB_SIGNATURE);
    while ((read_all(input, 1), input[0] != 0))
        fputc(input[0], stderr);

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
        fprintf(stderr, "%s: %m\n", filename);
        exit(1);
    }

    rpy_revdb.buf_p = rpy_rev_buffer;
    rpy_revdb.buf_limit = rpy_rev_buffer;
    rpy_revdb.stop_point_break = 1;
    rpy_revdb.unique_id_seen = 1;

    if (pipe(frozen_pipe_signal) < 0) {
        perror("pipe");
        exit(1);
    }
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
        printf("%s:%d: Attempted to do I/O or access raw memory\n",
               file, line);
        longjmp(jmp_buf_cancel_execution, 1);
    }
}

static void disable_io(rpy_revdb_t *dinfo)
{
    *dinfo = rpy_revdb;   /* save the complete struct */
    rpy_revdb.buf_p = NULL;
    rpy_revdb.buf_limit = NULL;
    flag_io_disabled = 1;
}

static void enable_io(rpy_revdb_t *dinfo)
{
    uint64_t v1, v2;
    flag_io_disabled = 0;

    /* restore the complete struct, with the exception of '*_break' */
    v1 = rpy_revdb.stop_point_break;
    v2 = rpy_revdb.unique_id_break;
    rpy_revdb = *dinfo;
    rpy_revdb.stop_point_break = v1;
    rpy_revdb.unique_id_break = v2;
}

/* generated by RPython */
extern char *rpy_revdb_command_names[];
extern void (*rpy_revdb_command_funcs[])(RPyString *);

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

static void execute_rpy_function(void func(RPyString *), RPyString *arg);

static void execute_rpy_command(long index, char *arguments)
{
    size_t length = strlen(arguments);
    RPyString *s;

    while (length > 0 && isspace(arguments[length - 1]))
        length--;
    s = make_rpy_string(length);
    memcpy(_RPyString_AsString(s), arguments, length);

    execute_rpy_function(rpy_revdb_command_funcs[index], s);
}

static void execute_rpy_function(void func(RPyString *), RPyString *arg)
{
    rpy_revdb_t dinfo;
    void *saved_t = pypy_g_ExcData.ed_exc_type;
    void *saved_v = pypy_g_ExcData.ed_exc_value;
    pypy_g_ExcData.ed_exc_type = NULL;
    pypy_g_ExcData.ed_exc_value = NULL;
    disable_io(&dinfo);
    invoke_after_forward = NULL;
    invoke_argument = NULL;

    if (setjmp(jmp_buf_cancel_execution) == 0) {

        func(arg);

        if (pypy_g_ExcData.ed_exc_type != NULL) {
            printf("Command crashed with %.*s\n",
                   (int)(pypy_g_ExcData.ed_exc_type->ov_name->rs_chars.length),
                   pypy_g_ExcData.ed_exc_type->ov_name->rs_chars.items);
        }
    }
    enable_io(&dinfo);
    pypy_g_ExcData.ed_exc_type = saved_t;
    pypy_g_ExcData.ed_exc_value = saved_v;
}

struct action_s {
    const char *name;
    void (*act)(char *);
};

static void process_input(char *input, const char *kind, int rpycmd,
                          struct action_s actions[])
{
    char *p;
    struct action_s *a;

    while (isspace(*input))
        input++;
    p = input;
    while (*p != 0 && !isspace(*p))
        p++;
    if (*p != 0) {
        *p = 0;
        do {
            p++;
        } while (isspace(*p));
    }

    if (rpycmd) {
        long i;
        for (i = 0; rpy_revdb_command_names[i] != NULL; i++) {
            if (strcmp(rpy_revdb_command_names[i], input) == 0) {
                execute_rpy_command(i, p);
                return;
            }
        }
    }

    for (a = actions; a->name != NULL; a++) {
        if (strcmp(a->name, input) == 0) {
            a->act(p);
            return;
        }
    }
    if (strcmp(input, "help") == 0) {
        printf("select %s:\n", kind);
        if (rpycmd) {
            char **p;
            for (p = rpy_revdb_command_names; *p != NULL; p++)
                printf("\t%s\n", *p);
        }
        for (a = actions; a->name != NULL; a++) {
            if (*a->name != 0)
                printf("\t%s\n", a->name);
        }
    }
    else {
        printf("bad %s '%s', try 'help'\n", kind, input);
    }
}

static int read_pipe(int fd, void *buf, ssize_t count)
{
    while (count > 0) {
        ssize_t got = read(fd, buf, count);
        if (got <= 0)
            return -1;
        count -= got;
        buf += got;
    }
    return 0;
}

static int write_pipe(int fd, const void *buf, ssize_t count)
{
    while (count > 0) {
        ssize_t wrote = write(fd, buf, count);
        if (wrote <= 0)
            return -1;
        count -= wrote;
        buf += wrote;
    }
    return 0;
}

static int copy_pipe(int dst_fd, int src_fd, ssize_t count)
{
    char buffer[16384];
    while (count > 0) {
        ssize_t count1 = count > sizeof(buffer) ? sizeof(buffer) : count;
        if (read_pipe(src_fd, buffer, count1) < 0 ||
            write_pipe(dst_fd, buffer, count1) < 0)
            return -1;
        count -= count1;
    }
    return 0;
}

static void cmd_go(uint64_t target_time, void callback(RPyString *),
                   RPyString *arg, char mode)
{
    struct jump_in_time_s header;

    header.target_time = target_time;
    header.mode = mode;
    header.callback = callback;    /* may be NULL */
    /* ^^^ assumes the fn address is the same in the various forks */
    header.arg_length = arg == NULL ? 0 : RPyString_Size(arg);

    assert(process_kind == PK_DEBUG_PROCESS);
    write_pipe(frozen_pipe_signal[WR_SIDE], &header, sizeof(header));
    if (header.arg_length > 0) {
        write_pipe(frozen_pipe_signal[WR_SIDE], _RPyString_AsString(arg),
                   header.arg_length);
    }
    exit(0);
}

static void check_at_end(uint64_t stop_points)
{
    char dummy[1];
    struct jump_in_time_s jump_in_time;

    if (process_kind == PK_DEBUG_PROCESS) {
        printf("At end.\n");
        cmd_go(stop_points, NULL, NULL, 'g');
        abort();   /* unreachable */
    }

    if (process_kind != PK_MAIN_PROCESS) {
        fprintf(stderr, "[%d] Unexpectedly falling off the end\n",
                process_kind);
        exit(1);
    }
    if (stop_points != rpy_revdb.stop_point_seen) {
        fprintf(stderr, "Bad number of stop points "
                "(seen %llu, recorded %llu)\n",
                (unsigned long long)rpy_revdb.stop_point_seen,
                (unsigned long long)stop_points);
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
    if (frozen_num_pipes == 0) {
        fprintf(stderr, "RevDB file does not contain any stop points\n");
        exit(1);
    }

    fprintf(stderr, "\n");
    fflush(stderr);
    printf("Replaying finished\n");
    printf("stop_points=%lld\n", (long long)stop_points);

    close(frozen_pipe_signal[WR_SIDE]);
    frozen_pipe_signal[WR_SIDE] = -1;

    memset(&jump_in_time, 0, sizeof(jump_in_time));
    jump_in_time.target_time = frozen_time[frozen_num_pipes-1];

    while (jump_in_time.target_time != (uint64_t)-1) {
        int p = frozen_num_pipes - 1;
        if (jump_in_time.target_time > frozen_time[p])
            jump_in_time.target_time = frozen_time[p];
        while (frozen_time[p] > jump_in_time.target_time)
            p--;
        if (write_pipe(frozen_pipes[p][WR_SIDE],
                       &jump_in_time, sizeof(jump_in_time)) < 0 ||
            copy_pipe(frozen_pipes[p][WR_SIDE],
                      frozen_pipe_signal[RD_SIDE],
                      jump_in_time.arg_length) < 0) {
            fprintf(stderr, "broken pipe to frozen subprocess\n");
            exit(1);
        }
        /* blocking here while the p'th frozen process spawns a debug process
           and the user interacts with it; then: */
        if (read_pipe(frozen_pipe_signal[RD_SIDE], &jump_in_time,
                      sizeof(jump_in_time)) < 0) {
            fprintf(stderr, "broken signal pipe\n");
            exit(1);
        }
    }
    exit(0);
}

static void run_frozen_process(int frozen_pipe_fd)
{
    struct jump_in_time_s jump_in_time;
    pid_t child_pid;

    while (1) {
        if (read_pipe(frozen_pipe_fd, &jump_in_time, sizeof(jump_in_time)) < 0)
            exit(1);

        child_pid = fork();
        if (child_pid == -1) {
            perror("fork");
            exit(1);
        }
        if (child_pid == 0) {
            /* in the child: this is a debug process */
            process_kind = PK_DEBUG_PROCESS;
            assert(jump_in_time.target_time >= rpy_revdb.stop_point_seen);
            most_recent_fork = rpy_revdb.stop_point_seen;
            switch (jump_in_time.mode) {
            case 'b':    /* go non-exact: stay at most_recent_fork */
                rpy_revdb.stop_point_break = most_recent_fork;
                break;
            default:     /* other modes: go exact */
                rpy_revdb.stop_point_break = jump_in_time.target_time;
            }

            if (jump_in_time.callback == NULL) {
                assert(jump_in_time.arg_length == 0);
                assert(invoke_after_forward == NULL);
            }
            else {
                RPyString *s = make_rpy_string(jump_in_time.arg_length);
                if (read_pipe(frozen_pipe_fd, _RPyString_AsString(s),
                              jump_in_time.arg_length) < 0) {
                    fprintf(stderr, "broken pipe to debug subprocess\n");
                    exit(1);
                }
                invoke_after_forward = jump_in_time.callback;
                invoke_argument = s;
            }
            /* continue "running" the RPython program until we reach
               exactly the specified target_time */
            break;
        }
        else {
            /* in the parent: the frozen process, which waits for
               the debug process to finish to reclaim the pid,
               and then loops to wait for the next wake-up */
            int status;
            waitpid(child_pid, &status, 0);
            if (WIFEXITED(status) && WEXITSTATUS(status) == 0)
                ;     /* normal exit */
            else {
                fprintf(stderr, "debugging subprocess died\n");
                cmd_go((uint64_t)-1, NULL, NULL, 'q');
                abort();    /* unreachable */
            }
        }
    }
}

static void make_new_frozen_process(void)
{
    pid_t child_pid;
    int *fds;
    off_t fileno_offset;

    if (frozen_num_pipes >= NUM_FROZEN_PROCESSES) {
        fprintf(stderr, "stop_point_break overflow?\n");
        exit(1);
    }
    if (frozen_num_pipes == 0)
        first_created_uid = rpy_revdb.unique_id_seen;

    fprintf(stderr, "[%llu]",
            (unsigned long long)rpy_revdb.stop_point_seen);

    fds = frozen_pipes[frozen_num_pipes];
    if (pipe(fds) < 0) {
        perror("pipe");
        exit(1);
    }
    frozen_time[frozen_num_pipes] = rpy_revdb.stop_point_seen;
    frozen_num_pipes += 1;

    fileno_offset = lseek(rpy_rev_fileno, 0, SEEK_CUR);

    child_pid = fork();
    if (child_pid == -1) {
        perror("fork");
        exit(1);
    }
    if (child_pid == 0) {
        /* in the child: this is a frozen process */
        process_kind = PK_FROZEN_PROCESS;
        close(fds[WR_SIDE]);
        fds[WR_SIDE] = -1;
        run_frozen_process(fds[RD_SIDE]);
        /* when we reach that point, we are in the debugging process */
        lseek(rpy_rev_fileno, fileno_offset, SEEK_SET);
    }
    else {
        /* in the main process: continue reloading the revdb log */
        uint64_t remaining = total_stop_points - rpy_revdb.stop_point_break;
        uint64_t delta;
        double step = STEP_RATIO;
        int remaining_freezes = NUM_FROZEN_PROCESSES - frozen_num_pipes;
        if (step * remaining_freezes < 1.0)
            step = 1.0 / remaining_freezes;
        delta = (uint64_t)(remaining * step);
        if (delta == 0 || delta > remaining || remaining_freezes == 1)
            rpy_revdb.stop_point_break = total_stop_points;
        else
            rpy_revdb.stop_point_break += delta;
        close(fds[RD_SIDE]);
        fds[RD_SIDE] = -1;
    }
}

static void act_quit(char *p)
{
    cmd_go((uint64_t)-1, NULL, NULL, 'q');
}

static void act_go(char *p)
{
    int64_t target_time = strtoll(p, NULL, 10);
    if (target_time <= 0) {
        printf("usage: go <target_time>\n");
        return;
    }
    cmd_go(target_time, NULL, NULL, 'g');
}

static void act_info(char *p)
{
    char cmd = *p;
    if (cmd == 0)
        cmd = '?';
    printf("info %c=%lld\n", cmd, (long long)rpy_reverse_db_get_value(cmd));
}

static void act_nop(char *p)
{
}

static void act_forward(char *p)
{
    int64_t delta = strtoll(p, NULL, 10);
    if (delta <= 0) {
        if (delta < 0 || *p == 0)
            printf("usage: forward <time_steps>\n");
        return;
    }
    rpy_revdb.stop_point_break = rpy_revdb.stop_point_seen + delta;
}

static void run_debug_process(void)
{
    static struct action_s actions_1[] = {
        { "info", act_info },
        { "quit", act_quit },
        { "__go", act_go },
        { "__forward", act_forward },
        { "", act_nop },
        { NULL }
    };
    while (rpy_revdb.stop_point_break == rpy_revdb.stop_point_seen) {
        stopped_time = rpy_revdb.stop_point_seen;
        stopped_uid = rpy_revdb.unique_id_seen;
        rpy_revdb.unique_id_seen = (-1ULL) << 63;
        if (invoke_after_forward != NULL) {
            execute_rpy_function(invoke_after_forward, invoke_argument);
        }
        else {
            char input[256];
            printf("(%llu)$ ", (unsigned long long)stopped_time);
            fflush(stdout);
            if (fgets(input, sizeof(input), stdin) != input) {
                fprintf(stderr, "\n");
                act_quit("");
                abort();   /* unreachable */
            }
            process_input(input, "command", 1, actions_1);
        }
        rpy_revdb.unique_id_seen = stopped_uid;
        stopped_time = 0;
        stopped_uid = 0;
    }
}

RPY_EXTERN
void rpy_reverse_db_stop_point(void)
{
    if (process_kind == PK_MAIN_PROCESS) {
        make_new_frozen_process();
        if (process_kind == PK_MAIN_PROCESS)
            return;
    }
    assert(process_kind == PK_DEBUG_PROCESS);
    run_debug_process();
}

RPY_EXTERN
void rpy_reverse_db_send_output(RPyString *output)
{
    fwrite(_RPyString_AsString(output), 1, RPyString_Size(output), stdout);
}

RPY_EXTERN
void rpy_reverse_db_change_time(char mode, long long time,
                                void callback(RPyString *), RPyString *arg)
{
    switch (mode) {

    case 'f': {      /* forward */
        if (time < 0) {
            fprintf(stderr, "revdb.go_forward(): negative amount of steps\n");
            exit(1);
        }
        if (stopped_time == 0) {
            fprintf(stderr, "revdb.go_forward(): not from a debug command\n");
            exit(1);
        }
        rpy_revdb.stop_point_break = stopped_time + time;
        invoke_after_forward = callback;
        invoke_argument = arg;
        break;
    }
    case 'g':       /* go */
    case 'b':       /* go non exact */
        cmd_go(time >= 1 ? time : 1, callback, arg, mode);
        abort();    /* unreachable */

    case 'k':       /* breakpoint */
        assert(time > 0);
        if (stopped_time != 0) {
            fprintf(stderr, "revdb.breakpoint(): cannot be called from a "
                            "debug command\n");
            exit(1);
        }
        rpy_revdb.stop_point_break = rpy_revdb.stop_point_seen + time;
        invoke_after_forward = callback;
        invoke_argument = arg;
        break;

    default:
        abort();    /* unreachable */
    }
}

RPY_EXTERN
long long rpy_reverse_db_get_value(char value_id)
{
    switch (value_id) {
    case 'c':       /* current_time() */
        return stopped_time ? stopped_time : rpy_revdb.stop_point_seen;
    case 'f':       /* most_recent_fork() */
        return most_recent_fork;
    case 't':       /* total_time() */
        return total_stop_points;
    case 'b':       /* current_break_time() */
        return rpy_revdb.stop_point_break;
    case 'u':       /* currently_created_objects() */
        return stopped_uid ? stopped_uid : rpy_revdb.unique_id_seen;
    case '1':       /* first_created_object_uid() */
        return first_created_uid;
    default:
        return -1;
    }
}

static void (*unique_id_callback)(void *);

RPY_EXTERN
uint64_t rpy_reverse_db_unique_id_break(void *new_object)
{
    rpy_revdb.unique_id_break = 0;
    unique_id_callback(new_object);
    return rpy_revdb.unique_id_seen;
}

RPY_EXTERN
void rpy_reverse_db_track_object(long long unique_id, void callback(void *))
{
    if (stopped_uid <= 0) {
        fprintf(stderr, "stopped_uid should not be <= 0\n");
        return;
    }
    if (unique_id <= 0) {
        printf("cannot track a prebuilt or debugger-created object\n");
        return;
    }
    if (unique_id < stopped_uid) {
        printf("cannot track the creation of an object already created\n");
        return;
    }
    assert(callback != NULL);
    unique_id_callback = callback;
    rpy_revdb.unique_id_break = unique_id;
}


/* ------------------------------------------------------------ */
