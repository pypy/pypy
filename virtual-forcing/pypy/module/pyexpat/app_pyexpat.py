class ExpatError(Exception):
    def __init__(self, msg, code, lineno, colno):
        Exception.__init__(self, msg)
        self.code = code
        self.lineno = lineno
        self.colno = colno
