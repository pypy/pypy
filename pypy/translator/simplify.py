"""
generate Pyrex files from the flowmodel. 

"""
import autopath
from pypy.tool import test
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.flowmodel import *


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
        victimlist = []
        entrymap = graph.mkentrymap()
        for node in graph.flatten():
            if node in victimlist:
                continue
            if isinstance(node, BasicBlock) and len(node.operations) == 0:
                prevnodes = entrymap[node]
                if len(prevnodes) != 1:
                    continue
                prevbranch = prevnodes[0]
                nextbranch = node.branch
                if not isinstance(prevbranch, Branch) or isinstance(nextbranch, EndBranch):
                   continue 
                # 
                if len(prevbranch.args) > len(nextbranch.args):
                    prevbranch.args = prevbranch.args[:len(nextbranch.args)]
                else:
                    prevbranch.args.extend(nextbranch.args[len(prevbranch.args):])
                prevbranch.target = nextbranch.target
                targetentrylist = entrymap[nextbranch.target]
                targetentrylist.remove(nextbranch)
                targetentrylist.append(prevbranch)
                victimlist.append(node)
                victimlist.append(nextbranch)
        victims = len(victimlist) > 0
    return graph

