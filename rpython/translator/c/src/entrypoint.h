#ifdef PYPY_STANDALONE

#ifndef STANDALONE_ENTRY_POINT
#  define STANDALONE_ENTRY_POINT   PYPY_STANDALONE
#endif

RPY_EXTERN void RPython_StartupCode(void);
#if defined(MS_WINDOWS)
  #ifndef PYPY_MAIN_FUNCTION
  #define PYPY_MAIN_FUNCTION wmain
  #endif
  RPY_EXPORTED int PYPY_MAIN_FUNCTION(int argc, wchar_t *argv[]);
#else
  #ifndef PYPY_MAIN_FUNCTION
  #define PYPY_MAIN_FUNCTION main
  #endif
  RPY_EXPORTED int PYPY_MAIN_FUNCTION(int argc, char *argv[]);
#endif
#endif  /* PYPY_STANDALONE */
