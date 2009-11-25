from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'cx_Oracle'

    interpleveldefs = {
        'connect': 'interp_connect.W_Connection',
        'UNICODE': 'interp_variable.VT_NationalCharString',
        'NUMBER': 'interp_variable.VT_Float',
        'STRING': 'interp_variable.VT_String',
        'DATETIME': 'interp_variable.VT_DateTime',
        'DATE': 'interp_variable.VT_Date',
        'TIMESTAMP': 'interp_variable.VT_Timestamp',
        'INTERVAL': 'interp_variable.VT_Interval',
        'BINARY': 'interp_variable.VT_Binary',
        'LONG_STRING': 'interp_variable.VT_LongString',
        'LONG_BINARY': 'interp_variable.VT_LongBinary',
        'FIXED_CHAR': 'interp_variable.VT_FixedChar',
        'CURSOR': 'interp_variable.VT_Cursor',
        'BLOB': 'interp_variable.VT_BLOB',
        'Variable': 'interp_variable.W_Variable',
        'Timestamp': 'interp_error.get(space).w_DateTimeType',
        'Date': 'interp_error.get(space).w_DateType',
    }

    appleveldefs = {
        'version': 'app_oracle.version',
        'makedsn': 'app_oracle.makedsn',
        'TimestampFromTicks': 'app_oracle.TimestampFromTicks',
    }
    for name in """DataError DatabaseError Error IntegrityError InterfaceError
                   InternalError NotSupportedError OperationalError
                   ProgrammingError Warning""".split():
        appleveldefs[name] = "app_oracle.%s" % (name,)

