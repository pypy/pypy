from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Internal Python object serialization

This module contains functions that can read and write Python values in a binary format. The format is specific to Python, but independent of machine architecture issues (e.g., you can write a Python value to a file on a PC, transport the file to a Sun, and read it back there). Details of the format may change between Python versions."""

    appleveldefs = {
        'dump'          : 'app_marshal.dump',
        'dumps'         : 'app_marshal.dumps',
        'load'          : 'app_marshal.load',
        'loads'         : 'app_marshal.loads',
        '_Marshaller'   : 'app_marshal.Marshaller',
        '_Unmarshaller' : 'app_marshal.Unmarshaller',
    }

    interpleveldefs = {
    }
