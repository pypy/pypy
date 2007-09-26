
class StructError(Exception):
    "Interp-level error that gets mapped to an app-level struct.error."

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
