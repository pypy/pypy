import os.path
from pathlib import Path
from setuptools import Extension

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
            self.src_dir.joinpath('argparse.c')
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

    def fix_distribution(self, dist, hpy_ext_modules):
        from setuptools.command.build_ext import build_ext

        def is_hpy_extension(ext_name):
            return ext_name in is_hpy_extension._ext_names
        is_hpy_extension._ext_names = set([ext.name for ext in hpy_ext_modules])

        # add the hpy_extension modules to the normal ext_modules
        if dist.ext_modules is None:
            dist.ext_modules = []
        dist.ext_modules += hpy_ext_modules

        hpy_devel = self
        base_class = dist.cmdclass.get('build_ext', build_ext)
        class build_hpy_ext(base_class):
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
                return base_class.build_extension(self, ext)

            def get_ext_filename(self, ext_name):
                # this is needed to give the .hpy.so extension to universal extensions
                if is_hpy_extension(ext_name) and self.distribution.hpy_abi == 'universal':
                    ext_path = ext_name.split('.')
                    ext_suffix = '.hpy.so' # XXX Windows?
                    return os.path.join(*ext_path) + ext_suffix
                return base_class.get_ext_filename(self, ext_name)

        dist.cmdclass['build_ext'] = build_hpy_ext



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
