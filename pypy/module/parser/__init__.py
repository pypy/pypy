from pypy.interpreter.error import OperationError
from pypy.interpreter import module
from pypy.interpreter.lazymodule import LazyModule 

class Module(LazyModule):
    """The builtin parser module. 
    """ 
    appleveldefs = {
        'ParserError'  : 'classes.ParserError', 
        'STType'       : 'classes.STType', 
        'ASTType'      : 'classes.STType', 
    }
        
    interpleveldefs = {
        '__name__'     : '(space.wrap("parser"))', 
        '__doc__'      : '(space.wrap("parser module"))', 

        'compileast'   : 'pyparser.compileast',
        'st2tuple'     : 'pyparser.st2tuple',
        'st2list'      : 'pyparser.st2list',
        'issuite'      : 'pyparser.issuite',
        'ast2tuple'    : 'pyparser.ast2tuple',
        'tuple2st'     : 'pyparser.tuple2st',
        'suite'        : 'pyparser.suite',
        'isexpr'       : 'pyparser.isexpr',
        'expr'         : 'pyparser.expr',
        'ast2list'     : 'pyparser.ast2list',
        'sequence2ast' : 'pyparser.sequence2ast',
        'tuple2ast'    : 'pyparser.tuple2ast',
        'sequence2st'  : 'pyparser.sequence2st',
        '_pickler'     : 'pyparser._pickler',
        'compilest'    : 'pyparser.compilest',
    }

    appleveldefs = {

    }
