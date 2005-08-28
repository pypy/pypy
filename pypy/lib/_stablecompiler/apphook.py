#
# overridable part of applevel compiler
# function applevelcompile can be patched at runtime
#

from _stablecompiler.misc import set_filename
from _stablecompiler.pycodegen import ModuleCodeGenerator
from _stablecompiler.pycodegen import InteractiveCodeGenerator
from _stablecompiler.pycodegen import ExpressionCodeGenerator
from _stablecompiler.transformer import Transformer

def applevelcompile(tuples, filename, mode, flag_names ):
    transformer = Transformer(filename)
    tree = transformer.compile_node(tuples)
    set_filename(filename, tree)
    if mode == 'exec':
        codegenerator = ModuleCodeGenerator(tree, flag_names)
    elif mode == 'single':
        codegenerator = InteractiveCodeGenerator(tree, flag_names)
    else: # mode == 'eval':
        codegenerator = ExpressionCodeGenerator(tree, flag_names)
    return codegenerator.getCode()

# temporary fake stuff, to allow to use the translated
# PyPy for testing.

DUMPFILE = 'this_is_the_marshal_file'

def fakeapplevelcompile(tuples_or_src, filename, mode, flag_names):
    import os, marshal
    done = False
    try:
        data = marshal.dumps( (tuples_or_src, filename, mode, done, flag_names))
    except ValueError:
        raise ValueError, ("ST tuple too deeply nested for fake compiling!"
                           " Please use the fakecompletely option")
    f = file(DUMPFILE, "wb")
    f.write(data)
    f.close()
    os.system('%s fakecompiler.py' % get_python())
    f = file(DUMPFILE, "rb")
    data = f.read()
    f.close()
    code_or_syntax, filename, mode, done, flag_names = marshal.loads(data)
    if not done:
        raise ValueError, "could not fake compile!"
    if type(code_or_syntax) is tuple:
        raise SyntaxError(*code_or_syntax)
    return code_or_syntax

def get_python():
    try:
        f = file('pythonname')
        res = f.read().strip()
        f.close()
        return res
    except IOError:
        raise ValueError, "I need a local file 'pythonname'"
