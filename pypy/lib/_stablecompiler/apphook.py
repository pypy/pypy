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

# temporary fake stuff, to allow to use the translated
# PyPy for testing.

DUMPFILE = 'this_is_the_marshal_file'

def fakeapplevelcompile(tuples, filename, mode):
    import os, marshal
    done = False
    data = marshal.dumps( (tuples, filename, mode, done) )
    f = file(DUMPFILE, "wb")
    f.write(data)
    f.close()
    os.system('%s fakecompiler.py' % get_python())
    f = file(DUMPFILE, "rb")
    data = f.read()
    f.close()
    code, filename, mode, done = marshal.loads(data)
    if not done:
        raise ValueError, "could not fake compile!"
    return code

def get_python():
    try:
        f = file('pythonname')
        res = f.read().strip()
        f.close()
        return res
    except IOError:
        raise ValueError, "I need a local file 'pythonname'"
