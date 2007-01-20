"""
For testing purposes.  Turns *simple enough* low-level graphs
into machine code by calling the rgenop interface.
"""
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel


def compile_graph(rgenop, graph):
    FUNC = lltype.FuncType([v.concretetype for v in graph.getargs()],
                           graph.getreturnvar().concretetype)
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_entrypoint, args_gv = rgenop.newgraph(sigtoken,
                                         "compiled_%s" % (graph.name,))
    builder.start_writing()

    pending_blocks = {graph.startblock: (builder, args_gv)}
    seen_blocks = {}

    def varkind(v):
        return rgenop.kindToken(v.concretetype)

    def var2gv(v):
        if isinstance(v, flowmodel.Variable):
            return varmap[v]
        else:
            return rgenop.genconst(v.value)

    for block in graph.iterblocks():
        builder, args_gv = pending_blocks.pop(block)
        assert len(args_gv) == len(block.inputargs)
        label = builder.enter_next_block(map(varkind, block.inputargs),
                                         args_gv)
        seen_blocks[block] = label
        varmap = dict(zip(block.inputargs, args_gv))

        if not block.exits:
            [retvar] = block.inputargs
            builder.finish_and_return(sigtoken, varmap[retvar])
            continue

        for op in block.operations:
            # XXX only supports some operations for now
            if op.opname == 'malloc':
                token = rgenop.allocToken(op.args[0].value)
                gv_result = builder.genop_malloc_fixedsize(token)
            elif op.opname == 'getfield':
                token = rgenop.fieldToken(op.args[0].concretetype.TO,
                                          op.args[1].value)
                gv_result = builder.genop_getfield(token,
                                                   var2gv(op.args[0]))
            elif op.opname == 'setfield':
                token = rgenop.fieldToken(op.args[0].concretetype.TO,
                                          op.args[1].value)
                gv_result = builder.genop_setfield(token,
                                                   var2gv(op.args[0]),
                                                   var2gv(op.args[2]))
            elif op.opname == 'malloc_varsize':
                token = rgenop.varsizeAllocToken(op.args[0].value)
                gv_result = builder.genop_malloc_varsize(token,
                                                         var2gv(op.args[1]))
            elif op.opname == 'getarrayitem':
                token = rgenop.arrayToken(op.args[0].concretetype.TO)
                gv_result = builder.genop_getarrayitem(token,
                                                       var2gv(op.args[0]),
                                                       var2gv(op.args[1]))
            elif op.opname == 'setarrayitem':
                token = rgenop.arrayToken(op.args[0].concretetype.TO)
                gv_result = builder.genop_setarrayitem(token,
                                                       var2gv(op.args[0]),
                                                       var2gv(op.args[1]),
                                                       var2gv(op.args[2]))
            elif op.opname == 'same_as':
                token = rgenop.kindToken(op.args[0])
                gv_result = builder.genop_same_as(token, var2gv(op.args[0]))
            elif len(op.args) == 1:
                gv_result = builder.genop1(op.opname, var2gv(op.args[0]))
            elif len(op.args) == 2:
                gv_result = builder.genop2(op.opname, var2gv(op.args[0]),
                                                      var2gv(op.args[1]))
            else:
                raise NotImplementedError(op.opname)
            varmap[op.result] = gv_result

        if block.exitswitch is not None:
            raise NotImplementedError("XXX exitswitch")
        else:
            [link] = block.exits
            args_gv = [var2gv(v) for v in link.args]
            pending_blocks[link.target] = builder, args_gv

    builder.end()
    return gv_entrypoint
           
