#include <string.h>

static int jitlog_fd = -1;
static char * jitlog_prefix = NULL;
static int jitlog_ready = 0;

RPY_EXTERN
int jitlog_filter(int tag)
{
    return 0; // TODO
}

RPY_EXTERN
void jitlog_try_init_using_env(void) {
    if (jitlog_ready) { return; }

    char *filename = getenv("JITLOG");

    if (filename && filename[0]) {
        char *newfilename = NULL, *escape;
        char *colon = strchr(filename, ':');
        if (filename[0] == '+') {
            filename += 1;
            colon = NULL;
        }
        if (!colon) {
            /* JITLOG=+filename (or just 'filename') --- profiling version */
            debug_profile = 1;
            pypy_setup_profiling();
        } else {
            /* JITLOG=prefix:filename --- conditional logging */
            int n = colon - filename;
            debug_prefix = malloc(n + 1);
            memcpy(debug_prefix, filename, n);
            debug_prefix[n] = '\0';
            filename = colon + 1;
        }
        escape = strstr(filename, "%d");
        if (escape) {
            /* a "%d" in the filename is replaced with the pid */
            newfilename = malloc(strlen(filename) + 32);
            if (newfilename != NULL) {
                char *p = newfilename;
                memcpy(p, filename, escape - filename);
                p += escape - filename;
                sprintf(p, "%ld", (long)getpid());
                strcat(p, escape + 2);
                filename = newfilename;
            }
        }
        if (strcmp(filename, "-") != 0) {
            // mode is 775
            mode_t mode = S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH;
            jitlog_fd = open(filename, O_WRONLY | O_CREATE, mode);
        }

        if (escape) {
            free(newfilename);   /* if not null */
            /* the env var is kept and passed to subprocesses */
      } else {
#ifndef _WIN32
          unsetenv("JITLOG");
#else
          putenv("JITLOG=");
#endif
      }
    }
    if (!jitlog_fd) {
        jitlog_fd = stderr;
        // TODO
        //if (isatty(2))
        //  {
        //    debug_start_colors_1 = "\033[1m\033[31m";
        //    debug_start_colors_2 = "\033[31m";
        //    debug_stop_colors = "\033[0m";
        //  }
    }

    jitlog_ready = 1;
}

RPY_EXTERN
char *jitlog_init(int fd, char * prefix)
{
    jitlog_fd = fd;
    jitlog_prefix = strdup(prefix);
    return NULL;
}

RPY_EXTERN
void jitlog_close(int close_fd)
{
    if (jitlog_fd == -1) {
        return;
    }
    if (close_fd) {
        close(jitlog_fd);
    }
    jitlog_fd = -1;
    free(jitlog_prefix);
}

