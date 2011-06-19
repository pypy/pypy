from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.conftest import option
import sys, os
import py

oracle_home = getattr(option, 'oracle_home',
                      os.environ.get("ORACLE_HOME"))
if oracle_home:
    ORACLE_HOME = py.path.local(oracle_home)
else:
    raise ImportError(
        "Please set ORACLE_HOME to the root of an Oracle client installation")

if sys.platform == 'win32':
    include_dirs = [str(ORACLE_HOME.join('OCI', 'include'))]
    libraries = ['oci']
    library_dirs = [str(ORACLE_HOME.join('OCI', 'lib', 'MSVC'))]
else:
    include_dirs = [str(ORACLE_HOME.join('sdk', 'include')),   # Oracle 11
                    str(ORACLE_HOME.join('rdbms', 'demo')),    # Oracle 9
                    str(ORACLE_HOME.join('rdbms', 'public')),  # Oracle 9
                    ]
    libraries = ['clntsh']
    library_dirs = [str(ORACLE_HOME.join('lib'))]

eci = ExternalCompilationInfo(
    post_include_bits = [
        # One single string, to be sure it will
        # be rendered in this order
        '#include <oci.h>\n' +
        'typedef boolean oci_boolean;\n' +
        '#undef boolean'
        ],
    include_dirs = include_dirs,
    libraries = libraries,
    library_dirs = library_dirs,
    )


