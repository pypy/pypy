
""" basic transform - some play around graph transformations
"""

from pypy.translator import unsimplify, simplify
from pypy.translator.unsimplify import varoftype
from pypy.annotation import model as annmodel
from pypy.objspace.flow import model
#from pypy.translator.js.helper import main_exception_helper, ExceptionHelper
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import rclass
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

class BasicTransformer(object):
    """ This is basic transformer which applies after annotation level.
    Some more high-level stuff defined here, needed for ie. changing
    block operations, reflowing, etc. etc.
    """
    def __init__(self, translator):
        # some shortcuts
        self.translator = translator
        self.annotator = translator.annotator
        self.bookkeeper = self.annotator.bookkeeper
        
    def genop(self, name, args):
        """ Pass here (example, is_constant) list as args, you'll
        get retval
        """
        real_args = []
        bk = self.bookkeeper
        for arg in args:
            if isinstance(arg, (model.Constant, model.Variable)):
                real_args.append(arg)
            else:
                if isinstance(arg, tuple):
                    arg_example, is_constant = arg
                else:
                    arg_example, is_constant = arg, True
                if is_constant:
                    real_args.append(model.Constant(arg_example, concretetype=bk.immutablevalue(arg_example)))
                else:
                    real_args.append(model.Variable(bk.annotation_from_example(arg_example)))
        retval = model.Variable()
        return model.SpaceOperation(name, real_args, retval), retval
    
    def add_block(self, graph, block):
        ann = self.annotator
        args_s = [ann.bindings[v] for v in block.inputargs]
        try:
            del ann.annotated[block]
        except KeyError:
            pass
        ann.addpendingblock(graph, block, args_s)
        
    def flow_method(self, _class, func_name, args):
        ann = self.annotator
        bk = self.bookkeeper
        example_ann = bk.annotation_from_example
        s_args = [example_ann(arg) for arg in args]
        graph = ann.annotate_helper_method(_class, func_name, s_args)
        return graph

    def transform_all(self):
        bk = self.translator.annotator.bookkeeper
        for graph in self.translator.graphs:
            self.transform_graph(graph)
        self.translator.annotator.complete()

    def get_const(self, arg):
        bk = self.bookkeeper
        return model.Constant(arg, bk.immutablevalue(arg))
