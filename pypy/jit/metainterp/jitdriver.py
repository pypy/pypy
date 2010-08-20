

class JitDriverStaticData:
    """There is one instance of this class per JitDriver used in the program.
    """
    # This is just a container with the following attributes (... set by):
    #    self.jitdriver         ... pypy.jit.metainterp.warmspot
    #    self.portal_graph      ... pypy.jit.metainterp.warmspot
    #    self.portal_runner_ptr ... pypy.jit.metainterp.warmspot
    #    self.portal_runner_adr ... pypy.jit.metainterp.warmspot
    #    self.num_green_args    ... pypy.jit.metainterp.warmspot
    #    self.result_type       ... pypy.jit.metainterp.warmspot
    #    self.virtualizable_info... pypy.jit.metainterp.warmspot
    #    self.warmstate         ... pypy.jit.metainterp.warmspot
    #    self.handle_jitexc_from_bh pypy.jit.metainterp.warmspot
    #    self.index             ... pypy.jit.codewriter.call
    #    self.mainjitcode       ... pypy.jit.codewriter.call

    # These attributes are read by the backend in CALL_ASSEMBLER:
    #    self.assembler_helper_adr
    #    self.index_of_virtualizable
    #    self.vable_token_descr

    # warmspot sets extra attributes starting with '_' for its own use.

    def _freeze_(self):
        return True
