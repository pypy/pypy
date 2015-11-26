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
        used to initialize all blocks before starting the analysis."""
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
        # add all successors
        return {link.target for link in block.exits}

    def _update_in_state_of(self, block, entrymap, in_states, out_states):
        # collect all out_states of predecessors:
        preds_outs = []
        inputargs = block.inputargs
        preds_out_args = [[] for _ in inputargs]
        for link in entrymap[block]:
            pred = link.prevblock
            if pred is None:
                # block == startblock
                return True
            preds_outs.append(out_states[pred])
            for i in range(len(inputargs)):
                preds_out_args[i].append(link.args[i])
        # join predecessor out_states for updated in_state:
        block_in = self.join_operation(preds_outs, inputargs, preds_out_args)
        if block_in != in_states[block]:
            # in_state changed
            in_states[block] = block_in
            return True
        return False



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
            if self._update_in_state_of(block, entrymap, in_states, out_states):
                block_out = self.transfer_function(block, in_states[block])
                if block_out != out_states[block]:
                    out_states[block] = block_out
                    pending |= {link.target for link in block.exits}
        #
        return in_states, out_states
