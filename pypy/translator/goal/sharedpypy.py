
import sys, pdb, traceback
from pypy.translator.c.dlltool import DLLDef
from pypy.config.translationoption import get_combined_translation_config
from pypy.rpython.lltypesystem.rffi import charp2str, CCHARP, VOIDP
from pypy.tool.option import make_objspace
from pypy.interpreter.error import OperationError
from pypy.config.pypyoption import pypy_optiondescription, set_pypy_opt_level
from pypy.interpreter.pyopcode import prepare_exec
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.config.translationoption import set_opt_level
from pypy.config.pypyoption import enable_allworkingmodules

OVERRIDES = {
    'translation.debug': False,
}

def main(argv):
    config = get_combined_translation_config(pypy_optiondescription,
        overrides=OVERRIDES, translating=True)
    config.objspace.nofaking = True
    config.objspace.compiler = "ast"
    config.translating = True
    set_opt_level(config, '1')
    set_pypy_opt_level(config, '1')
    enable_allworkingmodules(config)

    space = make_objspace(config)
    policy = PyPyAnnotatorPolicy(single_space = space)
    policy.allow_someobjects = False

    def interpret(source, context):
        source = charp2str(source)
        w_dict = space.newdict()
        try:
            ec = space.getexecutioncontext()
            pycode = ec.compiler.compile(source, 'source', 'exec', 0)
            pycode.exec_code(space, w_dict, w_dict)
        except OperationError, e:
            print "OperationError:"
            print " operror-type: " + e.w_type.getname(space, '?')
            print " operror-value: " + space.str_w(space.str(e.get_w_value(space)))
            return 1
        return 0

    dll = DLLDef('pypylib', [(interpret, [CCHARP, VOIDP])], policy=policy,
                 config=config)
    exe_name = dll.compile()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        raise
    except:
        e, v, tb = sys.exc_info()
        traceback.print_tb(tb)
        print e, v
        pdb.post_mortem(tb)
        
