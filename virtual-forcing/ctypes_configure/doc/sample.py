
from ctypes_configure import configure
import ctypes

class CConfigure:
    _compilation_info_ = configure.ExternalCompilationInfo(
        
        # all lines landing in C header before includes
        pre_include_lines = [],

        # list of .h files to include
        includes = ['time.h', 'sys/time.h', 'unistd.h'],

        # list of directories to search for include files
        include_dirs = [],

        # all lines landing in C header after includes
        post_include_lines = [],

        # libraries to link with
        libraries = [],

        # library directories
        library_dirs = [],

        # additional C sources to compile with (that go to
        # created .c files)
        separate_module_sources = [],

        # additional existing C source file names
        separate_module_files = [],
        )

    # get real int type out of hint and name
    size_t = configure.SimpleType('size_t', ctypes.c_int)

    # grab value of numerical #define
    NULL = configure.ConstantInteger('NULL')

    # grab #define, whether it's defined or not
    EXISTANT = configure.Defined('NULL')
    NOT_EXISTANT = configure.Defined('XXXNOTNULL')

    # check for existance of C functions
    has_write = configure.Has('write')
    no_xxxwrite = configure.Has('xxxwrite')

    # check for size of type
    sizeof_size_t = configure.SizeOf('size_t')

    # structure, with given hints for interesting fields,
    # types does not need to be too specific.
    # all interesting fields would end up with right offset
    # size and order
    struct_timeval = configure.Struct('struct timeval',[
        ('tv_sec', ctypes.c_int),
        ('tv_usec', ctypes.c_int)])

info = configure.configure(CConfigure)

assert info['has_write']
assert not info['no_xxxwrite']
assert info['NULL'] == 0
size_t = info['size_t']
print "size_t in ctypes is ", size_t
assert ctypes.sizeof(size_t) == info['sizeof_size_t']
assert info['EXISTANT']
assert not info['NOT_EXISTANT']
print
print "fields of struct timeval are "
for name, value in info['struct_timeval']._fields_:
    print "  ", name, " ", value
