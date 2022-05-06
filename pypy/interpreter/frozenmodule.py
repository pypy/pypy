import os
from rpython.config.translationoption import CACHE_DIR
from pypy.module.marshal import interp_marshal
from pypy.interpreter.pycode import default_magic


lib_python = os.path.join(os.path.dirname(__file__),
                          '..', '..', 'lib-python', '3')

def compile_bootstrap_module(space, name, w_name, w_dict, directory="importlib"):
    """NOT_RPYTHON"""
    with open(os.path.join(lib_python, directory, name + '.py')) as fp:
        source = fp.read()
    pathname = "<frozen %s>" % (directory + "." + name).lstrip(".")
    code_w = _cached_compile(space, name, source, pathname, 'exec', 0)
    space.setitem(w_dict, space.wrap('__name__'), w_name)
    space.setitem(w_dict, space.wrap('__builtins__'),
                  space.wrap(space.builtin))
    code_w.exec_code(space, w_dict, w_dict)

def _cached_compile(space, name, source, *args):
    cachename = os.path.join(CACHE_DIR, 'frozen_importlib_%d%s' % (
        default_magic, name))
    try:
        if space.config.translating:
            raise IOError("don't use the cache when translating pypy")
        with open(cachename, 'rb') as f:
            previous = f.read(len(source) + 1)
            if previous != source + '\x00':
                raise IOError("source changed")
            w_bin = space.newbytes(f.read())
            code_w = interp_marshal.loads(space, w_bin)
    except IOError:
        # must (re)compile the source
        ec = space.getexecutioncontext()
        code_w = ec.compiler.compile(source, *args)
        w_bin = interp_marshal.dumps(
            space, code_w)
        content = source + '\x00' + space.bytes_w(w_bin)
        with open(cachename, 'wb') as f:
            f.write(content)
    return code_w

