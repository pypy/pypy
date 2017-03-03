#include <string.h>
#include <stddef.h>
#include <stdlib.h>

#include <stdio.h>
#ifndef _WIN32
#include <unistd.h>
#include <time.h>
#include <sys/time.h>
#else
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif
#include "common_header.h"
#include "structdef.h"
#include "src/profiling.h"
#include "src/debug_print.h"

FILE *pypy_debug_file = NULL;
static unsigned char debug_ready = 0;
static unsigned char debug_profile = 0;
static __thread char debug_start_colors_1[32];
static __thread char debug_start_colors_2[28];
__thread char pypy_debug_threadid[16] = {0};
static char *debug_stop_colors = "";
static char *debug_prefix = NULL;

static void pypy_debug_open(void)
{
  char *filename = getenv("PYPYLOG");

  if (filename && filename[0])
    {
      char *newfilename = NULL, *escape;
      char *colon = strchr(filename, ':');
      if (filename[0] == '+')
        {
          filename += 1;
          colon = NULL;
        }
      if (!colon)
        {
          /* PYPYLOG=+filename (or just 'filename') --- profiling version */
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
      escape = strstr(filename, "%d");
      if (escape)  /* a "%d" in the filename is replaced with the pid */
        {
          newfilename = malloc(strlen(filename) + 32);
          if (newfilename != NULL)
            {
              char *p = newfilename;
              memcpy(p, filename, escape - filename);
              p += escape - filename;
              sprintf(p, "%ld", (long)getpid());
              strcat(p, escape + 2);
              filename = newfilename;
            }
        }
      if (strcmp(filename, "-") != 0)
        {
          pypy_debug_file = fopen(filename, "w");
        }

      if (escape)
        {
          free(newfilename);   /* if not null */
          /* the env var is kept and passed to subprocesses */
        }
      else
        {
#ifndef _WIN32
          unsetenv("PYPYLOG");
#else
          putenv("PYPYLOG=");
#endif
        }
    }
  if (!pypy_debug_file)
    {
      pypy_debug_file = stderr;
      if (isatty(2))
        {
          debug_stop_colors = "\033[0m";
        }
    }
  debug_ready = 1;
}

long pypy_debug_offset(void)
{
  if (!debug_ready)
    return -1;
  /* The following fflush() makes sure everything is written now, which
     is just before a fork().  So we can fork() and close the file in
     the subprocess without ending up with the content of the buffer
     written twice. */
  fflush(pypy_debug_file);

  // note that we deliberately ignore errno, since -1 is fine
  // in case this is not a real file
  return ftell(pypy_debug_file);
}

void pypy_debug_ensure_opened(void)
{
  if (!debug_ready)
    pypy_debug_open();
}

void pypy_debug_forked(long original_offset)
{
  /* 'original_offset' ignored.  It used to be that the forked log
     files started with this offset printed out, so that we can
     rebuild the tree structure.  That's overkill... */
  (void)original_offset;

  if (pypy_debug_file)
    {
      if (pypy_debug_file != stderr)
        fclose(pypy_debug_file);
      pypy_debug_file = NULL;
      /* if PYPYLOG was set to a name with "%d" in it, it is still
         alive, and will be reopened with the new subprocess' pid as
         soon as it logs anything */
      debug_ready = 0;
    }
}


#ifndef _WIN32

     RPY_EXTERN long long pypy_read_timestamp(void)
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
    /* any([str.startswith(x) for x in substr.split(',')]) */
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

static long oneofstartswith(const char *str, const char *substr)
{
    /* any([x.startswith(substr) for x in str.split(',')]) */
    const char *p = substr;
    for (; *str; str++) {
        if (p) {
            if (*p++ != *str)
                p = NULL;   /* mismatch */
            else if (*p == '\0')
                return 1;   /* full substring match */
        }
        if (*str == ',')
            p = substr;     /* restart looking */
    }
    return 0;
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


#define bool_cas __sync_bool_compare_and_swap
static Signed threadcounter = 0;

static void _prepare_display_colors(void)
{
    Signed counter;
    char *p;
    while (1) {
        counter = threadcounter;
        if (bool_cas(&threadcounter, counter, counter + 1))
            break;
    }
    if (debug_stop_colors[0] == 0) {
        /* not a tty output: no colors */
        sprintf(debug_start_colors_1, "%d# ", (int)counter);
        sprintf(debug_start_colors_2, "%d# ", (int)counter);
        sprintf(pypy_debug_threadid, "%d#", (int)counter);
    }
    else {
        /* tty output */
        int color = 0;
        color = 31 + (int)(counter % 7);
        sprintf(debug_start_colors_1, "\033[%dm%d# \033[1m",
                color, (int)counter);
        sprintf(debug_start_colors_2, "\033[%dm%d# ",
                color, (int)counter);
#ifdef RPY_STM
        sprintf(pypy_debug_threadid, "\033[%dm%d#\033[0m",
                color, (int)counter);
#endif
    }
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
  if (!debug_start_colors_1[0])
    _prepare_display_colors();
  display_startstop("{", "", category, debug_start_colors_1);
}

void pypy_debug_stop(const char *category)
{
  if (debug_profile | (pypy_have_debug_prints & 1))
    display_startstop("", "}", category, debug_start_colors_2);
  pypy_have_debug_prints >>= 1;
}

long pypy_have_debug_prints_for(const char *category_prefix)
{
  pypy_debug_ensure_opened();
  return (!debug_profile && debug_prefix &&
          /* if 'PYPYLOG=abc,xyz:-' and prefix=="ab", then return 1 */
          (oneofstartswith(debug_prefix, category_prefix) ||
           /* if prefix=="abcdef" and 'PYPYLOG=abc,xyz:-' then return 1 */
           startswithoneof(category_prefix, debug_prefix)));
}
