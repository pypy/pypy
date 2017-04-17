/* This file is mostly a copy of CPython's Module/_posixsubprocess.c */
/* modified for PyPy: Removed dependency on Python API. */

/* Authors: Gregory P. Smith & Jeffrey Yasskin */
#if defined(HAVE_PIPE2) && !defined(_GNU_SOURCE)
# define _GNU_SOURCE
#endif
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif
#if defined(HAVE_SYS_STAT_H) && defined(__FreeBSD__)
#include <sys/stat.h>
#endif
#ifdef HAVE_SYS_SYSCALL_H
#include <sys/syscall.h>
#endif
#include <dirent.h>
#include "_posixsubprocess.h"

#if defined(sun)
/* readdir64 is used to work around Solaris 9 bug 6395699. */
# define readdir readdir64
# define dirent dirent64
# if !defined(HAVE_DIRFD)
/* Some versions of Solaris lack dirfd(). */
#  define dirfd(dirp) ((dirp)->dd_fd)
#  define HAVE_DIRFD
# endif
#endif

#if defined(__FreeBSD__) || (defined(__APPLE__) && defined(__MACH__))
# define FD_DIR "/dev/fd"
#else
# define FD_DIR "/proc/self/fd"
#endif

#define POSIX_CALL(call)   if ((call) == -1) goto error


/* Maximum file descriptor, initialized on module load. */
static long max_fd;


/* Convert ASCII to a positive int, no libc call. no overflow. -1 on error. */
static int
_pos_int_from_ascii(char *name)
{
    int num = 0;
    while (*name >= '0' && *name <= '9') {
        num = num * 10 + (*name - '0');
        ++name;
    }
    if (*name)
        return -1;  /* Non digit found, not a number. */
    return num;
}


#if defined(__FreeBSD__)
/* When /dev/fd isn't mounted it is often a static directory populated
 * with 0 1 2 or entries for 0 .. 63 on FreeBSD, NetBSD and OpenBSD.
 * NetBSD and OpenBSD have a /proc fs available (though not necessarily
 * mounted) and do not have fdescfs for /dev/fd.  MacOS X has a devfs
 * that properly supports /dev/fd.
 */
static int
_is_fdescfs_mounted_on_dev_fd(void)
{
    struct stat dev_stat;
    struct stat dev_fd_stat;
    if (stat("/dev", &dev_stat) != 0)
        return 0;
    if (stat(FD_DIR, &dev_fd_stat) != 0)
        return 0; 
    if (dev_stat.st_dev == dev_fd_stat.st_dev)
        return 0;  /* / == /dev == /dev/fd means it is static. #fail */
    return 1;
}
#endif


/* Is fd found in the sorted Python Sequence? */
static int
_is_fd_in_sorted_fd_sequence(int fd, long *fd_sequence, ssize_t seq_len)
{
    /* Binary search. */
    ssize_t search_min = 0;
    ssize_t search_max = seq_len - 1;
    if (search_max < 0)
        return 0;
    do {
        ssize_t middle = (search_min + search_max) / 2;
        long middle_fd = fd_sequence[middle];
        if (fd == middle_fd)
            return 1;
        if (fd > middle_fd)
            search_min = middle + 1;
        else
            search_max = middle - 1;
    } while (search_min <= search_max);
    return 0;
}


RPY_EXTERN
int rpy_set_inheritable(int fd, int inheritable);   /* rposix.py */

static int
make_inheritable(long *py_fds_to_keep, ssize_t num_fds_to_keep,
                 int errpipe_write)
{
    long i;

    for (i = 0; i < num_fds_to_keep; ++i) {
        long fd = py_fds_to_keep[i];
        if (fd == errpipe_write) {
            /* errpipe_write is part of py_fds_to_keep. It must be closed at
               exec(), but kept open in the child process until exec() is
               called. */
            continue;
        }
        if (rpy_set_inheritable((int)fd, 1) < 0)
            return -1;
    }
    return 0;
}


/* Close all file descriptors in the range start_fd inclusive to
 * end_fd exclusive except for those in py_fds_to_keep.  If the
 * range defined by [start_fd, end_fd) is large this will take a
 * long time as it calls close() on EVERY possible fd.
 */
