
#include <string.h>
#include <stddef.h>
#include <stdlib.h>

#include <stdio.h>
#include <unistd.h>
#include "src/profiling.h"
#include "src/debug_print.h"

long pypy_have_debug_prints = -1;
FILE *pypy_debug_file = NULL;
static unsigned char debug_ready = 0;
static unsigned char debug_profile = 0;
static char *debug_start_colors_1 = "";
static char *debug_start_colors_2 = "";
static char *debug_stop_colors = "";
static char *debug_prefix = NULL;

static void pypy_debug_open(void)
{
  char *filename = getenv("PYPYLOG");
  if (filename)
#ifndef MS_WINDOWS
    unsetenv("PYPYLOG");   /* don't pass it to subprocesses */
#else
    putenv("PYPYLOG=");    /* don't pass it to subprocesses */
#endif
  if (filename && filename[0])
    {
      char *colon = strchr(filename, ':');
      if (!colon)
        {
          /* PYPYLOG=filename --- profiling version */
          debug_profile = 1;
          pypy_setup_profiling();
        }
      else
        {
          /* PYPYLOG=prefix:filename --- conditional logging */
          int n = colon - filename;
          debug_prefix = malloc(n + 1);
          memcpy(debug_prefix, filename, n);
          debug_prefix[n] = '\0';
          filename = colon + 1;
        }
      if (strcmp(filename, "-") != 0)
        pypy_debug_file = fopen(filename, "w");
    }
  if (!pypy_debug_file)
    {
      pypy_debug_file = stderr;
      if (isatty(2))
        {
          debug_start_colors_1 = "\033[1m\033[31m";
          debug_start_colors_2 = "\033[31m";
          debug_stop_colors = "\033[0m";
        }
    }
  debug_ready = 1;
}

void pypy_debug_ensure_opened(void)
{
  if (!debug_ready)
    pypy_debug_open();
}


#ifndef _WIN32

     static long long pypy_read_timestamp(void)
     {
#  ifdef CLOCK_THREAD_CPUTIME_ID
       struct timespec tspec;
       clock_gettime(CLOCK_THREAD_CPUTIME_ID, &tspec);
       return ((long long)tspec.tv_sec) * 1000000000LL + tspec.tv_nsec;
#  else
       /* argh, we don't seem to have clock_gettime().  Bad OS. */
       struct timeval tv;
       gettimeofday(&tv, NULL);
       return ((long long)tv.tv_sec) * 1000000LL + tv.tv_usec;
#  endif
     }
#endif


static unsigned char startswithoneof(const char *str, const char *substr)
{
  const char *p = str;
  for (; *substr; substr++)
    {
      if (*substr != ',')
        {
          if (p && *p++ != *substr)
            p = NULL;   /* mismatch */
        }
      else if (p != NULL)
        return 1;   /* match */
      else
        p = str;    /* mismatched, retry with the next */
    }
  return p != NULL;
}

#if defined(_MSC_VER) || defined(__MINGW32__)
#define PYPY_LONG_LONG_PRINTF_FORMAT "I64"
#else
#define PYPY_LONG_LONG_PRINTF_FORMAT "ll"
#endif

static void display_startstop(const char *prefix, const char *postfix,
                              const char *category, const char *colors)
{
  long long timestamp;
  READ_TIMESTAMP(timestamp);
  fprintf(pypy_debug_file, "%s[%"PYPY_LONG_LONG_PRINTF_FORMAT"x] %s%s%s\n%s",
          colors,
          timestamp, prefix, category, postfix,
          debug_stop_colors);
}

void pypy_debug_start(const char *category)
{
  pypy_debug_ensure_opened();
  /* Enter a nesting level.  Nested debug_prints are disabled by default
     because the following left shift introduces a 0 in the last bit.
     Note that this logic assumes that we are never going to nest
     debug_starts more than 31 levels (63 on 64-bits). */
  pypy_have_debug_prints <<= 1;
  if (!debug_profile)
    {
      /* non-profiling version */
      if (!debug_prefix || !startswithoneof(category, debug_prefix))
        {
          /* wrong section name, or no PYPYLOG at all, skip it */
          return;
        }
      /* else make this subsection active */
      pypy_have_debug_prints |= 1;
    }
  display_startstop("{", "", category, debug_start_colors_1);
}

void pypy_debug_stop(const char *category)
{
  if (debug_profile | (pypy_have_debug_prints & 1))
    display_startstop("", "}", category, debug_start_colors_2);
  pypy_have_debug_prints >>= 1;
}
