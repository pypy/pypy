#include "hpy.h"

#define _BREAK_IF_OPTIONAL(current_arg) if (HPy_IsNull(current_arg)) break;

int _HPyArg_ParseItem(HPyContext ctx, HPy current_arg, const char **fmt, va_list vl)
{
  switch (*(*fmt)++) {
  case 'i': {
      int *output = va_arg(vl, int *);
      _BREAK_IF_OPTIONAL(current_arg);
      long value = HPyLong_AsLong(ctx, current_arg);
      if (value == -1 && HPyErr_Occurred(ctx))
          return 0;
      *output = (int)value;
      break;
  }
  case 'l': {
      long *output = va_arg(vl, long *);
      _BREAK_IF_OPTIONAL(current_arg);
      long value = HPyLong_AsLong(ctx, current_arg);
      if (value == -1 && HPyErr_Occurred(ctx))
          return 0;
      *output = value;
      break;
  }
  case 'O': {
      HPy *output = va_arg(vl, HPy *);
      _BREAK_IF_OPTIONAL(current_arg);
      *output = current_arg;
      break;
  }
  default:
      HPyErr_SetString(ctx, ctx->h_ValueError, "XXX: Unknown arg format code");
      return 0;
  }
  return 1;
}

HPyAPI_RUNTIME_FUNC(int)
HPyArg_Parse(HPyContext ctx, HPy *args, HPy_ssize_t nargs, const char *fmt, ...)
{
    va_list vl;
    va_start(vl, fmt);
    const char *fmt1 = fmt;
    int optional = 0;
    HPy_ssize_t i = 0;
    HPy current_arg;

    while (*fmt1 != 0) {
        if (*fmt1 == '|') {
          optional = 1;
          fmt1++;
          continue;
        }
        current_arg = HPy_NULL;
        if (i < nargs) {
          current_arg = args[i];
        }
        if (!HPy_IsNull(current_arg) || optional) {
          if (!_HPyArg_ParseItem(ctx, current_arg, &fmt1, vl)) {
            return 0;
          }
        }
        else {
          HPyErr_SetString(ctx, ctx->h_TypeError,
                           "XXX: required positional argument missing");
          return 0;
        }
        i++;
    }
    if (i < nargs) {
        HPyErr_SetString(ctx, ctx->h_TypeError, "XXX: mismatched args (too many arguments for fmt)");
        return 0;
    }

    va_end(vl);
    return 1;
}

HPyAPI_RUNTIME_FUNC(int)
HPyArg_ParseKeywords(HPyContext ctx, HPy *args, HPy_ssize_t nargs, HPy kw,
                     const char *fmt, const char *keywords[], ...)
{
  va_list vl;
  va_start(vl, keywords);
  const char *fmt1 = fmt;
  int optional = 0;
  int keyword_only = 0;
  HPy_ssize_t i = 0;
  HPy_ssize_t nkw = 0;
  HPy current_arg;

  // first count positional only arguments
  while (keywords[nkw] != NULL && !*keywords[nkw]) nkw++;
  // then check and count the rest
  while (keywords[nkw] != NULL) {
    if (!*keywords[nkw]) {
      HPyErr_SetString(ctx, ctx->h_TypeError, "XXX: Empty keyword parameter name");
      return 0;
    }
    nkw++;
  }

  while (*fmt1 != 0) {
      if (*fmt1 == '|') {
        optional = 1;
        fmt1++;
        continue;
      }
      if (*fmt1 == '$') {
        optional = 1;
        keyword_only = 1;
        fmt1++;
        continue;
      }
      if (i >= nkw) {
        HPyErr_SetString(ctx, ctx->h_TypeError, "XXX: mismatched args (too few keywords for fmt)");
        return 0;
      }
      current_arg = HPy_NULL;
      if (i < nargs) {
        if (keyword_only) {
          HPyErr_SetString(ctx, ctx->h_TypeError, "XXX: keyword only argument passed as positional argument");
          return 0;
        }
        current_arg = args[i];
      }
      else if (!HPy_IsNull(kw) && *keywords[i]) {
        current_arg = HPyDict_GetItem(ctx, kw, HPyUnicode_FromString(ctx, keywords[i]));
      }
      if (!HPy_IsNull(current_arg) || optional) {
        if (!_HPyArg_ParseItem(ctx, current_arg, &fmt1, vl)) {
          return 0;
        }
      }
      else {
        HPyErr_SetString(ctx, ctx->h_TypeError, "XXX: no value for required argument");
        return 0;
      }
      i++;
  }
  if (i != nkw) {
      HPyErr_SetString(ctx, ctx->h_TypeError, "XXX: mismatched args (too many keywords for fmt)");
      return 0;
  }

  va_end(vl);
  return 1;
}
