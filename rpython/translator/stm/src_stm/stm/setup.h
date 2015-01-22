/* Imported by rpython/translator/stm/import_stmgc.py */
static void setup_mmap(char *reason);
static void setup_protection_settings(void);
static pthread_t *_get_cpth(stm_thread_local_t *);

#ifndef NDEBUG
static __thread long _stm_segfault_expected = 0;
#define DEBUG_EXPECT_SEGFAULT(v) do {if (v) _stm_segfault_expected++; else _stm_segfault_expected--;} while (0)
#else
#define DEBUG_EXPECT_SEGFAULT(v) {}
#endif
