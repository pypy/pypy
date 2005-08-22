#
# overridable part of applevel compiler
# function applevelcompile can be patched at runtime
#

from _stablecompiler.misc import set_filename
from _stablecompiler.pycodegen import ModuleCodeGenerator
from _stablecompiler.pycodegen import InteractiveCodeGenerator
from _stablecompiler.pycodegen import ExpressionCodeGenerator
from _stablecompiler.transformer import Transformer

def applevelcompile(tuples, filename, mode):
    transformer = Transformer()
    tree = transformer.compile_node(tuples)
    set_filename(filename, tree)
    if mode == 'exec':
        codegenerator = ModuleCodeGenerator(tree)
    elif mode == 'single':
        codegenerator = InteractiveCodeGenerator(tree)
    else: # mode == 'eval':
        codegenerator = ExpressionCodeGenerator(tree)
    return codegenerator.getCode()

return applevelcompile
