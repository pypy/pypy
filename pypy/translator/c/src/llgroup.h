#ifndef _PYPY_LL_GROUP_H_
#define _PYPY_LL_GROUP_H_

#define GROUP_MEMBER_OFFSET(grouptype, membername)  \
  ((unsigned short)(((int)&((grouptype*)NULL)->membername) / sizeof(long)))

#define _OP_GET_GROUP_MEMBER(groupptr, compactoffset)  \
  (((char*)groupptr) + ((long)compactoffset)*sizeof(long))

#define _OP_GET_NEXT_GROUP_MEMBER(groupptr, compactoffset, skipoffset)  \
  ((((char*)groupptr) + skipoffset) + ((long)compactoffset)*sizeof(long))

#define OP_IS_GROUP_MEMBER_NONZERO(compactoffset, r)  \
  r = (compactoffset != 0)

#define OP_EXTRACT_USHORT(value, r)  \
  r = (unsigned short)value

#define OP_COMBINE_USHORT(ushort, rest, r)  \
  r = ((long)ushort) | rest;

/* A macro to crash at compile-time if sizeof(group) is too large.
   Uses a hack that I've found on some random forum.  Haaaaaaaaaackish. */
#define PYPY_GROUP_CHECK_SIZE(groupname)                              \
  typedef char group_##groupname##_is_too_large[2*(sizeof(groupname)  \
                                                   <= 65536 * sizeof(long))-1]


#endif /* _PYPY_LL_GROUP_H_ */
