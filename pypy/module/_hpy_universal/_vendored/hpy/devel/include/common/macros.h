/* We define HPy_New as a macro around _HPy_New to suppress a
   warning. Usually, we expected it to be called this way:
       PointObject *p;
       HPy h = HPy_New(ctx, cls, &p);

   If we call _HPy_New directly, we get a warning because we are implicitly
   casting a PointObject** into a void**.  The following macro uses a trick to
   implicitly cast to void** in a safer way: the 3rd argument is passed as:

       (void)sizeof((*data)->_ob_head._reserved0), (void**)data

   The left operand of the comma operator is ignored, but it ensures that
   p is really a pointer to a pointer to a structure with a HPyObject_HEAD.
   The sizeof() ensures that the expression is not actually evaluated at all.
   The cast to (void) is needed to convince GCC not to emit a warning about
   the unused result.

   The goal of the comment inside the macro is to be displayed in case of
   error. If you pass a non compatible type (e.g. a PointObject* instead of a
   PointObject**), GCC will complain with an error like this:

     ...macros.h:28:19: error: invalid type argument of unary ‘*’ (...)
     (void)sizeof((*data)->_ob_head._reserved0), / * ERROR: blah blah * /

*/

#define HPy_New(ctx, cls, data) (_HPy_New(                                    \
    (ctx),                                                                    \
    (cls),                                                                    \
    ((void)sizeof((*data)->_ob_head._reserved0), /* ERROR: expected a variable of type T** with T a structure starting with HPyObject_HEAD */ \
     (void**)data)                                                            \
  ))


/* ~~~ HPyTuple_Pack ~~~

   this is just syntactic sugar around HPyTuple_FromArray, to help porting the
   exising code which uses PyTuple_Pack
*/

#define HPyTuple_Pack(ctx, n, ...) (HPyTuple_FromArray(ctx, (HPy[]){ __VA_ARGS__ }, n))

/* Rich comparison opcodes */
#define HPy_LT 0
#define HPy_LE 1
#define HPy_EQ 2
#define HPy_NE 3
#define HPy_GT 4
#define HPy_GE 5