class CConfig:
    _compilation_info_ = eci

    ub1 = platform.SimpleType('ub1', rffi.UINT)
    sb1 = platform.SimpleType('sb1', rffi.INT)
    ub2 = platform.SimpleType('ub2', rffi.UINT)
    sb2 = platform.SimpleType('sb2', rffi.INT)
    ub4 = platform.SimpleType('ub4', rffi.UINT)
    sb4 = platform.SimpleType('sb4', rffi.INT)
    sword = platform.SimpleType('sword', rffi.INT)
    uword = platform.SimpleType('uword', rffi.UINT)
    boolean = platform.SimpleType('oci_boolean', rffi.UINT)
    OCIDuration = platform.SimpleType('OCIDuration', rffi.UINT)
    OCIInd = platform.SimpleType('OCIInd', rffi.INT)
    OCIPinOpt = platform.SimpleType('OCIPinOpt', rffi.INT)
    OCILockOpt = platform.SimpleType('OCILockOpt', rffi.INT)
    OCITypeCode = platform.SimpleType('OCITypeCode', rffi.UINT)

    OCINumber = platform.Struct('OCINumber', [])
    OCITime   = platform.Struct('OCITime',
                                [('OCITimeHH', rffi.INT),
                                 ('OCITimeMI', rffi.INT),
                                 ('OCITimeSS', rffi.INT),
                                 ])
    OCIDate   = platform.Struct('OCIDate',
                                [('OCIDateYYYY', rffi.INT),
                                 ('OCIDateMM', rffi.INT),
                                 ('OCIDateDD', rffi.INT),
                                 ('OCIDateTime', OCITime),
                                 ])

    defines = '''
    OCI_ATTR_SERVER OCI_ATTR_SESSION OCI_ATTR_USERNAME OCI_ATTR_PASSWORD
    OCI_ATTR_STMT_TYPE OCI_ATTR_PARAM OCI_ATTR_PARAM_COUNT OCI_ATTR_ROW_COUNT
    OCI_ATTR_NAME OCI_ATTR_INTERNAL_NAME OCI_ATTR_EXTERNAL_NAME
    OCI_ATTR_SCALE OCI_ATTR_PRECISION OCI_ATTR_IS_NULL
    OCI_ATTR_DATA_SIZE OCI_ATTR_DATA_TYPE OCI_ATTR_REF_TDO
    OCI_ATTR_SCHEMA_NAME OCI_ATTR_TYPE_NAME OCI_ATTR_TYPECODE
    OCI_ATTR_NUM_TYPE_ATTRS OCI_ATTR_LIST_TYPE_ATTRS
    OCI_ATTR_COLLECTION_ELEMENT OCI_ATTR_MAXDATA_SIZE
    OCI_ATTR_CHARSET_FORM OCI_ATTR_CHARSET_ID OCI_ATTR_ENV_CHARSET_ID
    OCI_ATTR_PARSE_ERROR_OFFSET
    OCI_ATTR_SPOOL_OPEN_COUNT OCI_ATTR_SPOOL_BUSY_COUNT OCI_ATTR_SPOOL_TIMEOUT
    OCI_ATTR_SPOOL_GETMODE OCI_ATTR_PURITY OCI_ATTR_CONNECTION_CLASS
    OCI_ATTR_PURITY_DEFAULT
    SQLT_CHR SQLT_LNG SQLT_AFC SQLT_RDD SQLT_BIN SQLT_LBI SQLT_LVC SQLT_LVB
    SQLT_BFLOAT SQLT_IBFLOAT SQLT_BDOUBLE SQLT_IBDOUBLE
    SQLT_NUM SQLT_VNU SQLT_DAT SQLT_ODT SQLT_DATE SQLT_TIMESTAMP
    SQLT_TIMESTAMP_TZ SQLT_TIMESTAMP_LTZ SQLT_INTERVAL_DS
    SQLT_CLOB SQLT_CLOB SQLT_BLOB SQLT_BFILE SQLT_RSET SQLT_NTY
    '''.split()

    constants = '''
    OCI_DEFAULT OCI_OBJECT OCI_THREADED OCI_EVENTS
    OCI_SUCCESS OCI_SUCCESS_WITH_INFO OCI_INVALID_HANDLE OCI_NO_DATA
    OCI_HTYPE_ERROR OCI_HTYPE_SVCCTX OCI_HTYPE_SERVER OCI_HTYPE_SESSION
    OCI_HTYPE_STMT OCI_HTYPE_DESCRIBE OCI_HTYPE_BIND OCI_HTYPE_DEFINE
    OCI_HTYPE_ENV OCI_HTYPE_SPOOL OCI_HTYPE_AUTHINFO 
    OCI_DTYPE_PARAM OCI_DTYPE_TIMESTAMP OCI_DTYPE_INTERVAL_DS OCI_DTYPE_LOB
    OCI_CRED_RDBMS OCI_CRED_EXT OCI_SPOOL_ATTRVAL_NOWAIT
    OCI_NTV_SYNTAX OCI_COMMIT_ON_SUCCESS
    OCI_FETCH_NEXT
    OCI_IND_NULL OCI_IND_NOTNULL
    OCI_PIN_ANY OCI_LOCK_NONE OCI_OBJECTFREE_FORCE
    OCI_OTYPE_PTR OCI_PTYPE_TYPE
    OCI_STMT_SELECT OCI_STMT_CREATE OCI_STMT_DROP OCI_STMT_ALTER
    OCI_STMT_INSERT OCI_STMT_DELETE OCI_STMT_UPDATE
    SQLCS_IMPLICIT SQLCS_NCHAR
    OCI_TEMP_CLOB OCI_TEMP_BLOB OCI_DURATION_SESSION OCI_ONE_PIECE
    OCI_NUMBER_SIGNED
    OCI_TYPECODE_CHAR OCI_TYPECODE_VARCHAR OCI_TYPECODE_VARCHAR2
    OCI_TYPECODE_NUMBER OCI_TYPECODE_DATE OCI_TYPECODE_TIMESTAMP
    OCI_TYPECODE_NAMEDCOLLECTION OCI_TYPECODE_OBJECT
    OCI_NLS_MAXBUFSZ OCI_NLS_CS_ORA_TO_IANA OCI_UTF16ID
    OCI_SPC_STMTCACHE OCI_SPC_HOMOGENEOUS
    OCI_SESSGET_SPOOL OCI_SESSGET_CREDPROXY OCI_SESSGET_STMTCACHE
    OCI_SESSGET_CREDEXT OCI_SESSRLS_DROPSESS
    '''.split()

    for c in defines:
        locals()[c] = platform.DefinedConstantInteger(c)
    for c in constants:
        locals()[c] = platform.ConstantInteger(c)

    INT_MAX = platform.ConstantInteger('INT_MAX')


globals().update(platform.configure(CConfig))

OCI_IND_NOTNULL = rffi.cast(rffi.SHORT, OCI_IND_NOTNULL)
OCI_IND_NULL = rffi.cast(rffi.SHORT, OCI_IND_NULL)

