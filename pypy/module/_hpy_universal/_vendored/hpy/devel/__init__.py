import os.path
from pathlib import Path
from setuptools import Extension
from distutils.errors import DistutilsError, DistutilsSetupError

# NOTE: this file is also imported by PyPy tests, so it must be compatible
# with both Python 2.7 and Python 3.x

_BASE_DIR = Path(__file__).parent

class HPyDevel:
    def __init__(self, base_dir=_BASE_DIR):
        self.base_dir = Path(base_dir)
        self.include_dir = self.base_dir.joinpath('include')
        self.src_dir = self.base_dir.joinpath('src', 'runtime')
        # extra_sources are needed both in CPython and Universal mode
        self._extra_sources = [
            self.src_dir.joinpath('argparse.c'),
        ]
        # ctx_sources are needed only in Universal mode
        self._ctx_sources = list(self.src_dir.glob('ctx_*.c'))

    def get_extra_sources(self):
        return list(map(str, self._extra_sources))

    def get_ctx_sources(self):
        return list(map(str, self._ctx_sources))

    def fix_extension(self, ext, hpy_abi):
        """
        Modify an existing setuptools.Extension to generate an HPy module.
        """
        if hasattr(ext, 'hpy_abi'):
            return
        ext.hpy_abi = hpy_abi
        ext.include_dirs.append(str(self.include_dir))
        ext.sources += self.get_extra_sources()
        if hpy_abi == 'cpython':
            ext.sources += self.get_ctx_sources()
        if hpy_abi == 'universal':
            ext.define_macros.append(('HPY_UNIVERSAL_ABI', None))

    def collect_hpy_ext_names(self, dist, hpy_ext_modules):
        """
        This is sub-optimal but it should work in 99% of the cases, and complain
        clearly in the others.

        In order to implement build_hpy_ext, we need to know whether an
        Extension was put inside hpy_ext_modules or ext_modules, and we need
        to know it ONLY by looking at its name (because that's all we get when
        distutils calls build_hpy_ext.get_ext_filename). So here we collect
        and return all hpy_ext_names.

        However, there is a problem: if the module is inside a package,
        distutils' build_ext.get_ext_fullpath calls get_ext_filename with ONLY
        the last part of the dotted name (see distutils/commands/build_ext.py).

        This means that there is a risk of conflicts if we have two ext
        modules with the same name in two different packages, of which one is
        HPy and the other is legacy; e.g.::

            setup(ext_modules     = [Extension(name='foo.mymod', ...)],
                  hpy_ext_modules = [Extension(name='bar.mymod', ...)],)

        In that case, we cannot know whether ``mymod`` is an HPy ext module or
        not. If we detect such a problem, we exit early, and the only solution
        is to rename one of them :(
        """
        def collect_ext_names(exts):
            if exts is None:
                return set()
            names = set()
            for ext in exts:
                names.add(ext.name) # full name, e.g. 'foo.bar.baz'
                names.add(ext.name.split('.')[-1]) # modname, e.g. 'baz'
            return names

        hpy_ext_names = collect_ext_names(hpy_ext_modules)
        ext_names = collect_ext_names(dist.ext_modules)
        conflicts = hpy_ext_names.intersection(ext_names)
        if conflicts:
            lines = ['\n']
            lines.append('Name conflict between ext_modules and hpy_ext_modules:')
            for name in conflicts:
                lines.append('    - %s' % name)
            lines.append('You can not have modules ending with the same name in both')
            lines.append('ext_modules and hpy_ext_modules: this is a limitation of ')
            lines.append('hpy.devel, please rename one of them.')
            raise DistutilsSetupError('\n'.join(lines))
        return hpy_ext_names

    def fix_distribution(self, dist, hpy_ext_modules):
        from setuptools.command.build_ext import build_ext
        from setuptools.command.install import install

        def is_hpy_extension(ext_name):
            return ext_name in is_hpy_extension._ext_names
        is_hpy_extension._ext_names = self.collect_hpy_ext_names(dist, hpy_ext_modules)

        # add the hpy_extension modules to the normal ext_modules
        if dist.ext_modules is None:
            dist.ext_modules = []
        dist.ext_modules += hpy_ext_modules

        hpy_devel = self
        base_build_ext = dist.cmdclass.get('build_ext', build_ext)
        base_install = dist.cmdclass.get('install', install)

        class build_hpy_ext(base_build_ext):
            """
            Custom distutils command which properly recognizes and handle hpy
            extensions:

              - modify 'include_dirs', 'sources' and 'define_macros' depending on
                the selected hpy_abi

              - modify the filename extension if we are targeting the universal
                ABI.
            """

            def build_extension(self, ext):
                if is_hpy_extension(ext.name):
                    # add the required include_dirs, sources and macros
                    hpy_devel.fix_extension(ext, hpy_abi=self.distribution.hpy_abi)
                return base_build_ext.build_extension(self, ext)

            def get_ext_filename(self, ext_name):
                # this is needed to give the .hpy.so extension to universal extensions
                if is_hpy_extension(ext_name) and self.distribution.hpy_abi == 'universal':
                    ext_path = ext_name.split('.')
                    ext_suffix = '.hpy.so' # XXX Windows?
                    return os.path.join(*ext_path) + ext_suffix
                return base_build_ext.get_ext_filename(self, ext_name)

        class install_hpy(base_install):

            def run(self):
                if self.distribution.hpy_abi == 'universal':
                    raise DistutilsError(
                        'setup.py install is not supported for HPy universal modules.\n'
                        '       At the moment, the only supported method is: \n'
                        '           setup.py --hpy-abi-universal build_ext --inplace')
                return base_install.run(self)

        dist.cmdclass['build_ext'] = build_hpy_ext
        dist.cmdclass['install'] = install_hpy



def handle_hpy_ext_modules(dist, attr, hpy_ext_modules):
    """
    setuptools entry point, see setup.py
    """
    assert attr == 'hpy_ext_modules'

    # Add a global option --hpy-abi to setup.py
    if not hasattr(dist.__class__, 'hpy_abi'):
        dist.__class__.hpy_abi = 'cpython'
        dist.__class__.global_options += [
            ('hpy-abi=', None, 'Specify the HPy ABI mode (default: cpython)')
        ]

    hpy_devel = HPyDevel()
    hpy_devel.fix_distribution(dist, hpy_ext_modules)
