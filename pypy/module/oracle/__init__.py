from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    applevel_name = 'cx_Oracle'

    interpleveldefs = {
        'connect': 'interp_connect.W_Connection',
        'Connection': 'interp_connect.W_Connection',
        'NUMBER': 'interp_variable.VT_Float',
        'STRING': 'interp_variable.VT_String',
        'UNICODE': 'interp_variable.VT_NationalCharString',
        'DATETIME': 'interp_variable.VT_DateTime',
        'DATE': 'interp_variable.VT_Date',
        'TIMESTAMP': 'interp_variable.VT_Timestamp',
        'INTERVAL': 'interp_variable.VT_Interval',
        'BINARY': 'interp_variable.VT_Binary',
        'LONG_STRING': 'interp_variable.VT_LongString',
        'LONG_BINARY': 'interp_variable.VT_LongBinary',
        'FIXED_CHAR': 'interp_variable.VT_FixedChar',
        'FIXED_UNICODE': 'interp_variable.VT_FixedNationalChar',
        'CURSOR': 'interp_variable.VT_Cursor',
        'BLOB': 'interp_variable.VT_BLOB',
        'CLOB': 'interp_variable.VT_CLOB',
        'OBJECT': 'interp_variable.VT_Object',
        'Variable': 'interp_variable.W_Variable',
        'SessionPool': 'interp_pool.W_SessionPool',
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

    def startup(self, space):
        from pypy.module.oracle.interp_error import get
        state = get(space)
        state.startup(space)
        (state.w_DecimalType,
         state.w_DateTimeType, state.w_DateType, state.w_TimedeltaType,
         ) = space.fixedview(space.appexec([], """():
             import decimal, datetime
             return (decimal.Decimal,
                     datetime.datetime, datetime.date, datetime.timedelta)
        """))
        space.setattr(space.wrap(self),
                      space.wrap("Timestamp"), state.w_DateTimeType)
        space.setattr(space.wrap(self),
                      space.wrap("Date"), state.w_DateType)
