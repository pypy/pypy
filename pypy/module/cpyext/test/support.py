import os
import py
from rpython.translator.platform import log
from rpython.translator.platform.distutils_platform import DistutilsPlatform

rpy_platform = DistutilsPlatform()

if os.name != 'nt':
    so_ext = 'so'
else:
    so_ext = 'dll'

def c_compile(cfilenames, eci, outputfilename):
    self = rpy_platform
    libraries = list(eci.libraries)
    include_dirs = list(eci.include_dirs)
    library_dirs = list(eci.library_dirs)
    compile_extra = list(eci.compile_extra)
    link_extra = list(eci.link_extra)
    frameworks = list(eci.frameworks)
    if not self.name in ('win32', 'darwin', 'cygwin'): # xxx
        if 'm' not in libraries:
            libraries.append('m')
        if 'pthread' not in libraries:
            libraries.append('pthread')
    if self.name == 'win32':
        link_extra += ['/DEBUG'] # generate .pdb file
    if self.name == 'darwin':
        # support Fink & Darwinports
        for s in ('/sw/', '/opt/local/'):
            if s + 'include' not in include_dirs and \
                os.path.exists(s + 'include'):
                include_dirs.append(s + 'include')
            if s + 'lib' not in library_dirs and os.path.exists(s + 'lib'):
                library_dirs.append(s + 'lib')
        for framework in frameworks:
            link_extra += ['-framework', framework]

    outputfilename = py.path.local(outputfilename).new(ext=so_ext)
    saved_environ = os.environ.copy()
    try:
        _build(
            cfilenames, outputfilename,
            compile_extra, link_extra,
            include_dirs, libraries, library_dirs)
    finally:
        # workaround for a distutils bugs where some env vars can
        # become longer and longer every time it is used
        for key, value in saved_environ.items():
            if os.environ.get(key) != value:
                os.environ[key] = value
    return outputfilename

def _build(cfilenames, outputfilename, compile_extra, link_extra,
        include_dirs, libraries, library_dirs):
    from distutils.ccompiler import new_compiler
    from distutils import sysconfig
    compiler = new_compiler(force=1)
    sysconfig.customize_compiler(compiler) # XXX
    objects = []
    for cfile in cfilenames:
        cfile = py.path.local(cfile)
        old = cfile.dirpath().chdir()
        try:
            res = compiler.compile([cfile.basename],
                include_dirs=include_dirs, extra_preargs=compile_extra)
            assert len(res) == 1
            cobjfile = py.path.local(res[0])
            assert cobjfile.check()
            objects.append(str(cobjfile))
        finally:
            old.chdir()

    compiler.link_shared_object(
        objects, str(outputfilename),
        libraries=libraries,
        extra_preargs=link_extra,
        library_dirs=library_dirs)
