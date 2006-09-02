
""" basic transform - some play around graph transformations
"""

# this is RPython code which handles proper base elements for
# stack tracing

from pypy.translator import unsimplify, simplify
from pypy.translator.unsimplify import varoftype
from pypy.annotation import model as annmodel
from pypy.objspace.flow import model
from pypy.translator.js.helper import main_exception_helper, ExceptionHelper
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
                arg_example, is_constant = arg
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

##class Transformer(object):
##    def __init__(self, translator):
##        self.translator = translator
##        self.register_helpers()
##    
##    def register_helpers(self):
##        """ Flow necessary additional functions
##        """
##        ann = self.translator.annotator
##        bk = ann.bookkeeper
##        
##        for func_name, func_args in [("enter", [3]), ("leave", []), 
##                ("traceback", [])]:
##            self.flow_exc_handler_method(func_name, func_args)
##        self.excdef = bk.getuniqueclassdef(ExceptionHelper)
##    
##    def flow_exc_handler_method(self, func_name, args):
##        ann = self.translator.annotator
##        example_ann = ann.bookkeeper.annotation_from_example
##        s_args = [example_ann(arg) for arg in args]
##        graph = ann.annotate_helper_method(ExceptionHelper, func_name, s_args)
##        graph.exception_handler_explicit = True
##    
##    def transform_graph(self, graph):
##        # XXX: we do not want to flow low level helpers as well
##        # but for now I do not see how to see them
##        ann = self.translator.annotator
##        if graph.name.startswith("ll_"):
##            return
##        if getattr(graph, 'exception_handler_explicit', False):
##            return
##        # for each graph block enter operation which calls apropriate functions
##        old_start_block = graph.startblock
##        new_start_block = model.Block(old_start_block.inputargs[:])
##        newoutputargs = [unsimplify.copyvar(ann, v)
##            for v in old_start_block.inputargs]
##
##        mapping = {}
##        for old, new in zip(old_start_block.inputargs, newoutputargs):
##            mapping[old] = new
##        old_start_block.renamevariables(mapping)
##        new_start_block.closeblock(model.Link( \
##            new_start_block.inputargs, old_start_block))
##
##        old_start_block.isstartblock = False
##        new_start_block.isstartblock = True
##        
##        self.add_start_operations(graph, new_start_block)
##        
##        args_s = [ann.bindings[v] for v in new_start_block.inputargs]
##        ann.addpendingblock(graph, new_start_block, args_s)
##        graph.startblock = new_start_block
##        
##        #simplify.simplify_graph(graph, [simplify.eliminate_empty_blocks,
##        #                        simplify.join_blocks,
##        #                        simplify.transform_dead_op_vars])
##    
##    #def add_same_as_operations(self, new_block, old_block, old_args, new_args):
##    #    mapping = {}
##    #    for old, new in zip(old_args, new_args):
##    #        new_block.operations.append(model.SpaceOperation("same_as", [old], new))
##    #        mapping[old] = new
##    #    old_block.renamevariables(mapping)
##
##    def add_start_operations(self, graph, block):
##        assert len(block.operations) == 0
##        retval = model.Variable()
##        bk = self.translator.annotator.bookkeeper
##        arg = model.Constant(bk.immutablevalue("enter"))
##        block.operations.append(model.SpaceOperation("getattr", [self.main_instance, arg], retval))
##    
##    def transform_all(self):
##        bk = self.translator.annotator.bookkeeper
##        self.main_instance = model.Constant(bk.immutablevalue(main_exception_helper))
##        for graph in self.translator.graphs:
##            self.transform_graph(graph)
##        self.translator.annotator.complete()