static void
_close_fds_by_brute_force(int start_fd, int end_fd, long *py_fds_to_keep,
			  ssize_t num_fds_to_keep)
{
    ssize_t keep_seq_idx;
    int fd_num;
    /* As py_fds_to_keep is sorted we can loop through the list closing
     * fds inbetween any in the keep list falling within our range. */
    for (keep_seq_idx = 0; keep_seq_idx < num_fds_to_keep; ++keep_seq_idx) {
        int keep_fd = py_fds_to_keep[keep_seq_idx];
        if (keep_fd < start_fd)
            continue;
        for (fd_num = start_fd; fd_num < keep_fd; ++fd_num) {
            while (close(fd_num) < 0 && errno == EINTR);
        }
        start_fd = keep_fd + 1;
    }
    if (start_fd <= end_fd) {
        for (fd_num = start_fd; fd_num < end_fd; ++fd_num) {
            while (close(fd_num) < 0 && errno == EINTR);
        }
    }
}


#if defined(__linux__) && defined(HAVE_SYS_SYSCALL_H)
/* It doesn't matter if d_name has room for NAME_MAX chars; we're using this
 * only to read a directory of short file descriptor number names.  The kernel
 * will return an error if we didn't give it enough space.  Highly Unlikely.
 * This structure is very old and stable: It will not change unless the kernel
 * chooses to break compatibility with all existing binaries.  Highly Unlikely.
 */
struct linux_dirent64 {
   unsigned long long d_ino;
   long long d_off;
   unsigned short d_reclen;     /* Length of this linux_dirent */
   unsigned char  d_type;
   char           d_name[256];  /* Filename (null-terminated) */
};

/* Close all open file descriptors in the range start_fd inclusive to end_fd
 * exclusive. Do not close any in the sorted py_fds_to_keep list.
 *
 * This version is async signal safe as it does not make any unsafe C library
 * calls, malloc calls or handle any locks.  It is _unfortunate_ to be forced
 * to resort to making a kernel system call directly but this is the ONLY api
 * available that does no harm.  opendir/readdir/closedir perform memory
 * allocation and locking so while they usually work they are not guaranteed
 * to (especially if you have replaced your malloc implementation).  A version
 * of this function that uses those can be found in the _maybe_unsafe variant.
 *
 * This is Linux specific because that is all I am ready to test it on.  It
 * should be easy to add OS specific dirent or dirent64 structures and modify
 * it with some cpp #define magic to work on other OSes as well if you want.
 */
static void
_close_open_fd_range_safe(int start_fd, int end_fd, long *py_fds_to_keep,
			  ssize_t num_fds_to_keep)
{
    int fd_dir_fd;
    if (start_fd >= end_fd)
        return;
#ifdef O_CLOEXEC
    fd_dir_fd = open(FD_DIR, O_RDONLY | O_CLOEXEC, 0);
#else
    fd_dir_fd = open(FD_DIR, O_RDONLY, 0);
#ifdef FD_CLOEXEC
    {
        int old = fcntl(fd_dir_fd, F_GETFD);
        if (old != -1)
            fcntl(fd_dir_fd, F_SETFD, old | FD_CLOEXEC);
    }
#endif
#endif
    if (fd_dir_fd == -1) {
        /* No way to get a list of open fds. */
	_close_fds_by_brute_force(start_fd, end_fd, py_fds_to_keep,
				  num_fds_to_keep);
        return;
    } else {
        char buffer[sizeof(struct linux_dirent64)];
        int bytes;
        while ((bytes = syscall(SYS_getdents64, fd_dir_fd,
                                (struct linux_dirent64 *)buffer,
                                sizeof(buffer))) > 0) {
            struct linux_dirent64 *entry;
            int offset;
            for (offset = 0; offset < bytes; offset += entry->d_reclen) {
                int fd;
                entry = (struct linux_dirent64 *)(buffer + offset);
                if ((fd = _pos_int_from_ascii(entry->d_name)) < 0)
                    continue;  /* Not a number. */
                if (fd != fd_dir_fd && fd >= start_fd && fd < end_fd &&
                    !_is_fd_in_sorted_fd_sequence(
			fd, py_fds_to_keep, num_fds_to_keep)) {
                    while (close(fd) < 0 && errno == EINTR);
                }
            }
        }
        close(fd_dir_fd);
    }
}

#define _close_open_fd_range _close_open_fd_range_safe

#else  /* NOT (defined(__linux__) && defined(HAVE_SYS_SYSCALL_H)) */


