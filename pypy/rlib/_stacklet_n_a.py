

class StackletGcRootFinder:

    @staticmethod
    def stack_protected_call(callback):
        return callback()

    @staticmethod
    def set_handle_on_most_recent(h):
        pass
