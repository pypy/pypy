
from pypy.tool.autopath import pypydir
from pypy.translator.tool.cbuild import build_executable
import md5
import py
import distutils

py.path.local(pypydir).join('_cache').ensure(dir=1)
cache_dir = py.path.local(pypydir).join('_cache', 'gcc')
cache_dir.ensure(dir=1)

def build_executable_cache(c_files, *args, **kwds):
    s = "\n\n".join([c_file.read() for c_file in c_files])
    hash = md5.md5(s).hexdigest()
    try:
        return cache_dir.join(hash).read()
    except py.error.Error:
        result = py.process.cmdexec(build_executable(c_files, *args, **kwds))
        cache_dir.join(hash).write(result)
        return result

def try_compile_cache(c_files, *args, **kwds):
    s = "\n\n".join([c_file.read() for c_file in c_files])
    hash = md5.md5(s).hexdigest()
    try:
        return eval(cache_dir.join(hash).read())
    except py.error.Error:
        try:
            build_executable(c_files, *args, **kwds)
            result = True
        except (distutils.errors.CompileError,
                distutils.errors.LinkError):
            result = False
        cache_dir.join(hash).write(repr(result))
        return bool(result)
