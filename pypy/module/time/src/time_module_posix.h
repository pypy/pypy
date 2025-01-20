#ifdef HAVE_CLOCK_NANOSLEEP
RPY_EXTERN int
py_clock_nanosleep(clockid_t clockid, int flags,
                   const struct timespec *request,
                   struct timespec *remain);
#endif

#ifdef HAVE_NANOSLEEP
RPY_EXTERN int
py_nanosleep(const struct timespec *rqtp, struct timespec *rmtp);
#endif
