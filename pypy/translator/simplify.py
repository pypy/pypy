"""
generate Pyrex files from the flowmodel. 

"""
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.flowmodel import *

# debug
from pypy.translator.genpyrex import GenPyrex


def eliminate_empty_blocks(graph):
    """simplify_vars()
    Things we know we can remove:
    1. Basic blocks that do not contain any operations.
       When this happens, we need to replace the preceeding branch with the
       following branch.  Arguments of the following branch should be
       overwritten with the arguments of the preceeding branch, but any
       additional arguments should be kept.
    2. Branches into basic blocks that have a single entry point.
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

