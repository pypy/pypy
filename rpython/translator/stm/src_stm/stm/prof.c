/* Imported by rpython/translator/stm/import_stmgc.py */
#include <time.h>


static FILE *profiling_file;
static char *profiling_basefn = NULL;
static int (*profiling_expand_marker)(stm_loc_marker_t *, char *, int);


static void _stm_profiling_event(stm_thread_local_t *tl,
                                 enum stm_event_e event,
                                 stm_loc_marker_t *markers)
{
    struct buf_s {
        uint32_t tv_sec;
        uint32_t tv_nsec;
        uint32_t thread_num;
        uint32_t other_thread_num;
        uint8_t event;
        uint8_t marker_length[2];
        char extra[256];
    } __attribute__((packed));

    struct buf_s buf;
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    buf.tv_sec = t.tv_sec;
    buf.tv_nsec = t.tv_nsec;
    buf.thread_num = tl->thread_local_counter;
    buf.other_thread_num = 0;
    buf.event = event;

    int len0 = 0;
    int len1 = 0;
    if (markers != NULL) {
        if (markers[1].tl != NULL)
            buf.other_thread_num = markers[1].tl->thread_local_counter;
        if (markers[0].odd_number != 0)
            len0 = profiling_expand_marker(&markers[0], buf.extra, 128);
        if (markers[1].odd_number != 0)
            len1 = profiling_expand_marker(&markers[1], buf.extra + len0, 128);
    }
    buf.marker_length[0] = len0;
    buf.marker_length[1] = len1;

    fwrite(&buf, offsetof(struct buf_s, extra) + len0 + len1,
           1, profiling_file);
}

static int default_expand_marker(stm_loc_marker_t *m, char *p, int s)
{
    *(uintptr_t *)p = m->odd_number;
    return sizeof(uintptr_t);
}

static bool open_timing_log(const char *filename)
{
    profiling_file = fopen(filename, "w");
    if (profiling_file == NULL)
        return false;

    fwrite("STMGC-C7-PROF01\n", 16, 1, profiling_file);
    stmcb_timing_event = _stm_profiling_event;
    return true;
}

static bool close_timing_log(void)
{
    if (stmcb_timing_event == &_stm_profiling_event) {
        stmcb_timing_event = NULL;
        fclose(profiling_file);
        profiling_file = NULL;
        return true;
    }
    return false;
}

static void prof_forksupport_prepare(void)
{
    if (profiling_file != NULL)
        fflush(profiling_file);
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
                       int expand_marker(stm_loc_marker_t *, char *, int))
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
            stm_fatalerror("pthread_atfork() failed: %m");
        fork_support_ready = true;
    }

    if (!open_timing_log(profiling_file_name))
        return -1;

    if (fork_mode != 0)
        profiling_basefn = strdup(profiling_file_name);
    return 0;
}
