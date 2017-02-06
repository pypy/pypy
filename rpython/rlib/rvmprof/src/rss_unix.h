/* On normal Unices we can get RSS from '/proc/<pid>/status'. */
static int proc_file = -1;

static int setup_rss(void)
{
    char buf[128];

    sprintf(buf, "/proc/%d/status", getpid());
    proc_file = open(buf, O_RDONLY);
    return proc_file;
}

static int teardown_rss(void) {
    close(proc_file);
    proc_file = -1;
    return 0;
}

static long get_current_proc_rss(void)
{
    char buf[1024];
    int i = 0;

    if (lseek(proc_file, 0, SEEK_SET) == -1)
        return -1;
    if (read(proc_file, buf, 1024) == -1)
        return -1;
    while (i < 1020) {
        if (strncmp(buf + i, "VmRSS:\t", 7) == 0) {
            i += 7;
            return atoi(buf + i);
        }
        i++;
    }
    return -1;
}
