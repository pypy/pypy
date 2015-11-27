from rpython.flowspace.model import mkentrymap
import collections


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
        """Return the (default) out_state for 'block' used to
        initialize all blocks before starting the analysis."""
        raise NotImplementedError("abstract base class")

    def join_operation(self, inputargs, preds_outs, links_to_preds):
        """Joins all preds_outs to generate a new in_state for the
        current block.
        'inputargs' is the list of input arguments to the block
        'preds_outs': is the list of out_state for each preds
        'links_to_preds': is the list of links to the preds
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
        links_to_preds = []
        for link in entrymap[block]:
            pred = link.prevblock
            if pred is None:
                # block == startblock
                in_states[block] = self.entry_state(block)
                return True
            preds_outs.append(out_states[pred])
            links_to_preds.append(link)
        # join predecessor out_states for updated in_state:
        block_in = self.join_operation(inputargs, preds_outs, links_to_preds)
        #
        if block not in in_states or block_in != in_states[block]:
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
        blocks = set(graph.iterblocks())
        for block in blocks:
            out_states[block] = self.initialize_block(block)

        #
        # iterate:
        # todo: ordered set? reverse post-order?
        blocks.remove(graph.startblock)
        pending = collections.deque(blocks)
        pending.append(graph.startblock)
        while pending:
            block = pending.pop()
            if self._update_in_state_of(block, entrymap, in_states, out_states):
                block_out = self.transfer_function(block, in_states[block])
                if block_out != out_states[block]:
                    out_states[block] = block_out
                    for link in block.exits:
                        if link.target not in pending:
                            pending.appendleft(link.target)
        #
        return in_states, out_states