# Various pointers to incomplete structures
OCISvcCtx = rffi.VOIDP
OCIEnv = rffi.VOIDP
OCIError = rffi.VOIDP
OCIServer = rffi.VOIDP
OCISession = rffi.VOIDP
OCIAuthInfo = rffi.VOIDP
OCISPool = rffi.VOIDP
OCIStmt = rffi.VOIDP
OCIParam = rffi.VOIDP
OCIBind = rffi.VOIDP
OCIDefine = rffi.VOIDP
OCIDescribe = rffi.VOIDP
OCISnapshot = rffi.VOIDP
OCIString = rffi.VOIDP
OCIDateTime = rffi.VOIDP
OCIInterval = rffi.VOIDP
OCILobLocator = rffi.VOIDP
OCIRef = rffi.VOIDP
OCIType = rffi.VOIDP
OCIComplexObject = rffi.VOIDP
OCIColl = rffi.VOIDP
OCIIter = rffi.VOIDP

Ptr = rffi.CArrayPtr
void = lltype.Void
dvoidp = rffi.VOIDP
dvoidpp = rffi.VOIDPP
size_t = rffi.SIZE_T
oratext = rffi.CCHARP

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

# Connect, Authorize, and Initialize Functions

OCIEnvNlsCreate = external(
    'OCIEnvNlsCreate',
    [rffi.CArrayPtr(OCIEnv), # envhpp
     ub4,                    # mode
     dvoidp,                 # ctxp
     dvoidp,                 # malocfp
     dvoidp,                 # ralocfp
     dvoidp,                 # mfreefp
     size_t,             # xtramemsz
     dvoidpp,            # usermempp
     ub2,                # charset
     ub2],               # ncharset
    sword)

OCIServerAttach = external(
    'OCIServerAttach',
    [OCIServer,          # srvhp
     OCIError,           # errhp
     oratext,            # dblink
     sb4,                # dblink_len
     ub4],               # mode
    sword)

OCIServerDetach = external(
    'OCIServerDetach',
    [OCIServer, OCIError, ub4],
    sword)

OCISessionBegin = external(
    'OCISessionBegin',
    [OCISvcCtx, OCIError, OCISession, ub4, ub4],
    sword)

OCISessionEnd = external(
    'OCISessionEnd',
    [OCISvcCtx,    # svchp
     OCIError,     # errhp
     OCISession,   # usrhp
     ub4],         # mode
    sword)

OCISessionGet = external(
    'OCISessionGet',
    [OCIEnv,           # envhp
     OCIError,         # errhp
     Ptr(OCISvcCtx),   # svchp
     OCIAuthInfo,      # authInfop,
     oratext,          # dbName
     ub4,              # dbName_len
     oratext,          # tagInfo
     ub4,              # tagInfo_len
     Ptr(oratext),     # retTagInfo
     Ptr(ub4),         # retTagInfo_len
     Ptr(boolean),     # found
     ub4],             # mode
    sword)

OCISessionPoolCreate = external(
    'OCISessionPoolCreate',
    [OCISvcCtx,    # svchp
     OCIError,     # errhp
     OCISPool,     # spoolhp
     Ptr(oratext), # poolName
     Ptr(ub4),     # poolNameLen
     oratext,      # connStr
     ub4,          # connStrLen
     ub4,          # sessMin
     ub4,          # sessMax
     ub4,          # sessIncr
     oratext,      # userid
     ub4,          # useridLen
     oratext,      # password
     ub4,          # passwordLen
     ub4],         # mode
    sword)

OCISessionRelease = external(
    'OCISessionRelease',
    [OCISvcCtx,    # svchp
     OCIError,     # errhp
     oratext,      # tag
     ub4,          # tag_len
     ub4],         # mode
    sword)

# Handle and Descriptor Functions

OCIAttrGet = external(
    'OCIAttrGet',
    [dvoidp,    # trgthndlp
     ub4,       # trghndltyp
     dvoidp,    # attributep
     Ptr(ub4),  # sizep
     ub4,       # attrtype
     OCIError], # errhp
    sword)

OCIAttrSet = external(
    'OCIAttrSet',
    [dvoidp,    # trgthndlp
     ub4,       # trghndltyp
     dvoidp,    # attributep
     ub4,       # size
     ub4,       # attrtype
     OCIError], # errhp
    sword)

OCIDescriptorAlloc = external(
    'OCIDescriptorAlloc',
    [dvoidp,    # parenth
     dvoidpp,   # descpp
     ub4,       # type
     size_t,    # xtramem_sz
     dvoidp],   # usrmempp
    sword)

OCIDescriptorFree = external(
    'OCIDescriptorFree',
    [dvoidp,    # descp
     ub4],      # type
    sword)

OCIHandleAlloc = external(
    'OCIHandleAlloc',
    [dvoidp,      # parenth
     dvoidpp,     # handlepp
     ub4,         # type
     size_t,      # xtramem_sz
     dvoidpp],    # usermempp
    sword)

