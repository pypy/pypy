from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
     """The builtin parser module."""

     applevel_name = 'parser'

     appleveldefs = {
         'ParserError' : 'app_helpers.ParserError'
         }

     interpleveldefs = {
         '__name__'     : '(space.wrap("parser"))',
         '__doc__'      : '(space.wrap("parser module"))',

         'suite'        : 'pyparser.suite',
         'expr'         : 'pyparser.expr',
         'issuite'      : 'pyparser.issuite',
         'isexpr'       : 'pyparser.isexpr',
         'STType'       : 'pyparser.STType',
         'ast2tuple'    : 'pyparser.st2tuple',
         'st2tuple'     : 'pyparser.st2tuple',
         'ast2list'     : 'pyparser.st2list',
         'ast2tuple'    : 'pyparser.st2tuple',
         'ASTType'      : 'pyparser.STType',
         'compilest'    : 'pyparser.compilest',
         'compileast'   : 'pyparser.compilest'
         }
