"""
generate Pyrex files from the flowmodel. 

"""
from pypy.objspace.flow.model import *

# debug
from pypy.translator.genpyrex import GenPyrex


def eliminate_empty_blocks(graph):
    """Eliminate basic blocks that do not contain any operations.
    When this happens, we need to replace the preceeding link with the
    following link.  Arguments of the links should be updated."""
    def visit(link):
        if isinstance(link, Link):
            while not link.target.operations and len(link.target.exits) == 1:
                block1 = link.target
                exit = block1.exits[0]
                outputargs = []
                for v in exit.args:
                    if isinstance(v, Variable):
                        # this variable is valid in the context of block1
                        # but it must come from 'link'
                        i = block1.inputargs.index(v)
                        v = link.args[i]
                    outputargs.append(v)
                link.args = outputargs
                link.target = exit.target
                # the while loop above will simplify recursively the new link
    traverse(visit, graph)

def xxx_not_done_yet():
    """
    2. Unconditional links into basic blocks that have a single entry point.
       At this point, we can append all the operations of the following basic
       block to the preceeding basic block (but renaming variables with the
       appropriate arguments.) 
    """
    nodelist = graph.flatten()
    entrymap = graph.mkentrymap()
    victims = True
    while victims:
        victims = False
        entrymap = graph.mkentrymap()
        for node in graph.flatten():
            if isinstance(node, BasicBlock) and len(node.operations) == 0:
                prevnodes = entrymap[node]
                if len(prevnodes) != 1:
                    continue
                prevbranch = prevnodes[0]
                nextbranch = node.branch
                if not isinstance(prevbranch, Branch):
                   continue 
                if isinstance(nextbranch, EndBranch):
                    var = nextbranch.returnvalue
                    prevprevnode = entrymap[prevbranch]
                    assert len(prevprevnode) == 1 
                    if var in node.input_args:
                        i = node.input_args.index(var)
                        nextbranch.returnvalue = prevbranch.args[i]
                    prevprevnode[0].replace_branch(prevbranch, nextbranch)
                elif isinstance(nextbranch, ConditionalBranch):
                    continue
                else:
                    # renaming ... (figure it out yourself :-)
                    if len(prevbranch.args) > len(nextbranch.args):
                        prevbranch.args = prevbranch.args[:len(nextbranch.args)]
                    else:
                        prevbranch.args.extend(nextbranch.args[len(prevbranch.args):])
                    prevbranch.target = nextbranch.target
                #print "eliminated", node, nextbranch
                victims = True
                # restart the elimination-for loop cleanly
                break
    return graph

def simplify_graph(graph):
    """apply all the existing optimisations to the graph"""
    eliminate_empty_blocks(graph)
    return graph