OCIHandleFree = external(
    'OCIHandleFree',
    [dvoidp,      # handlp
     ub4],        # type
    sword)

OCIParamGet = external(
    'OCIParamGet',
    [dvoidp,      # hndlp
     ub4,         # htype
     OCIError,    # errhp
     dvoidpp,     # parmdpp
     ub4],        # pos
    sword)

# Bind, Define, and Describe Functions

OCIBindByName = external(
    'OCIBindByName',
    [OCIStmt,      # stmtp
     Ptr(OCIBind), # bindpp
     OCIError,     # errhp
     oratext,      # placeholder
     sb4,          # placeh_len
     dvoidp,       # valuep
     sb4,          # value_sz
     ub2,          # dty
     dvoidp,       # indp
     Ptr(ub2),     # alenp
     Ptr(ub2),     # rcodep
     ub4,          # maxarr_len
     Ptr(ub4),     # curelep
     ub4],         # mode
    sword)

OCIBindByPos = external(
    'OCIBindByPos',
    [OCIStmt,      # stmtp
     Ptr(OCIBind), # bindpp
     OCIError,     # errhp
     ub4,          # position
     dvoidp,       # valuep
     sb4,          # value_sz
     ub2,          # dty
     dvoidp,       # indp
     Ptr(ub2),     # alenp
     Ptr(ub2),     # rcodep
     ub4,          # maxarr_len
     Ptr(ub4),     # curelep
     ub4],         # mode
    sword)

OCIDefineByPos = external(
    'OCIDefineByPos',
    [OCIStmt,        # stmtp
     Ptr(OCIDefine), # defnpp
     OCIError,       # errhp
     ub4,            # position
     dvoidp,         # valuep
     sb4,            # value_sz
     ub2,            # dty
     dvoidp,         # indp
     Ptr(ub2),       # rlenp
     Ptr(ub2),       # rcodep
     ub4],           # mode
    sword)

OCIDefineObject = external(
    'OCIDefineObject',
    [OCIDefine,      # defnp
     OCIError,       # errhp
     OCIType,        # type
     dvoidpp,        # pgvpp
     ub4,            # pvszsp
     dvoidpp,        # indpp
     ub4],           # indszp
    sword)

OCIDescribeAny = external(
    'OCIDescribeAny',
    [OCISvcCtx,      # svchp
     OCIError,       # errhp
     dvoidp,         # objptr
     ub4,            # objptr_len
     ub1,            # objptr_typ
     ub1,            # info_level
     ub1,            # objtyp
     OCIDescribe],   # dschp
    sword)

OCIStmtGetBindInfo = external(
    'OCIStmtGetBindInfo',
    [OCIStmt,        # stmtp
     OCIError,       # errhp
     ub4,            # size
     ub4,            # startloc
     Ptr(sb4),       # found
     Ptr(oratext),   # bvnp
     Ptr(ub1),       # bvnl
     Ptr(oratext),   # invp
     Ptr(ub1),       # inpl
     Ptr(ub1),       # dupl
     Ptr(OCIBind)],  # hndl
    sword)

# Statement Functions

OCIStmtExecute = external(
    'OCIStmtExecute',
    [OCISvcCtx,   # svchp
     OCIStmt,     # stmtp
     OCIError,    # errhp
     ub4,         # iters
     ub4,         # rowoff
     OCISnapshot, # snap_in
     OCISnapshot, # snap_out
     ub4],        # mode
    sword)

OCIStmtFetch = external(
    'OCIStmtFetch',
    [OCIStmt,     # stmtp
     OCIError,    # errhp
     ub4,         # nrows
     ub2,         # orientation
     ub4],        # mode
    sword)

OCIStmtPrepare2 = external(
    'OCIStmtPrepare2',
    [OCISvcCtx,    # svchp
     Ptr(OCIStmt), # stmthp
     OCIError,     # errhp
     oratext,      # stmttext
     ub4,          # stmt_len
     oratext,      # key
     ub4,          # keylen
     ub4,          # language
     ub4],         # mode
    sword)

OCIStmtRelease = external(
    'OCIStmtRelease',
    [OCIStmt,      # stmthp
     OCIError,     # errp
     oratext,      # key
     ub4,          # keylen
     ub4],         # mode
    sword)

# LOB Functions

OCILobCreateTemporary = external(
    'OCILobCreateTemporary',
    [OCISvcCtx,     # svchp
     OCIError,      # errhp
     OCILobLocator, # locp
     ub2,           # csid
     ub1,           # csfrm
     ub1,           # lobtype
     boolean,       # cache
     OCIDuration],  # duration
    sword)

