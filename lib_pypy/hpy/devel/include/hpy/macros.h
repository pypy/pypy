/* We define HPy_New as a macro around _HPy_New to suppress a
   warning. Usually, we expected it to be called this way:

       PointObject *p;
       HPy h = HPy_New(ctx, cls, &p);

   If we call _HPy_New directly, we get a warning because we are implicitly
   casting a PointObject** into a void**. The following macro explicitly
   casts the third argument to a void**.
*/

#define HPy_New(ctx, cls, data) (_HPy_New(                                    \
    (ctx),                                                                    \
    (cls),                                                                    \
    ((void**)data)                                                            \
  ))

/* Rich comparison opcodes */
typedef enum {
    HPy_LT = 0,
    HPy_LE = 1,
    HPy_EQ = 2,
    HPy_NE = 3,
    HPy_GT = 4,
    HPy_GE = 5,
} HPy_RichCmpOp;

// this needs to be a macro because val1 and val2 can be of arbitrary types
#define HPy_RETURN_RICHCOMPARE(ctx, val1, val2, op)                     \
    do {                                                                \
        bool result;                                                    \
        switch (op) {                                                   \
        case HPy_EQ: result = ((val1) == (val2)); break;                \
        case HPy_NE: result = ((val1) != (val2)); break;                \
        case HPy_LT: result = ((val1) <  (val2)); break;                \
        case HPy_GT: result = ((val1) >  (val2)); break;                \
        case HPy_LE: result = ((val1) <= (val2)); break;                \
        case HPy_GE: result = ((val1) >= (val2)); break;                \
        default:                                                        \
            HPy_FatalError(ctx, "Invalid value for HPy_RichCmpOp");     \
        }                                                               \
        if (result)                                                     \
            return HPy_Dup(ctx, ctx->h_True);                           \
        return HPy_Dup(ctx, ctx->h_False);                              \
    } while (0)


#if !defined(SIZEOF_PID_T) || SIZEOF_PID_T == SIZEOF_INT
    #define _HPy_PARSE_PID "i"
    #define HPyLong_FromPid HPyLong_FromLong
    #define HPyLong_AsPid HPyLong_AsLong
#elif SIZEOF_PID_T == SIZEOF_LONG
    #define _HPy_PARSE_PID "l"
    #define HPyLong_FromPid HPyLong_FromLong
    #define HPyLong_AsPid HPyLong_AsLong
#elif defined(SIZEOF_LONG_LONG) && SIZEOF_PID_T == SIZEOF_LONG_LONG
    #define _HPy_PARSE_PID "L"
    #define HPyLong_FromPid HPyLong_FromLongLong
    #define HPyLong_AsPid HPyLong_AsLongLong
#else
#error "sizeof(pid_t) is neither sizeof(int), sizeof(long) or sizeof(long long)"
#endif /* SIZEOF_PID_T */

#define HPy_BEGIN_LEAVE_PYTHON(context) { \
    HPyThreadState _token;                                    \
    _token = HPy_LeavePythonExecution(context);

#define HPy_END_LEAVE_PYTHON(context)   \
    HPy_ReenterPythonExecution(context, _token); \
    }
