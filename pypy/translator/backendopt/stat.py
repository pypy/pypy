from pypy.translator.simplify import get_graph

def get_statistics(graph, translator):
    seen_graphs = {}
    stack = [graph]
    num_graphs = 0
    num_blocks = 0
    num_ops = 0
    while stack:
        graph = stack.pop()
        if graph in seen_graphs:
            continue
        seen_graphs[graph] = True
        num_graphs += 1
        for block in graph.iterblocks():
            num_blocks += 1
            for op in block.operations:
                if op.opname == "direct_call":
                    called_graph = get_graph(op.args[0], translator)
                    if called_graph is not None:
                        stack.append(called_graph)
                elif op.opname == "indirect_call":
                    called_graphs = op.args[-1].value
                    if called_graphs is not None:
                        stack.extend(called_graphs)
                num_ops += 1
    return num_graphs, num_blocks, num_ops

def print_statistics(graph, translator):
    num_graphs, num_blocks, num_ops = get_statistics(graph, translator)
    print ("Statistics:\nnumber of graphs %s\n"
           "number of blocks %s\n"
           "number of operations %s\n") % (num_graphs, num_blocks, num_ops)