OCILobGetLength = external(
    'OCILobGetLength',
    [OCIEnv,        # envhp
     OCIError,      # errhp
     OCILobLocator, # locp
     Ptr(ub4)],     # lenp
    sword)

OCILobIsTemporary = external(
    'OCILobIsTemporary',
    [OCIEnv,        # envhp
     OCIError,      # errhp
     OCILobLocator, # locp
     Ptr(boolean)], # is_temporary
    sword)

OCICallbackLobRead = dvoidp
OCILobRead = external(
    'OCILobRead',
    [OCISvcCtx,     # svchp
     OCIError,      # errhp
     OCILobLocator, # locp
     Ptr(ub4),      # amtp
     ub4,           # offset
     dvoidp,        # bufp
     ub4,           # buflen
     dvoidp,        # ctxp
     OCICallbackLobRead, # cbfp
     ub2,           # csid
     ub1],          # csfrm
    sword)

OCILobTrim = external(
    'OCILobTrim',
    [OCISvcCtx,     # svchp
     OCIError,      # errhp
     OCILobLocator, # locp
     ub4],          # newlen
    sword)

OCICallbackLobWrite = dvoidp
OCILobWrite = external(
    'OCILobWrite',
    [OCISvcCtx,     # svchp
     OCIError,      # errhp
     OCILobLocator, # locp
     Ptr(ub4),      # amtp
     ub4,           # offset
     dvoidp,        # bufp
     ub4,           # buflen
     ub1,           # piece
     dvoidp,        # ctxp
     OCICallbackLobWrite, # cbfp
     ub2,           # csid
     ub1],          # csfrm
    sword)

# Transaction Functions

OCITransCommit = external(
    'OCITransCommit',
    [OCISvcCtx,    # svchp
     OCIError,     # errhp
     ub4],         # mode
    sword)

OCITransRollback = external(
    'OCITransRollback',
    [OCISvcCtx,    # svchp
     OCIError,     # errhp
     ub4],         # mode
    sword)

# Miscellaneous Functions

OCIErrorGet = external(
    'OCIErrorGet',
    [dvoidp,      # hndlp
     ub4,         # recordno
     oratext,     # sqlstate
     Ptr(sb4) ,   # errcodep
     oratext,     # bufp
     ub4,         # bufsize
     ub4],        # type
    sword)

# OCI Miscellaneous Object Functions

OCIObjectGetAttr = external(
    'OCIObjectGetAttr',
    [OCIEnv,             # env
     OCIError,           # err
     dvoidp,             # instance
     dvoidp,             # null_struct
     OCIType,            # tdo
     Ptr(oratext),       # names
     Ptr(ub4),           # lengths
     ub4,                # name_count
     Ptr(ub4),           # indexes
     ub4,                # index_count
     Ptr(OCIInd),        # attr_null_status
     dvoidpp,            # attr_null_struct
     dvoidpp,            # attr_value
     dvoidpp],           # attr_tdo
    sword)


# OCI Object Pin, Unpin, and Free Functions

OCIObjectFree = external(
    'OCIObjectFree',
    [OCIEnv,           # env,
     OCIError,         # err
     dvoidp,           # instance
     ub2],             # flags
    sword)

OCIObjectPin = external(
    'OCIObjectPin',
    [OCIEnv,           # env,
     OCIError,         # err
     OCIRef,           # object_ref
     OCIComplexObject, # corhdl
     OCIPinOpt,        # pin_option
     OCIDuration,      # pin_duration
     OCILockOpt,       # lock_option
     dvoidpp],         # object
    sword)

OCIObjectUnpin = external(
    'OCIObjectUnpin',
    [OCIEnv,           # env,
     OCIError,         # err
     dvoidp],          # object
    sword)

# OCI Collection and Iterator Functions
OCIIterCreate = external(
    'OCIIterCreate',
    [OCIEnv,           # env,
     OCIError,         # err
     OCIColl,          # coll
     Ptr(OCIIter)],    # itr
    sword)

OCIIterDelete = external(
    'OCIIterDelete',
    [OCIEnv,           # env,
     OCIError,         # err
     Ptr(OCIIter)],    # itr
    sword)

OCIIterNext = external(
    'OCIIterNext',
    [OCIEnv,           # env,
     OCIError,         # err
     OCIIter,          # itr
     dvoidpp,          # elem
     dvoidpp,          # elemind
     Ptr(boolean)],    # eoc
    sword)

