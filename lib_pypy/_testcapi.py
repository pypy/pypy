from importlib.util import spec_from_file_location, module_from_spec
import os

try:
    import cpyext
except ImportError:
    pass   # no 'cpyext', but we still have to define e.g. awaitType
else:
    import _pypy_testcapi
    cfile = '_testcapimodule.c'
    csources = [cfile,
                '_testcapi/abstract.c',
                '_testcapi/buffer.c',
                '_testcapi/bytearray.c',
                #'_testcapi/bytes.c',
                #'_testcapi/code.c',
                '_testcapi/codec.c',
                #'_testcapi/complex.c',
                '_testcapi/datetime.c',
                #'_testcapi/dict.c',
                '_testcapi/docstring.c',
                '_testcapi/eval.c',
                '_testcapi/exceptions.c',
                '_testcapi/file.c',
                #'_testcapi/float.c',
                '_testcapi/getargs.c',
                #'_testcapi/heaptype.c',
                '_testcapi/heaptype_relative.c',
                '_testcapi/immortal.c',
                #'_testcapi/import.c',
                '_testcapi/list.c',
                #'_testcapi/long.c',
                #'_testcapi/mem.c',
                '_testcapi/numbers.c',
                #'_testcapi/pyos.c',
                '_testcapi/pytime.c',
                '_testcapi/run.c',
                '_testcapi/set.c',
                '_testcapi/structmember.c',
                #'_testcapi/sys.c',
                '_testcapi/tuple.c',
                #'_testcapi/unicode.c',
                '_testcapi/vectorcall.c',
                '_testcapi/vectorcall_limited.c',
                #'_testcapi/watchers.c',
               ]
    thisdir = os.path.dirname(__file__)
    output_dir = _pypy_testcapi.get_hashed_dir(os.path.join(thisdir, cfile))
    modfile = '_testcapi' + _pypy_testcapi._get_c_extension_suffix()
    spec = spec_from_file_location('_testcapi',
                                   os.path.join(thisdir, modfile))
    try:
        module_from_spec(spec)
    except ImportError:
        if os.name == 'nt':
            # hack around finding compilers on win32
            try:
                import setuptools
            except ImportError:
                pass
        mod = _pypy_testcapi.compile_shared(csources, '_testcapi', thisdir)

class awaitType:
    def __init__(self, iterator):
        self._iterator = iterator
    def __await__(self):
        return self._iterator

# the hacks above have replaced this module with another, so we need
# to push the extra names into this other module too...
import _testcapi
_testcapi.awaitType = awaitType
