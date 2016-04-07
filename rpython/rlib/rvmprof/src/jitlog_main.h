#include <string.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

static int jitlog_fd = -1;
static int jitlog_ready = 0;

RPY_EXTERN
int jitlog_enabled()
{
    return jitlog_ready;
}

RPY_EXTERN
void jitlog_try_init_using_env(void) {
    if (jitlog_ready) { return; }

    char *filename = getenv("JITLOG");

    if (filename && filename[0]) {
        // mode is 775
        mode_t mode = S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH;
        jitlog_fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, mode);
        if (jitlog_fd == -1) {
            dprintf(2, "could not open '%s': ", filename);
            perror(NULL);
            exit(-1);
        }
    } else {
        jitlog_ready = 0;
        return;
    }
#ifndef _WIN32
    unsetenv("JITLOG");
#else
    putenv("JITLOG=");
#endif
    jitlog_ready = 1;
}

RPY_EXTERN
char *jitlog_init(int fd)
{
    jitlog_fd = fd;
    jitlog_ready = 1;
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
}

RPY_EXTERN
void jitlog_write_marked(int tag, char * text, int length)
{
    if (!jitlog_ready) { return; }

    char header[1];
    header[0] = tag;
    write(jitlog_fd, (const char*)&header, 1);
    write(jitlog_fd, text, length);
}
