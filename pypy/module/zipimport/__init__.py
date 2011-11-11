
""" Zipimport module
"""

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    interpleveldefs = {
        'zipimporter':'interp_zipimport.W_ZipImporter',
        '_zip_directory_cache' : 'space.wrap(interp_zipimport.zip_cache)',
        'ZipImportError': 'interp_zipimport.get_error(space)',
    }

    appleveldefs = {
    }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        space = self.space
        # install zipimport hook
        w_path_hooks = space.sys.get('path_hooks')
        from pypy.module.zipimport.interp_zipimport import W_ZipImporter
        w_zipimporter = space.gettypefor(W_ZipImporter)
        space.call_method(w_path_hooks, 'append', w_zipimporter)
