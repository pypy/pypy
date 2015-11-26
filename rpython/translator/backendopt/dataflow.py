from rpython.flowspace.model import mkentrymap



class AbstractDataFlowAnalysis(object):

    def transfer_function(self, block, in_state):
        """Returns a new out_state after flowing the 'in_state'
        through 'block'"""
        raise NotImplementedError("abstract base class")

    def entry_state(self, block):
        """Returns the initial state for the 'block' with which
        the analysis starts.
            Forward: start block
            Backwards: return block"""
        raise NotImplementedError("abstract base class")

    def initialize_block(self, block):
        """Return the (default) in_state, out_state for 'block'
        used to initialize all blocks before starting the analysis"""
        raise NotImplementedError("abstract base class")

    def join_operation(self, preds_outs, inputargs, pred_out_args):
        """Joins all preds_outs to generate a new in_state for the
        current block.
        'inputargs' is the list of input arguments to the block;
        'pred_out_args' is a list of lists of arguments given to
            the link by a certain predecessor.
        """
        raise NotImplementedError("abstract base class")

    def calculate(self, graph, entrymap=None):
        """Run the analysis on 'graph' and return the in and
        out states as two {block:state} dicts"""
        raise NotImplementedError("abstract base class")





class AbstractForwardDataFlowAnalysis(AbstractDataFlowAnalysis):

    def _update_successor_blocks(self, block, out_state, entrymap,
                                 in_states, out_states):
        if out_states[block] == out_state:
            return set()
        out_states[block] = out_state
        #
        # update all successors
        to_do = set()
        for link in block.exits:
            succ = link.target
            # collect all out_states of predecessors:
            preds_outs = []
            inputargs = succ.inputargs
            preds_out_args = [[] for _ in inputargs]
            for link in entrymap[succ]:
                preds_outs.append(out_states[link.prevblock])
                for i in range(len(inputargs)):
                    preds_out_args[i].append(link.args[i])
            block_in = self.join_operation(preds_outs, inputargs, preds_out_args)
            if block_in != in_states[succ]:
                # in_state changed
                to_do.add(succ)
                in_states[succ] = block_in
        return to_do


    def calculate(self, graph, entrymap=None):
        if entrymap is None:
            entrymap = mkentrymap(graph)
        in_states = {}
        out_states = {}
        #
        for block in graph.iterblocks():
            in_states[block], out_states[block] = self.initialize_block(block)
        in_states[graph.startblock] = self.entry_state(graph.startblock)
        #
        # iterate:
        pending = {graph.startblock,}
        while pending:
            block = pending.pop()
            block_out = self.transfer_function(block, in_states[block])
            pending |= self._update_successor_blocks(
                block, block_out, entrymap, in_states, out_states)
        #
        return in_states, out_states
