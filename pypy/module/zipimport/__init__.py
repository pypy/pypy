
""" Zipimport module
"""

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevelname = 'zipimport'

    interpleveldefs = {
        'zipimporter':'interp_zipimport.W_ZipImporter',
        '_zip_directory_cache' : 'space.wrap(interp_zipimport.zip_cache)'
    }

    appleveldefs = {
        'ZipImportError'      : 'app_zipimport.ZipImportError',
    }
    