# OCI Date, Datetime, and Interval Functions

OCIDateTimeCheck = external(
    'OCIDateTimeCheck',
    [dvoidp,        # hndl
     OCIError,      # err
     OCIDateTime,   # date
     Ptr(ub4)],     # valid
    sword)

OCIDateTimeConstruct = external(
    'OCIDateTimeConstruct',
    [dvoidp,        # hndl
     OCIError,      # errhp
     OCIDateTime,   # datetime
     sb2,           # year
     ub1,           # month
     ub1,           # day
     ub1,           # hour
     ub1,           # min
     ub1,           # src
     ub4,           # fsec
     oratext,       # timezone
     size_t],       # timezone_length
    sword)

OCIDateTimeGetDate = external(
    'OCIDateTimeGetDate',
    [dvoidp,        # hndl
     OCIError,      # errhp
     OCIDateTime,   # datetime
     Ptr(sb2),      # year
     Ptr(ub1),      # month
     Ptr(ub1)],     # day
    sword)

OCIDateTimeGetTime = external(
    'OCIDateTimeGetTime',
    [dvoidp,        # hndl
     OCIError,      # errhp
     OCIDateTime,   # datetime
     Ptr(ub1),      # hour
     Ptr(ub1),      # minute
     Ptr(ub1),      # second
     Ptr(ub4)],     # fsec
    sword)

OCIIntervalGetDaySecond = external(
    'OCIIntervalGetDaySecond',
    [dvoidp,         # hndl
     OCIError,       # errhp
     Ptr(sb4),       # dy
     Ptr(sb4),       # hr
     Ptr(sb4),       # mm
     Ptr(sb4),       # ss
     Ptr(sb4),       # fsec
     OCIInterval],   # result
    sword)

OCIIntervalSetDaySecond = external(
    'OCIIntervalSetDaySecond',
    [dvoidp,         # hndl
     OCIError,       # errhp
     sb4,            # dy
     sb4,            # hr
     sb4,            # mm
     sb4,            # ss
     sb4,            # fsec
     OCIInterval],   # result
    sword)

# OCI Number Functions

OCINumberFromInt = external(
    'OCINumberFromInt',
    [OCIError,         # err
     dvoidp,           # inum
     uword,            # inum_length
     uword,            # inum_s_flag
     Ptr(OCINumber)],  # number
    sword)

OCINumberFromReal = external(
    'OCINumberFromReal',
    [OCIError,         # err
     dvoidp,           # rnum
     uword,            # rnum_length
     Ptr(OCINumber)],  # number
    sword)

OCINumberFromText = external(
    'OCINumberFromText',
    [OCIError,         # err
     oratext,          # str
     ub4,              # str_length
     oratext,          # fmt
     ub4,              # fmt_length
     oratext,          # nls_params
     ub4,              # nls_p_length
     Ptr(OCINumber)],  # number
    sword)

OCINumberToInt = external(
    'OCINumberToInt',
    [OCIError,         # err
     Ptr(OCINumber),   # number
     uword,            # rsl_length
     uword,            # rsl_flag
     dvoidp],          # rsl
    sword)

OCINumberToReal = external(
    'OCINumberToReal',
    [OCIError,         # err
     Ptr(OCINumber),   # number
     uword,            # rsl_length
     dvoidp],          # rsl
    sword)

OCINumberToText = external(
    'OCINumberToText',
    [OCIError,         # err
     Ptr(OCINumber),   # number
     oratext,          # fmt
     ub4,              # fmt_length
     oratext,          # nls_params
     ub4,              # nls_p_length
     Ptr(ub4),         # buf_size
     oratext],         # buf
    sword)

# OCI String Functions

OCIStringPtr = external(
    'OCIStringPtr',
    [OCIEnv,        # envhp
     OCIString],    # vs
    oratext)

OCIStringSize = external(
    'OCIStringSize',
    [OCIEnv,        # envhp
     OCIString],    # vs
    ub4)

# OCI Locale Functions

OCINlsCharSetIdToName = external(
    'OCINlsCharSetIdToName',
    [dvoidp,           # hndl
     oratext,          # buf
     size_t,           # buflen
     ub2],             # id
    sword)

OCINlsNameMap = external(
    'OCINlsNameMap',
    [dvoidp,           # hndl
     oratext,          # buf
     size_t,           # buflen
     oratext,          # srcbuf
     uword],           # flag
    sword)
