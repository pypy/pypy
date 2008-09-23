
from pypy.tool.autopath import pypydir
from pypy.translator.tool.cbuild import build_executable
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.tool.cbuild import CompilationError
from pypy.tool.compat import md5
import py

cache_dir_root = py.path.local(pypydir).join('_cache').ensure(dir=1)

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
        result = eci.platform.execute(build_executable(c_files, eci))
        path.write(result)
        return result

def try_compile_cache(c_files, eci):
    path = cache_file_path(c_files, eci, 'try_compile_cache')
    try:
        data = path.read()
    except py.error.Error:
        data = ''
    if not (data.startswith('True') or data.startswith('FAIL\n')):
        try:
            build_executable(c_files, eci)
            data = 'True'
        except CompilationError, e:
            data = 'FAIL\n%s\n' % (e,)
        path.write(data)
    if data.startswith('True'):
        return True
    else:
        assert data.startswith('FAIL\n')
        msg = data[len('FAIL\n'):]
        raise CompilationError(msg.strip())
