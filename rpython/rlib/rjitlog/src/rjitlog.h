#define _GNU_SOURCE 1

#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */
#ifndef RPY_EXTERN
#define RPY_EXTERN RPY_EXPORTED
#endif
#ifdef _WIN32
#define RPY_EXPORTED __declspec(dllexport)
#else
#define RPY_EXPORTED  extern __attribute__((visibility("default")))
#endif

RPY_EXTERN char * jitlog_init(int);
RPY_EXTERN void jitlog_try_init_using_env(void);
RPY_EXTERN int jitlog_enabled();
RPY_EXTERN void jitlog_write_marked(char*, int);
RPY_EXTERN void jitlog_teardown();
