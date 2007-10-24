
""" Zipimport module
"""

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevelname = 'zipimport'

    interpleveldefs = {'zipimporter':'interp_zipimport.W_ZipImporter'}

    appleveldefs = {
        'ZipImportError' : 'app_zipimport.ZipImportError',
    }
    
