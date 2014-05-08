/* Imported by rpython/translator/stm/import_stmgc.py */

static char *setup_mmap(char *reason, int *map_fd);
static void close_fd_mmap(int map_fd);
static void setup_protection_settings(void);
static pthread_t *_get_cpth(stm_thread_local_t *);
