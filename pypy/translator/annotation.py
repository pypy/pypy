from pypy.translator.flowmodel import *

class GraphGlobalVariable(Variable):
    pass

def get_type(w,annotations):
    if isinstance(w,Constant):
        return type(w.value)
    for ann in annotations:
        if ann.opname == 'type' and list(ann.args) == [var] and isinstance(ann.result,Constant):
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
        self.flowin(self.flowgraph.startblock,input_annotations)
        return self.annotated

    def flownext(self,branch,curblock):
        getattr(self,'flownext_'+branch.__class__.__name__)(branch,curblock)
    
    def flowin(self, block, annotations):
        if block not in self.annotated:
            self.annotated[block] = annotations[:]
        else:
            oldannotations = block.annotations
            newannotations = self.unify(oldannotations,annotations)
            if newannotations == oldannotations:
                return
            self.annotated[block] = newannotations

        for op in block.operations:
                self.consider_op(op,self.annotated[block])
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
                renaming[w_from] = w_to
            else:
                self.consider_const(w_to,w_from,newannotations)        

        def rename(w):
            if isinstance(w,Constant):
                return w
            if isinstance(w,GraphGlobalVariable):
                return w
            else
                return renaming[w]

        for ann in self.annotated[curblock]:
            try:
                result = rename(ann.result)
                args = [ rename(arg) for arg in ann.args ]
            except KeyError:
                pass
            else:
                newannotations.append(SpaceOperation(ann.opname,args,result))

        self.flowin(branch.target,newannotations)
         
    def flownext_ConditionalBranch(self,branch,curblock):
        self.flownext(branch.ifbranch,block)
        self.flownext(branch.elsebranch,block)

    def flownext_EndBranch(self,branch,curblock):
        pass # XXX

    def unify(self,oldannotations,annotations):
        return [ ann for ann in oldannotations if ann in annotations]
    
        