/* Close all open file descriptors in the range start_fd inclusive to end_fd
 * exclusive. Do not close any in the sorted py_fds_to_keep list.
 *
 * This function violates the strict use of async signal safe functions. :(
 * It calls opendir(), readdir() and closedir().  Of these, the one most
 * likely to ever cause a problem is opendir() as it performs an internal
 * malloc().  Practically this should not be a problem.  The Java VM makes the
 * same calls between fork and exec in its own UNIXProcess_md.c implementation.
 *
 * readdir_r() is not used because it provides no benefit.  It is typically
 * implemented as readdir() followed by memcpy().  See also:
 *   http://womble.decadent.org.uk/readdir_r-advisory.html
 */
static void
_close_open_fd_range_maybe_unsafe(int start_fd, int end_fd,
                                  long *py_fds_to_keep, ssize_t num_fds_to_keep)
{
    DIR *proc_fd_dir;
#ifndef HAVE_DIRFD
    while (_is_fd_in_sorted_fd_sequence(start_fd, py_fds_to_keep, num_fds_to_keep) &&
           (start_fd < end_fd)) {
        ++start_fd;
    }
    if (start_fd >= end_fd)
        return;
    /* Close our lowest fd before we call opendir so that it is likely to
     * reuse that fd otherwise we might close opendir's file descriptor in
     * our loop.  This trick assumes that fd's are allocated on a lowest
     * available basis. */
    while (close(start_fd) < 0 && errno == EINTR);
    ++start_fd;
#endif
    if (start_fd >= end_fd)
        return;

#if defined(__FreeBSD__)
    if (!_is_fdescfs_mounted_on_dev_fd())
        proc_fd_dir = NULL;
    else
#endif
        proc_fd_dir = opendir(FD_DIR);
    if (!proc_fd_dir) {
        /* No way to get a list of open fds. */
        _close_fds_by_brute_force(start_fd, end_fd, py_fds_to_keep, num_fds_to_keep);
    } else {
        struct dirent *dir_entry;
#ifdef HAVE_DIRFD
        int fd_used_by_opendir = dirfd(proc_fd_dir);
#else
        int fd_used_by_opendir = start_fd - 1;
#endif
        errno = 0;
        while ((dir_entry = readdir(proc_fd_dir))) {
            int fd;
            if ((fd = _pos_int_from_ascii(dir_entry->d_name)) < 0)
                continue;  /* Not a number. */
            if (fd != fd_used_by_opendir && fd >= start_fd && fd < end_fd &&
                !_is_fd_in_sorted_fd_sequence(fd, py_fds_to_keep, num_fds_to_keep)) {
                while (close(fd) < 0 && errno == EINTR);
            }
            errno = 0;
        }
        if (errno) {
            /* readdir error, revert behavior. Highly Unlikely. */
            _close_fds_by_brute_force(
		start_fd, end_fd, py_fds_to_keep, num_fds_to_keep);
        }
        closedir(proc_fd_dir);
    }
}

#define _close_open_fd_range _close_open_fd_range_maybe_unsafe

#endif  /* else NOT (defined(__linux__) && defined(HAVE_SYS_SYSCALL_H)) */


/*
 * This function is code executed in the child process immediately after fork
 * to set things up and call exec().
 *
 * All of the code in this function must only use async-signal-safe functions,
 * listed at `man 7 signal` or
 * http://www.opengroup.org/onlinepubs/009695399/functions/xsh_chap02_04.html.
 *
 * This restriction is documented at
 * http://www.opengroup.org/onlinepubs/009695399/functions/fork.html.
 */
