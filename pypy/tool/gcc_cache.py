from pypy.tool.autopath import pypydir
from pypy.translator.platform import CompilationError
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.compat import md5
import py

cache_dir_root = py.path.local(pypydir).join('_cache').ensure(dir=1)

def cache_file_path(c_files, eci, cachename):
    "Builds a filename to cache compilation data"
    # Import 'platform' every time, the compiler may have been changed
    from pypy.translator.platform import platform
    cache_dir = cache_dir_root.join(cachename).ensure(dir=1)
    filecontents = [c_file.read() for c_file in c_files]
    key = repr((filecontents, eci, platform.key()))
    hash = md5(key).hexdigest()
    return cache_dir.join(hash)

def build_executable_cache(c_files, eci):
    "Builds and run a program; caches the result"
    # Import 'platform' every time, the compiler may have been changed
    from pypy.translator.platform import platform
    path = cache_file_path(c_files, eci, 'build_executable_cache')
    try:
        return path.read()
    except py.error.Error:
        result = platform.execute(platform.compile(c_files, eci))
        path.write(result.out)
        return result.out

def try_compile_cache(c_files, eci):
    "Try to compile a program; caches the result (starts with 'True' or 'FAIL')"
    # Import 'platform' every time, the compiler may have been changed
    from pypy.translator.platform import platform
    path = cache_file_path(c_files, eci, 'try_compile_cache')
    try:
        data = path.read()
    except py.error.Error:
        data = ''
    if not (data.startswith('True') or data.startswith('FAIL\n')):
        try:
            _previous = platform.log_errors
            try:
                platform.log_errors = False
                platform.compile(c_files, eci)
            finally:
                del platform.log_errors
                # ^^^remove from the instance --- needed so that it can
                # compare equal to another instance without it
                if platform.log_errors != _previous:
                    platform.log_errors = _previous
            data = 'True'
            path.write(data)
        except CompilationError, e:
            data = 'FAIL\n%s\n' % (e,)
    if data.startswith('True'):
        return True
    else:
        assert data.startswith('FAIL\n')
        msg = data[len('FAIL\n'):]
        raise CompilationError(msg.strip(), '')
