from pypy.translator.flowmodel import *

class GraphGlobalVariable(Variable):
    pass

def get_type(w,annotations):
    if isinstance(w,Constant):
        return type(w.value)
    for ann in annotations:
        if ann.opname == 'type' and list(ann.args) == [w] and isinstance(ann.result,Constant):
            return ann.result.value
    return None

def set_type(var,type,annotations):
    ann = SpaceOperation("type",[var],Constant(type))
    annotations.append(ann)    

class Annotator:

    def __init__(self, flowgraph):
        self.flowgraph = flowgraph

    def build_annotations(self,input_annotations):
        self.annotated = {}
        self.endblock = BasicBlock([Variable('_return_value')], [], [], None)
        self.flowin(self.flowgraph.startblock,input_annotations)
        return self.annotated

    def end_annotations(self):
        "Returns (return_value_Variable(), annotations_list)."
        # XXX what if self.endblock not in self.annotated?
        return self.endblock.input_args[0], self.annotated[self.endblock]

    def flownext(self,branch,curblock):
        getattr(self,'flownext_'+branch.__class__.__name__)(branch,curblock)
    
    def flowin(self, block, annotations):
        if block not in self.annotated:
            self.annotated[block] = annotations[:]
        else:
            oldannotations = self.annotated[block]
            #import sys; print >> sys.stderr, block, oldannotations, annotations,
            newannotations = self.unify(oldannotations,annotations)
            #import sys; print >> sys.stderr, newannotations
            if newannotations == oldannotations:
                return
            self.annotated[block] = newannotations

        for op in block.operations:
            self.consider_op(op,self.annotated[block])
        if block is not self.endblock:
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

    def consider_const(self,to_var,const,annotations):
        set_type(to_var,type(const.value),annotations)

    def flownext_Branch(self,branch,curblock):

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

        self.flowin(branch.target,newannotations)
         
    def flownext_ConditionalBranch(self,branch,curblock):
        # XXX this hack depends on the fact that ConditionalBranches
        # XXX point to two EggBlocks with *no* renaming necessary
        curannotations = self.annotated[curblock]
        self.flowin(branch.ifbranch.target,curannotations)
        self.flowin(branch.elsebranch.target,curannotations)

    def flownext_EndBranch(self,branch,curblock):
        branch = Branch([branch.returnvalue], self.endblock)
        self.flownext_Branch(branch,curblock)

    def unify(self,oldannotations,annotations):
        return [ ann for ann in oldannotations if ann in annotations]
    
        