void
pypy_subprocess_child_exec(
           char *const exec_array[],
           char *const argv[],
           char *const envp[],
           const char *cwd,
           int p2cread, int p2cwrite,
           int c2pread, int c2pwrite,
           int errread, int errwrite,
           int errpipe_read, int errpipe_write,
           int close_fds, int restore_signals,
           int call_setsid,
           long *py_fds_to_keep,
	   ssize_t num_fds_to_keep,
           int (*preexec_fn)(void*),
           void *preexec_fn_arg)
{
    int i, saved_errno, unused, reached_preexec = 0;
    int result;
    const char* err_msg = "";
    /* Buffer large enough to hold a hex integer.  We can't malloc. */
    char hex_errno[sizeof(saved_errno)*2+1];

    if (make_inheritable(py_fds_to_keep, num_fds_to_keep, errpipe_write) < 0)
        goto error;

    /* Close parent's pipe ends. */
    if (p2cwrite != -1) {
        POSIX_CALL(close(p2cwrite));
    }
    if (c2pread != -1) {
        POSIX_CALL(close(c2pread));
    }
    if (errread != -1) {
        POSIX_CALL(close(errread));
    }
    POSIX_CALL(close(errpipe_read));

    /* When duping fds, if there arises a situation where one of the fds is
       either 0, 1 or 2, it is possible that it is overwritten (#12607). */
    if (c2pwrite == 0)
        POSIX_CALL(c2pwrite = dup(c2pwrite));
    if (errwrite == 0 || errwrite == 1)
        POSIX_CALL(errwrite = dup(errwrite));

    /* Dup fds for child.
       dup2() removes the CLOEXEC flag but we must do it ourselves if dup2()
       would be a no-op (issue #10806). */
    if (p2cread == 0) {
        if (rpy_set_inheritable(p2cread, 1) < 0)
            goto error;
    }
    else if (p2cread != -1)
        POSIX_CALL(dup2(p2cread, 0));  /* stdin */

    if (c2pwrite == 1) {
        if (rpy_set_inheritable(c2pwrite, 1) < 0)
            goto error;
    }
    else if (c2pwrite != -1)
        POSIX_CALL(dup2(c2pwrite, 1));  /* stdout */

    if (errwrite == 2) {
        if (rpy_set_inheritable(errwrite, 1) < 0)
            goto error;
    }
    else if (errwrite != -1)
        POSIX_CALL(dup2(errwrite, 2));  /* stderr */

    /* Close pipe fds.  Make sure we don't close the same fd more than */
    /* once, or standard fds. */
    if (p2cread > 2) {
        POSIX_CALL(close(p2cread));
    }
    if (c2pwrite > 2 && c2pwrite != p2cread) {
        POSIX_CALL(close(c2pwrite));
    }
    if (errwrite != c2pwrite && errwrite != p2cread && errwrite > 2) {
        POSIX_CALL(close(errwrite));
    }

    if (cwd)
        POSIX_CALL(chdir(cwd));

    /* PyPy change: moved this call to the preexec callback */
    /* if (restore_signals) */
    /*     _Py_RestoreSignals(); */

#ifdef HAVE_SETSID
    if (call_setsid)
        POSIX_CALL(setsid());
#endif

    reached_preexec = 1;
    if (preexec_fn != NULL) {
        /* This is where the user has asked us to deadlock their program. */
        result = preexec_fn(preexec_fn_arg);
        if (result == 0) {
            /* Stringifying the exception or traceback would involve
             * memory allocation and thus potential for deadlock.
             * We've already faced potential deadlock by calling back
             * into Python in the first place, so it probably doesn't
             * matter but we avoid it to minimize the possibility. */
            err_msg = "Exception occurred in preexec_fn.";
            errno = 0;  /* We don't want to report an OSError. */
            goto error;
        }
    }

    /* close FDs after executing preexec_fn, which might open FDs */
    if (close_fds) {
        int local_max_fd = max_fd;
#if defined(__NetBSD__)
        local_max_fd = fcntl(0, F_MAXFD);
        if (local_max_fd < 0)
            local_max_fd = max_fd;
#endif
        /* TODO HP-UX could use pstat_getproc() if anyone cares about it. */
        _close_open_fd_range(3, local_max_fd, py_fds_to_keep, num_fds_to_keep);
    }

    /* This loop matches the Lib/os.py _execvpe()'s PATH search when */
    /* given the executable_list generated by Lib/subprocess.py.     */
    saved_errno = 0;
    for (i = 0; exec_array[i] != NULL; ++i) {
        const char *executable = exec_array[i];
        if (envp) {
            execve(executable, argv, envp);
        } else {
            execv(executable, argv);
        }
        if (errno != ENOENT && errno != ENOTDIR && saved_errno == 0) {
            saved_errno = errno;
        }
    }
    /* Report the first exec error, not the last. */
    if (saved_errno)
        errno = saved_errno;

error:
    saved_errno = errno;
    /* Report the posix error to our parent process. */
    /* We ignore all write() return values as the total size of our writes is
     * less than PIPEBUF and we cannot do anything about an error anyways. */
    if (saved_errno) {
        char *cur;
        unused = write(errpipe_write, "OSError:", 8);
        cur = hex_errno + sizeof(hex_errno);
        while (saved_errno != 0 && cur > hex_errno) {
            *--cur = "0123456789ABCDEF"[saved_errno % 16];
            saved_errno /= 16;
        }
        unused = write(errpipe_write, cur, hex_errno + sizeof(hex_errno) - cur);
        unused = write(errpipe_write, ":", 1);
        if (!reached_preexec) {
            /* Indicate to the parent that the error happened before exec(). */
            unused = write(errpipe_write, "noexec", 6);
        }
        /* We can't call strerror(saved_errno).  It is not async signal safe.
         * The parent process will look the error message up. */
    } else {
        unused = write(errpipe_write, "SubprocessError:0:", 18);
        unused = write(errpipe_write, err_msg, strlen(err_msg));
    }
    if (unused) return;  /* silly? yes! avoids gcc compiler warning. */
}


