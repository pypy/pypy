
from ctypes_configure.cbuild import build_executable, ExternalCompilationInfo
import md5
import py
import distutils
import distutils.errors

cache_dir_root = py.magic.autopath().join('..', '_cache').ensure(dir=1)

def cache_file_path(c_files, eci, cachename):
    cache_dir = cache_dir_root.join(cachename).ensure(dir=1)
    filecontents = [c_file.read() for c_file in c_files]
    key = repr((filecontents, eci))
    hash = md5.md5(key).hexdigest()
    return cache_dir.join(hash)

def build_executable_cache(c_files, eci):
    path = cache_file_path(c_files, eci, 'build_executable_cache')
    try:
        return path.read()
    except py.error.Error:
        result = py.process.cmdexec(build_executable(c_files, eci))
        path.write(result)
        return result

def try_compile_cache(c_files, eci):
    path = cache_file_path(c_files, eci, 'try_compile_cache')
    try:
        return eval(path.read())
    except py.error.Error:
        try:
            build_executable(c_files, eci)
            result = True
        except (distutils.errors.CompileError,
                distutils.errors.LinkError):
            result = False
        path.write(repr(result))
        return result
