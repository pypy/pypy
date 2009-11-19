from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'cx_Oracle'

    interpleveldefs = {
        'connect': 'interp_connect.W_Connection',
        'UNICODE': 'interp_variable.VT_NationalCharString',
        'NUMBER': 'interp_variable.VT_Float',
        'STRING': 'interp_variable.VT_String',
        'DATETIME': 'interp_variable.VT_DateTime',
        'BINARY': 'interp_variable.VT_Binary',
        'LONG_STRING': 'interp_variable.VT_LongString',
        'LONG_BINARY': 'interp_variable.VT_LongBinary',
        'FIXED_CHAR': 'interp_variable.VT_FixedChar',
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

