import sys, tempfile, imp, binascii, os

try:
    import cpyext
except ImportError:
    raise ImportError("No module named '_testcapi'")

def get_hashed_dir(cfile):
    # from cffi's Verifier()
    key = '\x00'.join([sys.version[:3], cfile])
    if sys.version_info >= (3,):
        key = key.encode('utf-8')
    k1 = hex(binascii.crc32(key[0::2]) & 0xffffffff)
    k1 = k1.lstrip('0x').rstrip('L')
    k2 = hex(binascii.crc32(key[1::2]) & 0xffffffff)
    k2 = k2.lstrip('0').rstrip('L')
    output_dir = tempfile.gettempdir() + os.path.sep + 'tmp_%s%s' %(k1, k2)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    return output_dir 

cfile = '_testcapimodule.c'
output_dir = get_hashed_dir(cfile)

try:
    fp, filename, description = imp.find_module('_testcapi', path=[output_dir])
    imp.load_module('_testcapi', fp, filename, description)
except ImportError:
    import _pypy_testcapi
    _pypy_testcapi.compile_shared(cfile, '_testcapi', output_dir)
