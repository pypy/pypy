from hashlib import md5
import py, os

def cache_file_path(c_files, eci, cache_root, cachename):
    "Builds a filename to cache compilation data"
    # Import 'platform' every time, the compiler may have been changed
    from rpython.translator.platform import platform
    cache_dir = cache_root.join(cachename).ensure(dir=1)
    filecontents = [c_file.read() for c_file in c_files]
    key = repr((filecontents, eci, platform.key()))
    hash = md5(key).hexdigest()
    return cache_dir.join(hash)

def build_executable_cache(c_files, eci, ignore_errors=False):
    "Builds and run a program; caches the result"
    # Import 'platform' every time, the compiler may have been changed
    from rpython.translator.platform import platform
    from rpython.conftest import cache_dir
    cache_root = py.path.local(cache_dir).ensure(dir=1)
    path = cache_file_path(c_files, eci, cache_root, 'build_executable_cache')
    try:
        return path.read()
    except py.error.Error:
        _previous = platform.log_errors
        try:
            if ignore_errors:
                platform.log_errors = False
            result = platform.execute(platform.compile(c_files, eci))
        finally:
            if ignore_errors:
                del platform.log_errors
            # ^^^remove from the instance --- needed so that it can
            # compare equal to another instance without it
            if platform.log_errors != _previous:
                platform.log_errors = _previous
        try_atomic_write(path, result.out)
        return result.out

def try_atomic_write(path, data):
    path = str(path)
    tmppath = '%s~%d' % (path, os.getpid())
    f = open(tmppath, 'wb')
    f.write(data)
    f.close()
    try:
        os.rename(tmppath, path)
    except OSError:
        try:
            os.unlink(tmppath)
        except OSError:
            pass

def try_compile_cache(c_files, eci):
    "Try to compile a program.  If it works, caches this fact."
    # Import 'platform' every time, the compiler may have been changed
    from rpython.translator.platform import platform
    from rpython.conftest import cache_dir
    cache_root = py.path.local(cache_dir).ensure(dir=1)
    path = cache_file_path(c_files, eci, cache_root, 'try_compile_cache')
    try:
        data = path.read()
        if data == 'True':
            return True
    except py.error.Error:
        pass
    #
    _previous = platform.log_errors
    try:
        platform.log_errors = False
        platform.compile(c_files, eci)
        # ^^^ may raise CompilationError.  We don't cache such results.
    finally:
        del platform.log_errors
        # ^^^remove from the instance --- needed so that it can
        # compare equal to another instance without it
        if platform.log_errors != _previous:
            platform.log_errors = _previous
    path.write('True')
    return True
