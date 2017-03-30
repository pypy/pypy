// cannot include this header because it also has definitions
#include "windows.h"
#include "compat.h"
#include "vmp_stack.h"

HANDLE write_mutex;

int prepare_concurrent_bufs(void)
{
    if (!(write_mutex = CreateMutex(NULL, FALSE, NULL)))
        return -1;
    return 0;
}

#include <tlhelp32.h>

int vmp_write_all(const char *buf, size_t bufsize)
{
    int res;
    int fd;
    int count;

    res = WaitForSingleObject(write_mutex, INFINITE);
    fd = vmp_profile_fileno();

    if (fd == -1) {
        ReleaseMutex(write_mutex);
        return -1;
    }
    while (bufsize > 0) {
        count = _write(fd, buf, (long)bufsize);
        if (count <= 0) {
            ReleaseMutex(write_mutex);
            return -1;   /* failed */
        }
        buf += count;
        bufsize -= count;
    }
    ReleaseMutex(write_mutex);
    return 0;
}

