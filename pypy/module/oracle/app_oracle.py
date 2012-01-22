version = '5.0.0'
paramstyle = 'named'

class Warning(StandardError):
    pass

class Error(StandardError):
    pass

class InterfaceError(Error):
    pass

class DatabaseError(Error):
    pass

class DataError(DatabaseError):
    pass

class OperationalError(DatabaseError):
    pass

class IntegrityError(DatabaseError):
    pass

class InternalError(DatabaseError):
    pass

class ProgrammingError(DatabaseError):
    pass

class NotSupportedError(DatabaseError):
    pass


def makedsn(host, port, sid):
    return ("(DESCRIPTION=(ADDRESS_LIST=(ADDRESS="
            "(PROTOCOL=TCP)(HOST=%s)(PORT=%s)))"
            "(CONNECT_DATA=(SID=%s)))" % (host, port, sid))

def TimestampFromTicks(*args):
    import datetime
    return datetime.datetime.fromtimestamp(*args)
