/* Imported by rpython/translator/stm/import_stmgc.py */
#include <stdio.h>
#include <time.h>

static FILE *volatile profiling_file;
static char *profiling_basefn = NULL;
static stm_expand_marker_fn profiling_expand_marker;

#define MARKER_LEN_MAX   160


static bool close_timing_log(void);   /* forward */

static void _stm_profiling_event(stm_thread_local_t *tl,
                                 enum stm_event_e event,
                                 stm_loc_marker_t *marker)
{
    struct buf_s {
        uint32_t tv_sec;
        uint32_t tv_nsec;
        uint32_t thread_num;
        uint8_t event;
        uint8_t marker_length;
        char extra[MARKER_LEN_MAX+1];
    } __attribute__((packed));

    struct buf_s buf;
    struct timespec t;
    buf.thread_num = tl->thread_local_counter;
    buf.event = event;
    buf.marker_length = 0;

    if (marker != NULL && marker->odd_number != 0) {
        buf.marker_length = profiling_expand_marker(get_segment_base(0),
                                                    marker,
                                                    buf.extra, MARKER_LEN_MAX);
    }

    size_t result, outsize = offsetof(struct buf_s, extra) + buf.marker_length;
    FILE *f = profiling_file;
    if (f == NULL)
        return;
    flockfile(f);

    /* We expect the following CLOCK_MONOTONIC to be really monotonic:
       it should guarantee that the file will be perfectly ordered by time.
       That's why we do it inside flockfile()/funlockfile(). */
    clock_gettime(CLOCK_MONOTONIC, &t);
    buf.tv_sec = t.tv_sec;
    buf.tv_nsec = t.tv_nsec;

    result = fwrite_unlocked(&buf, outsize, 1, f);
    funlockfile(f);

    if (result != 1) {
        fprintf(stderr, "stmgc: profiling log file closed unexpectedly: %m\n");

        /* xxx the FILE leaks here, but it is better than random crashes if
           we try to close it while other threads are still writing to it
        */
        profiling_file = NULL;
    }
}

static int default_expand_marker(char *b, stm_loc_marker_t *m, char *p, int s)
{
    *(uintptr_t *)p = m->odd_number;
    return sizeof(uintptr_t);
}

static bool open_timing_log(const char *filename)
{
    FILE *f = fopen(filename, "w");
    profiling_file = f;
    if (f == NULL)
        return false;

    fwrite("STMGC-C8-PROF01\n", 16, 1, f);
    stmcb_timing_event = _stm_profiling_event;
    return true;
}

static bool close_timing_log(void)
{
    if (stmcb_timing_event == &_stm_profiling_event) {
        FILE *f = profiling_file;
        stmcb_timing_event = NULL;
        profiling_file = NULL;
        if (f != NULL)
            fclose(f);
        return true;
    }
    return false;
}

static void prof_forksupport_prepare(void)
{
    FILE *f = profiling_file;
    if (f != NULL)
        fflush(f);
}

static void prof_forksupport_child(void)
{
    if (close_timing_log() && profiling_basefn != NULL) {
        char filename[1024];
        snprintf(filename, sizeof(filename),
                 "%s.fork%ld", profiling_basefn, (long)getpid());
        open_timing_log(filename);
    }
}

int stm_set_timing_log(const char *profiling_file_name, int fork_mode,
                       stm_expand_marker_fn expand_marker)
{
    close_timing_log();
    free(profiling_basefn);
    profiling_basefn = NULL;

    if (profiling_file_name == NULL)
        return 0;

    if (!expand_marker)
        expand_marker = default_expand_marker;
    profiling_expand_marker = expand_marker;

    static bool fork_support_ready = false;
    if (!fork_support_ready) {
        int res = pthread_atfork(prof_forksupport_prepare,
                                 NULL, prof_forksupport_child);
        if (res != 0)
            stm_fatalerror("pthread_atfork() failed: %d", res);
        fork_support_ready = true;
    }

    if (!open_timing_log(profiling_file_name))
        return -1;

    if (fork_mode != 0)
        profiling_basefn = strdup(profiling_file_name);
    return 0;
}
