from __future__ import generators

from pypy.translator.flowmodel import *

class GraphGlobalVariable(Variable):
    pass

def what_about(opname, args, annotations):
    for ann in annotations:
        if ann.opname == opname and list(ann.args) == args:
            return ann.result
    return None

def get_type(w,annotations):
    if isinstance(w,Constant):
        return type(w.value)
    w_type = what_about('type', [w], annotations)
    if isinstance(w_type ,Constant):
        return w_type.value
    return None

def set_type(var,type,annotations):
    ann = SpaceOperation("type",[var],Constant(type))
    annotations.append(ann)

class Annotator:

    def __init__(self, flowgraph):
        self.flowgraph = flowgraph

    def build_types(self, input_arg_types):
        input_ann = []
        for arg, arg_type in zip(self.flowgraph.get_args(), input_arg_types):
            set_type(arg, arg_type, input_ann)
        return self.build_annotations(input_ann)

    def build_annotations(self,input_annotations):
        self.annotated = {}
        self.endblock = BasicBlock([Variable('_return_value')], [], [], None)
        self.flowin(self.flowgraph.startblock,input_annotations)
        return self.annotated

    def end_annotations(self):
        "Returns (return_value_Variable(), annotations_list)."
        # XXX what if self.endblock not in self.annotated?
        return self.endblock.input_args[0], self.annotated[self.endblock]

    def simplify_calls(self):
        for block, ann in self.annotated.iteritems():
            newops = []
            for op in block.operations:
                if op.opname == "call":
                    w_func, w_varargs, w_kwargs = op.args
                    w_len = what_about('len', [w_varargs], ann)
                    if isinstance(w_len, Constant):
                        args_w = [what_about('getitem', [w_varargs, Constant(i)],
                                             ann)
                                  for i in range(w_len.value)]
                        if None not in args_w:
                            args_w.insert(0, w_func)
                            op = SpaceOperation('simple_call', args_w, op.result)
                            # XXX check that w_kwargs is empty
                newops.append(op)
            block.operations = newops

    #__________________________________________________

    def flowin(self, block, annotations):
        if block not in self.annotated:
            oldannotations = None
            newannotations = annotations[:]
        else:
            oldannotations = self.annotated[block]
            #import sys; print >> sys.stderr, block, oldannotations, annotations,
            newannotations = self.unify(oldannotations,annotations)
            #import sys; print >> sys.stderr, newannotations

        for op in block.operations:
            self.consider_op(op,newannotations)
        self.annotated[block] = newannotations
        if newannotations != oldannotations and block is not self.endblock:
            self.flownext(block.branch,block)
            
    def consider_op(self,op,annotations):
        consider_meth = getattr(self,'consider_op_'+op.opname,None)
        if consider_meth is not None:
            consider_meth(op,annotations)

    def consider_op_add(self,op,annotations):
        arg1,arg2 = op.args
        type1 = get_type(arg1,annotations)
        type2 = get_type(arg2,annotations)
        if type1 == int and type2 == int:
            set_type(op.result,int,annotations)

    consider_op_sub = consider_op_add
    consider_op_and_ = consider_op_add   # don't forget the trailing '_'
    # XXX add more

    # XXX give them Bool result type
    consider_op_lt = consider_op_add
    consider_op_le = consider_op_add
    consider_op_eq = consider_op_add
    consider_op_ne = consider_op_add
    consider_op_gt = consider_op_add
    consider_op_ge = consider_op_add

    def consider_op_newtuple(self,op,annotations):
        set_type(op.result,tuple,annotations)
        ann = SpaceOperation("len",[op.result],Constant(len(op.args)))
        annotations.append(ann)
        for i in range(len(op.args)):
            ann = SpaceOperation("getitem",[op.result,Constant(i)],op.args[i])
            annotations.append(ann)

    def consider_const(self,to_var,const,annotations):
        if getattr(const, 'dummy', False):
            return   # undefined local variables
        set_type(to_var,type(const.value),annotations)

    def flownext(self,branch,curblock):
        getattr(self,'flownext_'+branch.__class__.__name__)(branch,curblock)

    def flownext_Branch(self,branch,curblock):
        if branch.target.has_renaming:
            renaming = {}
            newannotations = []

            for w_from,w_to in zip(branch.args,branch.target.input_args):
                if isinstance(w_from,Variable):
                    renaming.setdefault(w_from, []).append(w_to)
                else:
                    self.consider_const(w_to,w_from,newannotations)        

            def rename(w):
                if isinstance(w,Constant):
                    return [w]
                if isinstance(w,GraphGlobalVariable):
                    return [w]
                else:
                    return renaming.get(w, [])

            def renameall(list_w):
                if list_w:
                    for w in rename(list_w[0]):
                        for tail_w in renameall(list_w[1:]):
                            yield [w] + tail_w
                else:
                    yield []

            for ann in self.annotated[curblock]:
                # we translate a single SpaceOperation(...) into either
                # 0 or 1 or multiple ones, by replacing each variable
                # used in the original operation by (in turn) any of
                # the variables it can be renamed into
                for list_w in renameall([ann.result] + ann.args):
                    result = list_w[0]
                    args = list_w[1:]
                    newannotations.append(SpaceOperation(ann.opname,args,result))
        else:
            newannotations = self.annotated[curblock]
        self.flowin(branch.target,newannotations)
    
    def flownext_ConditionalBranch(self,branch,curblock):
        self.flownext(branch.ifbranch,curblock)
        self.flownext(branch.elsebranch,curblock)

    def flownext_EndBranch(self,branch,curblock):
        branch = Branch([branch.returnvalue], self.endblock)
        self.flownext_Branch(branch,curblock)

    def unify(self,oldannotations,annotations):
        return [ ann for ann in oldannotations if ann in annotations]
    
        
