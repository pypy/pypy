#include <string.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

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
            //pypy_setup_profiling();
        } else {
            /* JITLOG=prefix:filename --- conditional logging */
            int n = colon - filename;
            jitlog_prefix = malloc(n + 1);
            memcpy(jitlog_prefix, filename, n);
            //debug_prefix[n] = '\0';
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
            jitlog_fd = open(filename, O_WRONLY | O_CREAT, mode);
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
        jitlog_fd = 2;
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
char *jitlog_init(int fd, const char * prefix)
{
    jitlog_fd = fd;
    jitlog_prefix = strdup(prefix);
    return NULL;
}

RPY_EXTERN
void jitlog_teardown()
{
    jitlog_ready = 0;
    if (jitlog_fd == -1) {
        return;
    }
    // close the jitlog file descriptor
    close(jitlog_fd);
    jitlog_fd = -1;
    // free the prefix
    if (jitlog_prefix != NULL) {
        free(jitlog_prefix);
    }
}

RPY_EXTERN
void jitlog_write_marked(int tag, char * text, int length)
{
    if (!jitlog_ready) { return; }

    char header[5];
    header[0] = tag;
    // little endian 32 bit singed int
    header[1] = length & 0xff;
    header[2] = (length >> 8) & 0xff;
    header[3] = (length >> 16) & 0xff;
    header[4] = (length >> 24) & 0xff;
    write(jitlog_fd, (const char*)&header, 5);
    write(jitlog_fd, text, length);
}
