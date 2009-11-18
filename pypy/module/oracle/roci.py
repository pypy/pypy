from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.conftest import option
import os
import py

oracle_home = getattr(option, 'oracle_home',
                      os.environ.get("ORACLE_HOME"))
if oracle_home:
    ORACLE_HOME = py.path.local(oracle_home)
else:
    raise ImportError(
        "Please set ORACLE_HOME to the root of an Oracle client installation")

eci = ExternalCompilationInfo(
    includes = ['oci.h'],
    include_dirs = [str(ORACLE_HOME.join('OCI', 'include'))],
    libraries = ['oci'],
    library_dirs = [str(ORACLE_HOME.join('OCI', 'lib', 'MSVC'))],
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
    uword = platform.SimpleType('sword', rffi.UINT)

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

    constants = '''
    OCI_DEFAULT OCI_OBJECT OCI_THREADED OCI_EVENTS
    OCI_SUCCESS OCI_SUCCESS_WITH_INFO OCI_INVALID_HANDLE OCI_NO_DATA
    OCI_HTYPE_ERROR OCI_HTYPE_SVCCTX OCI_HTYPE_SERVER OCI_HTYPE_SESSION
    OCI_HTYPE_STMT OCI_HTYPE_DESCRIBE
    OCI_DTYPE_PARAM
    OCI_CRED_RDBMS
    OCI_ATTR_SERVER OCI_ATTR_SESSION OCI_ATTR_USERNAME OCI_ATTR_PASSWORD
    OCI_ATTR_STMT_TYPE OCI_ATTR_PARAM_COUNT OCI_ATTR_ROW_COUNT
    OCI_ATTR_NAME OCI_ATTR_SCALE OCI_ATTR_PRECISION OCI_ATTR_IS_NULL
    OCI_ATTR_DATA_SIZE OCI_ATTR_DATA_TYPE OCI_ATTR_CHARSET_FORM
    OCI_ATTR_PARSE_ERROR_OFFSET
    OCI_NTV_SYNTAX
    OCI_FETCH_NEXT
    OCI_IND_NULL OCI_IND_NOTNULL
    OCI_STMT_SELECT OCI_STMT_CREATE OCI_STMT_DROP OCI_STMT_ALTER
    OCI_STMT_INSERT OCI_STMT_DELETE OCI_STMT_UPDATE
    SQLT_CHR SQLT_LNG SQLT_AFC SQLT_RDD SQLT_BIN SQLT_LBI
    SQLT_BFLOAT SQLT_IBFLOAT SQLT_BDOUBLE SQLT_IBDOUBLE
    SQLT_NUM SQLT_VNU SQLT_DAT SQLT_ODT SQLT_DATE SQLT_TIMESTAMP
    SQLT_TIMESTAMP_TZ SQLT_TIMESTAMP_LTZ SQLT_INTERVAL_DS
    SQLT_CLOB SQLT_CLOB SQLT_BLOB SQLT_BFILE SQLT_RSET SQLT_NTY
    SQLCS_IMPLICIT SQLCS_NCHAR
    OCI_NUMBER_SIGNED
    '''.split()

    for c in constants:
        locals()[c] = platform.ConstantInteger(c)

globals().update(platform.configure(CConfig))

OCI_IND_NOTNULL = rffi.cast(rffi.SHORT, OCI_IND_NOTNULL)
OCI_IND_NULL = rffi.cast(rffi.SHORT, OCI_IND_NULL)

OCISvcCtx = rffi.VOIDP
OCIEnv = rffi.VOIDP
OCIError = rffi.VOIDP
OCIServer = rffi.VOIDP
OCISession = rffi.VOIDP
OCIStmt = rffi.VOIDP
OCIParam = rffi.VOIDP
OCIBind = rffi.VOIDP
OCIDefine = rffi.VOIDP
OCISnapshot = rffi.VOIDP

void = lltype.Void
dvoidp = rffi.VOIDP
dvoidpp = rffi.VOIDPP
size_t = rffi.SIZE_T
oratext = rffi.CCHARP
Ptr = rffi.CArrayPtr

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

# Connect, Authorize, and Initialize Functions

OCIEnvNlsCreate = external(
    'OCIEnvNlsCreate',
    [rffi.CArrayPtr(OCIEnv), # envhpp
     ub4,                    # mode
     dvoidp,                 # ctxp
     rffi.CCallback(         # malocfp
         [dvoidp, size_t], dvoidp),
     rffi.CCallback(         # ralocfp
         [dvoidp, dvoidp, size_t], dvoidp),
     rffi.CCallback(         # mfreefp
         [dvoidp, dvoidp], lltype.Void),
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

