#ifdef PYPY_STANDALONE

#ifndef STANDALONE_ENTRY_POINT
#  define STANDALONE_ENTRY_POINT   PYPY_STANDALONE
#endif

#ifndef PYPY_MAIN_FUNCTION
#define PYPY_MAIN_FUNCTION main
#endif

char *RPython_StartupCode(void);
int PYPY_MAIN_FUNCTION(int argc, char *argv[]);
#endif  /* PYPY_STANDALONE */
