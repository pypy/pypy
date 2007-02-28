"""Mixed module for dynamic grammar modification"""

from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """dyngram module definition"""
    
    name = 'dyngram'
    appleveldefs = {}
    interpleveldefs = {
        'insert_grammar_rule' : 'pypy.interpreter.pycompiler.insert_grammar_rule',
        }
