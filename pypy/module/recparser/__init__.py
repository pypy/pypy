from pypy.interpreter.error import OperationError, debug_print
import pypy.interpreter.pyparser.pythonparse

from pypy.interpreter.mixedmodule import MixedModule 

# Forward imports so they run at startup time
import pyparser
import pypy.interpreter.pyparser.pythonlexer
import pypy.interpreter.pyparser.pythonparse

class Module(MixedModule):
     """The builtin parser module. 
     """ 


     appleveldefs = {
         'ParserError'  : 'app_class.ParserError',
         }
     interpleveldefs = {
         '__name__'     : '(space.wrap("parser"))', 
         '__doc__'      : '(space.wrap("parser (recparser version) module"))', 

         'suite'        : 'pyparser.suite',
         'expr'         : 'pyparser.expr',
         'STType'       : 'pyparser.STType', 
         'ast2tuple'    : 'pyparser.ast2tuple',
## #        'ASTType'      : 'pyparser.STType', 
##         # 'sequence2st'  : 'pyparser.sequence2st',
##         #'eval_input'   : 'pyparser.eval_input', 
##         #'file_input'   : 'pyparser.file_input', 
##         #'compileast'   : 'pyparser.compileast',
##         #'st2tuple'     : 'pyparser.st2tuple',
##         #'st2list'      : 'pyparser.st2list',
##         #'issuite'      : 'pyparser.issuite',
##         #'ast2tuple'    : 'pyparser.ast2tuple',
##         #'tuple2st'     : 'pyparser.tuple2st',
##         #'isexpr'       : 'pyparser.isexpr',
##         #'ast2list'     : 'pyparser.ast2list',
##         #'sequence2ast' : 'pyparser.sequence2ast',
##         #'tuple2ast'    : 'pyparser.tuple2ast',
##         #'_pickler'     : 'pyparser._pickler',
##         #'compilest'    : 'pyparser.compilest',
     }

