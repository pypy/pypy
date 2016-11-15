import cffi, os, sys

ffi = cffi.FFI()
ffi.cdef('''
#define GDBM_READER ...
#define GDBM_WRITER ...
#define GDBM_WRCREAT ...
#define GDBM_NEWDB ...
#define GDBM_FAST ...
#define GDBM_SYNC ...
#define GDBM_NOLOCK ...
#define GDBM_REPLACE ...

void* gdbm_open(char *, int, int, int, void (*)());
void gdbm_close(void*);

typedef struct {
    char *dptr;
    int   dsize;
} datum;

datum gdbm_fetch(void*, datum);
datum pygdbm_fetch(void*, char*, int);
int gdbm_delete(void*, datum);
int gdbm_store(void*, datum, datum, int);
int gdbm_exists(void*, datum);
int pygdbm_exists(void*, char*, int);

int gdbm_reorganize(void*);

datum gdbm_firstkey(void*);
datum gdbm_nextkey(void*, datum);
void gdbm_sync(void*);

char* gdbm_strerror(int);
int gdbm_errno;

void free(void*);
''')


kwds = {}
if sys.platform.startswith('freebsd'):
    _localbase = os.environ.get('LOCALBASE', '/usr/local')
    kwds['include_dirs'] = [os.path.join(_localbase, 'include')]
    kwds['library_dirs'] = [os.path.join(_localbase, 'lib')]

ffi.set_source("_gdbm_cffi", '''
#include <stdlib.h>
#include "gdbm.h"

static datum pygdbm_fetch(GDBM_FILE gdbm_file, char *dptr, int dsize) {
    datum key = {dptr, dsize};
    return gdbm_fetch(gdbm_file, key);
}

static int pygdbm_exists(GDBM_FILE gdbm_file, char *dptr, int dsize) {
    datum key = {dptr, dsize};
    return gdbm_exists(gdbm_file, key);
}
''', libraries=['gdbm'], **kwds)


if __name__ == '__main__':
    ffi.compile()
