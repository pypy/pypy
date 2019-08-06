#include <stdlib.h>
#include <string.h>
#include <errno.h>


#define RPY_SANDBOX_ARGBUF    512
#define RPY_SANDBOX_NAMEMAX   256

#define RPY_FD_STDIN          0
#define RPY_FD_STDOUT         1

static char sand_argbuf[RPY_SANDBOX_ARGBUF];
static size_t sand_nextarg = RPY_SANDBOX_NAMEMAX;


static void sand_writeall(const char *buf, size_t count)
{
    while (count > 0) {
        ssize_t result = write(RPY_FD_STDOUT, buf, count);
        if (result <= 0) {
            if (result == 0) {
                fprintf(stderr, "sandbox: write(stdout) gives the result 0, "
                                "which is not expected\n");
            }
            else {
                perror("sandbox: write(stdout)");
            }
            abort();
        }
        if (result > count) {
            fprintf(stderr, "sandbox: write(stdout) wrote more data than "
                            "request, which is not expected\n");
            abort();
        }
        buf += result;
        count -= result;
    }
}

static void sand_readall(char *buf, size_t count)
{
    while (count > 0) {
        ssize_t result = read(RPY_FD_STDIN, buf, count);
        if (result <= 0) {
            if (result == 0) {
                fprintf(stderr, "sandbox: stdin is closed, subprocess "
                                "interrupted\n");
            }
            else {
                perror("sandbox: read(stdin)");
            }
            abort();
        }
        if (result > count) {
            fprintf(stderr, "sandbox: read(stdin) returned more data than "
                            "expected\n");
            abort();
        }
        buf += result;
        count -= result;
    }
}


static char *sand_arg_output(size_t size)
{
    char *p = sand_argbuf + sand_nextarg;
    sand_nextarg += size;
    if (sand_nextarg > RPY_SANDBOX_ARGBUF) {
        fprintf(stderr,
                "sandbox: argument buffer overflow (RPY_SANDBOX_ARGBUF)\n");
        abort();
    }
    return p;
}

void rpy_sandbox_arg_i(unsigned long long i)
{
    *(unsigned long long *)sand_arg_output(sizeof(unsigned long long)) = i;
}

void rpy_sandbox_arg_f(double f)
{
    *(double *)sand_arg_output(sizeof(double)) = f;
}

void rpy_sandbox_arg_p(void *p)
{
    *(void **)sand_arg_output(sizeof(void *)) = p;
}

struct sand_data_s {
    void *data;
    size_t size;
};

static void sand_interact(const char *name_and_sig, char expected_result,
                          void *result, size_t result_size)
{
    int saved_errno = errno;

    size_t name_len = strlen(name_and_sig);
    assert(name_len > 0);
    if (name_len > RPY_SANDBOX_NAMEMAX - 1) {
        fprintf(stderr,
             "sandbox: function name buffer overflow (RPY_SANDBOX_NAMEMAX)\n");
        abort();
    }
    char *p = sand_argbuf + RPY_SANDBOX_NAMEMAX - name_len - 1;
    *p = name_len;
    memcpy(p + 1, name_and_sig, name_len);

    assert(sand_nextarg >= RPY_SANDBOX_NAMEMAX);
    assert(sand_nextarg <= RPY_SANDBOX_ARGBUF);

    sand_writeall(p, sand_nextarg - (p - sand_argbuf));
    sand_nextarg = RPY_SANDBOX_NAMEMAX;

    while (1) {
        size_t n1;
        void *p1;
        struct sand_data_s data_hdr;
        char command = 0;
        sand_readall(&command, 1);
        switch (command) {

            case 'v':
            case 'i':
            case 'f':
            case 'p':
                if (expected_result != command) {
                    fprintf(stderr, "sandbox: %s: waiting for a result of type "
                                    "%c but got %c instead\n", name_and_sig,
                                    expected_result, command);
                    abort();
                }
                sand_readall((char *)result, result_size);
                errno = saved_errno;
                return;

            case 'R':
                sand_readall((char *)&data_hdr, sizeof(data_hdr));
                sand_writeall(data_hdr.data, data_hdr.size);
                break;

            case 'Z':
                sand_readall((char *)&data_hdr, sizeof(data_hdr));
                if (data_hdr.size == (size_t)-1)
                    n1 = strlen((char *)data_hdr.data);
                else
                    n1 = strnlen((char *)data_hdr.data, data_hdr.size);
                sand_writeall((char *)&n1, sizeof(n1));
                sand_writeall(data_hdr.data, n1);
                break;

            case 'W':
                sand_readall((char *)&data_hdr, sizeof(data_hdr));
                sand_readall(data_hdr.data, data_hdr.size);
                break;

            case 'M':
                sand_readall((char *)&n1, sizeof(n1));
                p1 = malloc(n1);
                if (p1 == NULL) {
                    fprintf(stderr, "sandbox: command M: failed to allocate "
                                    "%zd bytes\n", n1);
                    abort();
                }
                sand_readall((char *)p1, n1);
                sand_writeall((char *)&p1, sizeof(p1));
                break;

            case 'F':
                sand_readall((char *)&p1, sizeof(p1));
                free(p1);
                break;

            case 'E':
                sand_readall((char *)&saved_errno, sizeof(saved_errno));
                break;

            default:
                fprintf(stderr, "sandbox: protocol error: unexpected byte %d\n",
                        (int)command);
                abort();
        }
    }
}

void rpy_sandbox_res_v(const char *name_and_sig)
{
    sand_interact(name_and_sig, 'v', NULL, 0);
}

unsigned long long rpy_sandbox_res_i(const char *name_and_sig)
{
    unsigned long long result;
    sand_interact(name_and_sig, 'i', &result, sizeof(result));
    return result;
}

double rpy_sandbox_res_f(const char *name_and_sig)
{
    double result;
    sand_interact(name_and_sig, 'f', &result, sizeof(result));
    return result;
}

void *rpy_sandbox_res_p(const char *name_and_sig)
{
    void *result;
    sand_interact(name_and_sig, 'p', &result, sizeof(result));
    return result;
}
