import pypy
from pypy.module.pypyjit.interp_jit import PORTAL
from pypy.module.pypyjit.newbool import NewBoolDesc
from pypy.translator.translator import graphof
from pypy.annotation.specialize import getuniquenondirectgraph
from pypy.jit.hintannotator.policy import ManualGraphPolicy

class PyPyHintAnnotatorPolicy(ManualGraphPolicy):
    PORTAL = PORTAL
    
    def look_inside_graph_of_module(self, graph, func, mod):
        if mod.startswith('pypy.objspace'):
            return False
        if '_geninterp_' in func.func_globals: # skip all geninterped stuff
            return False
        if mod.startswith('pypy.interpreter.astcompiler'):
            return False
        if mod.startswith('pypy.interpreter.pyparser'):
            return False
        if mod.startswith('pypy.module.'):
            if not mod.startswith('pypy.module.pypyjit.'):
                return False
        if mod.startswith('pypy.translator.goal.nanos'):
            return False
        if mod in forbidden_modules:
            return False
        if func.__name__.startswith('_mm_') or '_mth_mm_' in func.__name__:
            return False
        if func.__name__.startswith('fastfunc_'):
            return False
        return True

    def seebinary(self, opname):
        name2 = name1 = opname[:3].lower()
        if name1 in ('and', 'or'):
            name1 += '_'
        descr_impl = getattr(
                pypy.objspace.descroperation.DescrOperation, name1)
        obj_impl = getattr(pypy.objspace.std.intobject, name2 + '__Int_Int')
        self.seepath(
            getattr(pypy.interpreter.pyframe.PyFrame, 'BINARY_'+ opname),
            descr_impl,
            obj_impl)
        self.seepath(descr_impl,
                     pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)
        descr_impl = getattr(pypy.objspace.descroperation.DescrOperation,
                             'inplace_' + name2)
        self.seepath(
            getattr(pypy.interpreter.pyframe.PyFrame, 'INPLACE_'+ opname),
            descr_impl,
            obj_impl)
        self.seepath(descr_impl,
                     pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)
        
    def seeunary(self, opname, name=None):
        if name is None:
            name = opname.lower()
        descr_impl = getattr(
                pypy.objspace.descroperation.DescrOperation, name)
        self.seepath(
                getattr(pypy.interpreter.pyframe.PyFrame, 'UNARY_' + opname),
                descr_impl,
                getattr(pypy.objspace.std.intobject, name + '__Int'))
        self.seepath(descr_impl,
                pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)

    def seecmp(self, name):
        descr_impl = getattr(pypy.objspace.descroperation.DescrOperation, name)
        self.seepath(
                pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
                descr_impl,
                getattr(pypy.objspace.std.intobject, name +'__Int_Int'),
                pypy.objspace.std.Space.newbool)
        self.seepath(
                descr_impl,
                pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)

    def fill_timeshift_graphs(self, portal_graph):
        import pypy

        # --------------------
        for binop in 'ADD SUBTRACT MULTIPLY AND OR XOR'.split():
            self.seebinary(binop)
        for cmpname in 'lt le eq ne ge gt'.split():
            self.seecmp(cmpname)
        self.seepath(pypy.interpreter.pyframe.PyFrame.UNARY_NOT,
                     pypy.objspace.std.Space.not_)
        self.seeunary('INVERT')
        self.seeunary('POSITIVE', 'pos')
        self.seeunary('NEGATIVE', 'neg')

        self.seepath(pypy.objspace.descroperation._invoke_binop,
                     pypy.objspace.descroperation._check_notimplemented)
        self.seepath(pypy.objspace.std.intobject.add__Int_Int,
                     pypy.objspace.std.inttype.wrapint,
                     pypy.objspace.std.intobject.W_IntObject.__init__)
        self.seepath(pypy.objspace.descroperation.DescrOperation.add,
                     pypy.objspace.std.Space.type,
                     pypy.objspace.std.Space.gettypeobject)
        self.seepath(pypy.objspace.descroperation.DescrOperation.add,
                     pypy.objspace.std.Space.is_w)
        self.seegraph(pypy.interpreter.pyframe.PyFrame.execute_frame, False)
        # --------------------
        # special timeshifting logic for newbool
        self.seegraph(pypy.objspace.std.Space.newbool, NewBoolDesc)
        self.seepath(pypy.interpreter.pyframe.PyFrame.JUMP_IF_TRUE,
                     pypy.objspace.std.Space.is_true)
        self.seepath(pypy.interpreter.pyframe.PyFrame.JUMP_IF_FALSE,
                     pypy.objspace.std.Space.is_true)

        #
        self.seepath(pypy.interpreter.pyframe.PyFrame.CALL_FUNCTION,
                     pypy.interpreter.function.Function.funccall_valuestack)



forbidden_modules = {'pypy.interpreter.gateway': True,
                     #'pypy.interpreter.baseobjspace': True,
                     'pypy.interpreter.typedef': True,
                     'pypy.interpreter.eval': True,
                     'pypy.interpreter.function': True,
                     'pypy.interpreter.pytraceback': True,
                     }


def get_portal(drv):
    t = drv.translator
    portal = getattr(PORTAL, 'im_func', PORTAL)
    portal_graph = graphof(t, portal)

    policy = PyPyHintAnnotatorPolicy()
    policy.seetranslator(t)
    return portal, policy
