from pypy.translator.unsimplify import split_block
from pypy.translator.backendopt import canraise
from pypy.objspace.flow.model import Block, Constant, Variable, Link, \
        c_last_exception, SpaceOperation
from pypy.rpython import rclass


class ExceptionTransformer(object):
    def __init__(self, translator):
        self.translator = translator
        self.raise_analyzer = canraise.RaiseAnalyzer(translator)

    def create_exception_handling(self, graph):
        """After an exception in a direct_call (or indirect_call), that is not caught
        by an explicit
        except statement, we need to reraise the exception. So after this
        direct_call we need to test if an exception had occurred. If so, we return
        from the current graph with an unused value (false/0/0.0/null).
        Because of the added exitswitch we need an additional block.
        """
        exc_data = self.translator.rtyper.getexceptiondata()
        for block in graph.iterblocks():
            last_operation = len(block.operations)-1
            if block.exitswitch == c_last_exception:
                last_operation -= 1
            for i in range(last_operation, -1, -1):
                op = block.operations[i]
                print "considering op", op, i
                if not self.raise_analyzer.can_raise(op):
                    continue

                afterblock = split_block(self.translator, graph, block, i+1)

                block.exitswitch = c_last_exception

                #non-exception case
                block.exits[0].exitcase = block.exits[0].llexitcase = None

                #exception occurred case
                etype = Variable('extra_etype')
                etype.concretetype = exc_data.lltype_of_exception_type
                evalue = Variable('extra_evalue')
                evalue.concretetype = exc_data.lltype_of_exception_value
                
                l = Link([etype, evalue], graph.exceptblock)
                l.extravars(etype, evalue)
                l.prevblock  = block
                l.exitcase   = Exception
                r_case = rclass.get_type_repr(self.translator.rtyper)
                l.llexitcase = r_case.convert_const(l.exitcase)

                block.exits.append(l)

