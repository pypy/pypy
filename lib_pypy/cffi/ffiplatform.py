import sys, os


class VerificationError(Exception):
    """ An error raised when verification fails
    """

class VerificationMissing(Exception):
    """ An error raised when incomplete structures are passed into
    cdef, but no verification has been done
    """


LIST_OF_FILE_NAMES = ['sources', 'include_dirs', 'library_dirs',
                      'extra_objects', 'depends']

def get_extension(srcfilename, modname, sources=(), **kwds):
    from distutils.core import Extension
    allsources = [srcfilename]
    for src in sources:
        allsources.append(os.path.normpath(src))
    return Extension(name=modname, sources=allsources, **kwds)

def compile(tmpdir, ext, compiler_verbose=0, target_extension=None,
            embedding=False):
    """Compile a C extension module using distutils."""

    saved_environ = os.environ.copy()
    try:
        outputfilename = _build(tmpdir, ext, compiler_verbose,
                                target_extension, embedding)
        outputfilename = os.path.abspath(outputfilename)
    finally:
        # workaround for a distutils bugs where some env vars can
        # become longer and longer every time it is used
        for key, value in saved_environ.items():
            if os.environ.get(key) != value:
                os.environ[key] = value
    return outputfilename

def _save_val(name):
    import distutils.sysconfig
    config_vars = distutils.sysconfig.get_config_vars()
    return config_vars.get(name, Ellipsis)

def _restore_val(name, value):
    import distutils.sysconfig
    config_vars = distutils.sysconfig.get_config_vars()
    config_vars[name] = value
    if value is Ellipsis:
        del config_vars[name]

def _win32_hack_for_embedding():
    from distutils.msvc9compiler import MSVCCompiler
    if not hasattr(MSVCCompiler, '_remove_visual_c_ref_CFFI_BAK'):
        MSVCCompiler._remove_visual_c_ref_CFFI_BAK = \
            MSVCCompiler._remove_visual_c_ref
    MSVCCompiler._remove_visual_c_ref = lambda self,manifest_file: manifest_file

def _win32_unhack_for_embedding():
    from distutils.msvc9compiler import MSVCCompiler
    MSVCCompiler._remove_visual_c_ref = \
        MSVCCompiler._remove_visual_c_ref_CFFI_BAK

def _build(tmpdir, ext, compiler_verbose=0, target_extension=None,
           embedding=False):
    # XXX compact but horrible :-(
    from distutils.core import Distribution
    import distutils.errors, distutils.log
    #
    dist = Distribution({'ext_modules': [ext]})
    dist.parse_config_files()
    options = dist.get_option_dict('build_ext')
    options['force'] = ('ffiplatform', True)
    options['build_lib'] = ('ffiplatform', tmpdir)
    options['build_temp'] = ('ffiplatform', tmpdir)
    #
    try:
        if sys.platform == 'win32' and embedding:
            _win32_hack_for_embedding()
        old_level = distutils.log.set_threshold(0) or 0
        old_SO = _save_val('SO')
        old_EXT_SUFFIX = _save_val('EXT_SUFFIX')
        try:
            if target_extension is not None:
                _restore_val('SO', target_extension)
                _restore_val('EXT_SUFFIX', target_extension)
            distutils.log.set_verbosity(compiler_verbose)
            dist.run_command('build_ext')
            cmd_obj = dist.get_command_obj('build_ext')
            [soname] = cmd_obj.get_outputs()
        finally:
            distutils.log.set_threshold(old_level)
            _restore_val('SO', old_SO)
            _restore_val('EXT_SUFFIX', old_EXT_SUFFIX)
            if sys.platform == 'win32' and embedding:
                _win32_unhack_for_embedding()
    except (distutils.errors.CompileError,
            distutils.errors.LinkError) as e:
        raise VerificationError('%s: %s' % (e.__class__.__name__, e))
    #
    return soname

try:
    from os.path import samefile
except ImportError:
    def samefile(f1, f2):
        return os.path.abspath(f1) == os.path.abspath(f2)

def maybe_relative_path(path):
    if not os.path.isabs(path):
        return path      # already relative
    dir = path
    names = []
    while True:
        prevdir = dir
        dir, name = os.path.split(prevdir)
        if dir == prevdir or not dir:
            return path     # failed to make it relative
        names.append(name)
        try:
            if samefile(dir, os.curdir):
                names.reverse()
                return os.path.join(*names)
        except OSError:
            pass

# ____________________________________________________________

try:
    int_or_long = (int, long)
    import cStringIO
except NameError:
    int_or_long = int      # Python 3
    import io as cStringIO

def _flatten(x, f):
    if isinstance(x, str):
        f.write('%ds%s' % (len(x), x))
    elif isinstance(x, dict):
        keys = sorted(x.keys())
        f.write('%dd' % len(keys))
        for key in keys:
            _flatten(key, f)
            _flatten(x[key], f)
    elif isinstance(x, (list, tuple)):
        f.write('%dl' % len(x))
        for value in x:
            _flatten(value, f)
    elif isinstance(x, int_or_long):
        f.write('%di' % (x,))
    else:
        raise TypeError(
            "the keywords to verify() contains unsupported object %r" % (x,))

def flatten(x):
    f = cStringIO.StringIO()
    _flatten(x, f)
    return f.getvalue()
