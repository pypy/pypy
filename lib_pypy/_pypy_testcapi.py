import os, sys, imp
import tempfile, binascii


def _get_hashed_filename(cfile):
    with open(cfile,'r') as fid:
        content = fid.read()
    # from cffi's Verifier()
    key = '\x00'.join([sys.version[:3], content])
    key += 'cpyext-gc-support-2'   # this branch requires recompilation!
    if sys.version_info >= (3,):
        key = key.encode('utf-8')
    k1 = hex(binascii.crc32(key[0::2]) & 0xffffffff)
    k1 = k1.lstrip('0x').rstrip('L')
    k2 = hex(binascii.crc32(key[1::2]) & 0xffffffff)
    k2 = k2.lstrip('0').rstrip('L')
    try:
        username = os.environ['USER']           #linux, et al
    except KeyError:
        try:
            username = os.environ['USERNAME']   #windows
        except KeyError:
            username = os.getuid()
    return tempfile.gettempdir() + os.path.sep + 'testcapi_%s_%s%s' % (
        username, k1, k2)

def get_hashed_dir(cfile):
    hashed_fn = _get_hashed_filename(cfile)
    try:
        with open(hashed_fn) as f:
            dirname = f.read(1024)
    except IOError:
        dirname = ''
    tmpdir = tempfile.gettempdir()
    if (not dirname or '/' in dirname or '\\' in dirname or '\x00' in dirname
            or not os.path.isdir(os.path.join(tmpdir, dirname))):
        dirname = binascii.hexlify(os.urandom(8))
        if not isinstance(dirname, str):    # Python 3
            dirname = dirname.decode('ascii')
        dirname = 'testcapi_' + dirname
    output_dir = os.path.join(tmpdir, dirname)
    try:
        os.mkdir(output_dir)
    except OSError:
        pass
    return output_dir


def _get_c_extension_suffix():
    for ext, mod, typ in imp.get_suffixes():
        if typ == imp.C_EXTENSION:
            return ext


def compile_shared(csource, modulename, output_dir):
    """Compile '_testcapi.c' or '_ctypes_test.c' into an extension module,
    and import it.
    """
    thisdir = os.path.dirname(__file__)
    assert output_dir is not None

    from distutils.ccompiler import new_compiler

    compiler = new_compiler()
    compiler.output_dir = output_dir

    # Compile .c file
    include_dir = os.path.join(thisdir, '..', 'include')
    if sys.platform == 'win32':
        ccflags = ['-D_CRT_SECURE_NO_WARNINGS']
    else:
        ccflags = ['-fPIC', '-Wimplicit-function-declaration']
    res = compiler.compile([os.path.join(thisdir, csource)],
                           include_dirs=[include_dir],
                           extra_preargs=ccflags)
    object_filename = res[0]

    # set link options
    output_filename = modulename + _get_c_extension_suffix()
    if sys.platform == 'win32':
        # XXX pyconfig.h uses a pragma to link to the import library,
        #     which is currently python27.lib
        library = os.path.join(thisdir, '..', 'libs', 'python27')
        if not os.path.exists(library + '.lib'):
            # For a local translation or nightly build
            library = os.path.join(thisdir, '..', 'pypy', 'goal', 'python27')
        assert os.path.exists(library + '.lib'),'Could not find import library "%s"' % library
        libraries = [library, 'oleaut32']
        extra_ldargs = ['/MANIFEST',  # needed for VC10
                        '/EXPORT:init' + modulename]
    else:
        libraries = []
        extra_ldargs = []

    # link the dynamic library
    compiler.link_shared_object(
        [object_filename],
        output_filename,
        libraries=libraries,
        extra_preargs=extra_ldargs)

    # Now import the newly created library, it will replace the original
    # module in sys.modules
    fp, filename, description = imp.find_module(modulename, path=[output_dir])
    with fp:
        imp.load_module(modulename, fp, filename, description)

    # If everything went fine up to now, write the name of this new
    # directory to 'hashed_fn', for future processes (and to avoid a
    # growing number of temporary directories that are not completely
    # obvious to clean up on Windows)
    hashed_fn = _get_hashed_filename(os.path.join(thisdir, csource))
    try:
        with open(hashed_fn, 'w') as f:
            f.write(os.path.basename(output_dir))
    except IOError:
        pass
