from cffi import FFI

ffi = FFI()

ffi.set_source("_pwd_cffi", """
#include <sys/types.h>
#include <pwd.h>
""")


ffi.cdef("""

typedef int uid_t;
typedef int gid_t;

struct passwd {
    char *pw_name;
    char *pw_passwd;
    uid_t pw_uid;
    gid_t pw_gid;
    char *pw_gecos;
    char *pw_dir;
    char *pw_shell;
    ...;
};

struct passwd *getpwuid(uid_t uid);
struct passwd *getpwnam(const char *name);

struct passwd *getpwent(void);
void setpwent(void);
void endpwent(void);

""")


if __name__ == "__main__":
    ffi.compile()
