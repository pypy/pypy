# ______________________________________________________________________
"""Module automata

THIS FILE WAS COPIED FROM pypy/module/parser/pytokenize.py AND ADAPTED
TO BE ANNOTABLE (Mainly made the DFA's __init__ accept two lists
instead of a unique nested one)

$Id: automata.py,v 1.2 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________
# Module level definitions

# PYPY Modification: removed the EMPTY class as it's not needed here


# PYPY Modification: we don't need a particuliar DEFAULT class here
#                    a simple None works fine.
#                    (Having a DefaultClass inheriting from str makes
#                     the annotator crash)
DEFAULT = "\00default" # XXX hack, the rtyper does not support dict of with str|None keys
                       # anyway using dicts doesn't seem the best final way to store these char indexed tables
# PYPY Modification : removed all automata functions (any, maybe,
#                     newArcPair, etc.)

class DFA:
    # ____________________________________________________________
    def __init__(self, states, accepts, start = 0):
        self.states = states
        self.accepts = accepts
        self.start = start

    # ____________________________________________________________
    def recognize (self, inVec, pos = 0): # greedy = True
        crntState = self.start
        lastAccept = False
        i = pos
        for i in range(pos, len(inVec)):
            item = inVec[i]
            # arcMap, accept = self.states[crntState]
            arcMap = self.states[crntState]
            accept = self.accepts[crntState]
            if item in arcMap:
                crntState = arcMap[item]
            elif DEFAULT in arcMap:
                crntState = arcMap[DEFAULT]
            elif accept:
                return i
            elif lastAccept:
                # This is now needed b/c of exception cases where there are
                # transitions to dead states
                return i - 1
            else:
                return -1
            lastAccept = accept
        # if self.states[crntState][1]:
        if self.accepts[crntState]:
            return i + 1
        elif lastAccept:
            return i
        else:
            return -1

# ______________________________________________________________________

class NonGreedyDFA (DFA):
    def recognize (self, inVec, pos = 0):
        crntState = self.start
        i = pos
        for item in inVec[pos:]:
            # arcMap, accept = self.states[crntState]
            arcMap = self.states[crntState]
            accept = self.accepts[crntState]
            if accept:
                return i
            elif item in arcMap:
                crntState = arcMap[item]
            elif DEFAULT in arcMap:
                crntState = arcMap[DEFAULT]
            else:
                return -1
            i += 1
        # if self.states[crntState][1]:
        if self.accepts[crntState]:
            return i
        else:
            return -1

# ______________________________________________________________________
# End of automata.py