int
pypy_subprocess_cloexec_pipe(int *fds)
{
    int res, saved_errno;
    long oldflags;
#ifdef HAVE_PIPE2
    Py_BEGIN_ALLOW_THREADS
    res = pipe2(fds, O_CLOEXEC);
    Py_END_ALLOW_THREADS
    if (res != 0 && errno == ENOSYS)
    {
#endif
        /* We hold the GIL which offers some protection from other code calling
         * fork() before the CLOEXEC flags have been set but we can't guarantee
         * anything without pipe2(). */
        res = pipe(fds);

        if (res == 0) {
            oldflags = fcntl(fds[0], F_GETFD, 0);
            if (oldflags < 0) res = oldflags;
        }
        if (res == 0)
            res = fcntl(fds[0], F_SETFD, oldflags | FD_CLOEXEC);

        if (res == 0) {
            oldflags = fcntl(fds[1], F_GETFD, 0);
            if (oldflags < 0) res = oldflags;
        }
        if (res == 0)
            res = fcntl(fds[1], F_SETFD, oldflags | FD_CLOEXEC);
#ifdef HAVE_PIPE2
    }
#endif
    if (res == 0 && fds[1] < 3) {
        /* We always want the write end of the pipe to avoid fds 0, 1 and 2
         * as our child may claim those for stdio connections. */
        int write_fd = fds[1];
        int fds_to_close[3] = {-1, -1, -1};
        int fds_to_close_idx = 0;
#ifdef F_DUPFD_CLOEXEC
        fds_to_close[fds_to_close_idx++] = write_fd;
        write_fd = fcntl(write_fd, F_DUPFD_CLOEXEC, 3);
        if (write_fd < 0)  /* We don't support F_DUPFD_CLOEXEC / other error */
#endif
        {
            /* Use dup a few times until we get a desirable fd. */
            for (; fds_to_close_idx < 3; ++fds_to_close_idx) {
                fds_to_close[fds_to_close_idx] = write_fd;
                write_fd = dup(write_fd);
                if (write_fd >= 3)
                    break;
                /* We may dup a few extra times if it returns an error but
                 * that is okay.  Repeat calls should return the same error. */
            }
            if (write_fd < 0) res = write_fd;
            if (res == 0) {
                oldflags = fcntl(write_fd, F_GETFD, 0);
                if (oldflags < 0) res = oldflags;
                if (res == 0)
                    res = fcntl(write_fd, F_SETFD, oldflags | FD_CLOEXEC);
            }
        }
        saved_errno = errno;
        /* Close fds we tried for the write end that were too low. */
        for (fds_to_close_idx=0; fds_to_close_idx < 3; ++fds_to_close_idx) {
            int temp_fd = fds_to_close[fds_to_close_idx];
            while (temp_fd >= 0 && close(temp_fd) < 0 && errno == EINTR);
        }
        errno = saved_errno;  /* report dup or fcntl errors, not close. */
        fds[1] = write_fd;
    }  /* end if write fd was too small */

    if (res != 0)
	return res;
    return 0;
}


void
pypy_subprocess_init(void)
{
#ifdef _SC_OPEN_MAX
    max_fd = sysconf(_SC_OPEN_MAX);
    if (max_fd == -1)
#endif
        max_fd = 256;  /* Matches Lib/subprocess.py */
}
