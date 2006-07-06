; GNU C version 3.4-llvm 20051104 (LLVM 1.6) (i686-pc-linux-gnu)
;	compiled by GNU C version 3.4.0.
; GGC heuristics: --param ggc-min-expand=30 --param ggc-min-heapsize=4096
; options passed:  -iprefix -mtune=pentiumpro -auxbase
; options enabled:  -feliminate-unused-debug-types -fpeephole
; -ffunction-cse -fkeep-static-consts -fpcc-struct-return -fgcse-lm
; -fgcse-sm -fsched-interblock -fsched-spec -fbranch-count-reg -fcommon
; -fgnu-linker -fargument-alias -fzero-initialized-in-bss -fident
; -fmath-errno -ftrapping-math -m80387 -mhard-float -mno-soft-float
; -mieee-fp -mfp-ret-in-387 -maccumulate-outgoing-args -mno-red-zone
; -mtls-direct-seg-refs -mtune=pentiumpro -march=i386

target triple = "i686-pc-linux-gnu"
target pointersize = 32
target endian = little
deplibs = ["c", "crtend"]

"complex double" = type { double, double }
"complex float" = type { float, float }
"complex long double" = type { double, double }

implementation
declare double %acos(double)  ;; __builtin_acos
declare float %acosf(float)  ;; __builtin_acosf
declare double %acosh(double)  ;; __builtin_acosh
declare float %acoshf(float)  ;; __builtin_acoshf
declare double %acoshl(double)  ;; __builtin_acoshl
declare double %acosl(double)  ;; __builtin_acosl
declare double %asin(double)  ;; __builtin_asin
declare float %asinf(float)  ;; __builtin_asinf
declare double %asinh(double)  ;; __builtin_asinh
declare float %asinhf(float)  ;; __builtin_asinhf
declare double %asinhl(double)  ;; __builtin_asinhl
declare double %asinl(double)  ;; __builtin_asinl
declare double %atan(double)  ;; __builtin_atan
declare double %atan2(double,double)  ;; __builtin_atan2
declare float %atan2f(float,float)  ;; __builtin_atan2f
declare double %atan2l(double,double)  ;; __builtin_atan2l
declare float %atanf(float)  ;; __builtin_atanf
declare double %atanh(double)  ;; __builtin_atanh
declare float %atanhf(float)  ;; __builtin_atanhf
declare double %atanhl(double)  ;; __builtin_atanhl
declare double %atanl(double)  ;; __builtin_atanl
declare double %cbrt(double)  ;; __builtin_cbrt
declare float %cbrtf(float)  ;; __builtin_cbrtf
declare double %cbrtl(double)  ;; __builtin_cbrtl
declare double %ceil(double)  ;; __builtin_ceil
declare float %ceilf(float)  ;; __builtin_ceilf
declare double %ceill(double)  ;; __builtin_ceill
declare double %copysign(double,double)  ;; __builtin_copysign
declare float %copysignf(float,float)  ;; __builtin_copysignf
declare double %copysignl(double,double)  ;; __builtin_copysignl
declare double %cos(double)  ;; __builtin_cos
declare float %cosf(float)  ;; __builtin_cosf
declare double %cosh(double)  ;; __builtin_cosh
declare float %coshf(float)  ;; __builtin_coshf
declare double %coshl(double)  ;; __builtin_coshl
declare double %cosl(double)  ;; __builtin_cosl
declare double %drem(double,double)  ;; __builtin_drem
declare float %dremf(float,float)  ;; __builtin_dremf
declare double %dreml(double,double)  ;; __builtin_dreml
declare double %erf(double)  ;; __builtin_erf
declare double %erfc(double)  ;; __builtin_erfc
declare float %erfcf(float)  ;; __builtin_erfcf
declare double %erfcl(double)  ;; __builtin_erfcl
declare float %erff(float)  ;; __builtin_erff
declare double %erfl(double)  ;; __builtin_erfl
declare double %exp(double)  ;; __builtin_exp
declare double %exp10(double)  ;; __builtin_exp10
declare float %exp10f(float)  ;; __builtin_exp10f
declare double %exp10l(double)  ;; __builtin_exp10l
declare double %exp2(double)  ;; __builtin_exp2
declare float %exp2f(float)  ;; __builtin_exp2f
declare double %exp2l(double)  ;; __builtin_exp2l
declare float %expf(float)  ;; __builtin_expf
declare double %expl(double)  ;; __builtin_expl
declare double %expm1(double)  ;; __builtin_expm1
declare float %expm1f(float)  ;; __builtin_expm1f
declare double %expm1l(double)  ;; __builtin_expm1l
declare double %fabs(double)  ;; __builtin_fabs
declare float %fabsf(float)  ;; __builtin_fabsf
declare double %fabsl(double)  ;; __builtin_fabsl
declare double %fdim(double,double)  ;; __builtin_fdim
declare float %fdimf(float,float)  ;; __builtin_fdimf
declare double %fdiml(double,double)  ;; __builtin_fdiml
declare double %floor(double)  ;; __builtin_floor
declare float %floorf(float)  ;; __builtin_floorf
declare double %floorl(double)  ;; __builtin_floorl
declare double %fma(double,double,double)  ;; __builtin_fma
declare float %fmaf(float,float,float)  ;; __builtin_fmaf
declare double %fmal(double,double,double)  ;; __builtin_fmal
declare double %fmax(double,double)  ;; __builtin_fmax
declare float %fmaxf(float,float)  ;; __builtin_fmaxf
declare double %fmaxl(double,double)  ;; __builtin_fmaxl
declare double %fmin(double,double)  ;; __builtin_fmin
declare float %fminf(float,float)  ;; __builtin_fminf
declare double %fminl(double,double)  ;; __builtin_fminl
declare double %fmod(double,double)  ;; __builtin_fmod
declare float %fmodf(float,float)  ;; __builtin_fmodf
declare double %fmodl(double,double)  ;; __builtin_fmodl
declare double %frexp(double,int*)  ;; __builtin_frexp
declare float %frexpf(float,int*)  ;; __builtin_frexpf
declare double %frexpl(double,int*)  ;; __builtin_frexpl
declare double %gamma(double)  ;; __builtin_gamma
declare float %gammaf(float)  ;; __builtin_gammaf
declare double %gammal(double)  ;; __builtin_gammal
declare double %__builtin_huge_val()
declare float %__builtin_huge_valf()
declare double %__builtin_huge_vall()
declare double %hypot(double,double)  ;; __builtin_hypot
declare float %hypotf(float,float)  ;; __builtin_hypotf
declare double %hypotl(double,double)  ;; __builtin_hypotl
declare int %ilogb(double)  ;; __builtin_ilogb
declare int %ilogbf(float)  ;; __builtin_ilogbf
declare int %ilogbl(double)  ;; __builtin_ilogbl
declare double %__builtin_inf()
declare float %__builtin_inff()
declare double %__builtin_infl()
declare double %j0(double)  ;; __builtin_j0
declare float %j0f(float)  ;; __builtin_j0f
declare double %j0l(double)  ;; __builtin_j0l
declare double %j1(double)  ;; __builtin_j1
declare float %j1f(float)  ;; __builtin_j1f
declare double %j1l(double)  ;; __builtin_j1l
declare double %jn(int,double)  ;; __builtin_jn
declare float %jnf(int,float)  ;; __builtin_jnf
declare double %jnl(int,double)  ;; __builtin_jnl
declare double %ldexp(double,int)  ;; __builtin_ldexp
declare float %ldexpf(float,int)  ;; __builtin_ldexpf
declare double %ldexpl(double,int)  ;; __builtin_ldexpl
declare double %lgamma(double)  ;; __builtin_lgamma
declare float %lgammaf(float)  ;; __builtin_lgammaf
declare double %lgammal(double)  ;; __builtin_lgammal
declare long %llrint(double)  ;; __builtin_llrint
declare long %llrintf(float)  ;; __builtin_llrintf
declare long %llrintl(double)  ;; __builtin_llrintl
declare long %llround(double)  ;; __builtin_llround
declare long %llroundf(float)  ;; __builtin_llroundf
declare long %llroundl(double)  ;; __builtin_llroundl
declare double %log(double)  ;; __builtin_log
declare double %log10(double)  ;; __builtin_log10
declare float %log10f(float)  ;; __builtin_log10f
declare double %log10l(double)  ;; __builtin_log10l
declare double %log1p(double)  ;; __builtin_log1p
declare float %log1pf(float)  ;; __builtin_log1pf
declare double %log1pl(double)  ;; __builtin_log1pl
declare double %log2(double)  ;; __builtin_log2
declare float %log2f(float)  ;; __builtin_log2f
declare double %log2l(double)  ;; __builtin_log2l
declare double %logb(double)  ;; __builtin_logb
declare float %logbf(float)  ;; __builtin_logbf
declare double %logbl(double)  ;; __builtin_logbl
declare float %logf(float)  ;; __builtin_logf
declare double %logl(double)  ;; __builtin_logl
declare int %lrint(double)  ;; __builtin_lrint
declare int %lrintf(float)  ;; __builtin_lrintf
declare int %lrintl(double)  ;; __builtin_lrintl
declare int %lround(double)  ;; __builtin_lround
declare int %lroundf(float)  ;; __builtin_lroundf
declare int %lroundl(double)  ;; __builtin_lroundl
declare double %modf(double,double*)  ;; __builtin_modf
declare float %modff(float,float*)  ;; __builtin_modff
declare double %modfl(double,double*)  ;; __builtin_modfl
declare double %nan(sbyte*)  ;; __builtin_nan
declare float %nanf(sbyte*)  ;; __builtin_nanf
declare double %nanl(sbyte*)  ;; __builtin_nanl
declare double %nans(sbyte*)  ;; __builtin_nans
declare float %nansf(sbyte*)  ;; __builtin_nansf
declare double %nansl(sbyte*)  ;; __builtin_nansl
declare double %nearbyint(double)  ;; __builtin_nearbyint
declare float %nearbyintf(float)  ;; __builtin_nearbyintf
declare double %nearbyintl(double)  ;; __builtin_nearbyintl
declare double %nextafter(double,double)  ;; __builtin_nextafter
declare float %nextafterf(float,float)  ;; __builtin_nextafterf
declare double %nextafterl(double,double)  ;; __builtin_nextafterl
declare double %nexttoward(double,double)  ;; __builtin_nexttoward
declare float %nexttowardf(float,double)  ;; __builtin_nexttowardf
declare double %nexttowardl(double,double)  ;; __builtin_nexttowardl
declare double %pow(double,double)  ;; __builtin_pow
declare double %pow10(double)  ;; __builtin_pow10
declare float %pow10f(float)  ;; __builtin_pow10f
declare double %pow10l(double)  ;; __builtin_pow10l
declare float %powf(float,float)  ;; __builtin_powf
declare double %powl(double,double)  ;; __builtin_powl
declare double %remainder(double,double)  ;; __builtin_remainder
declare float %remainderf(float,float)  ;; __builtin_remainderf
declare double %remainderl(double,double)  ;; __builtin_remainderl
declare double %remquo(double,double,int*)  ;; __builtin_remquo
declare float %remquof(float,float,int*)  ;; __builtin_remquof
declare double %remquol(double,double,int*)  ;; __builtin_remquol
declare double %rint(double)  ;; __builtin_rint
declare float %rintf(float)  ;; __builtin_rintf
declare double %rintl(double)  ;; __builtin_rintl
declare double %round(double)  ;; __builtin_round
declare float %roundf(float)  ;; __builtin_roundf
declare double %roundl(double)  ;; __builtin_roundl
declare double %scalb(double,double)  ;; __builtin_scalb
declare float %scalbf(float,float)  ;; __builtin_scalbf
declare double %scalbl(double,double)  ;; __builtin_scalbl
declare double %scalbln(double,int)  ;; __builtin_scalbln
declare float %scalblnf(float,int)  ;; __builtin_scalblnf
declare double %scalblnl(double,int)  ;; __builtin_scalblnl
declare double %scalbn(double,int)  ;; __builtin_scalbn
declare float %scalbnf(float,int)  ;; __builtin_scalbnf
declare double %scalbnl(double,int)  ;; __builtin_scalbnl
declare double %significand(double)  ;; __builtin_significand
declare float %significandf(float)  ;; __builtin_significandf
declare double %significandl(double)  ;; __builtin_significandl
declare double %sin(double)  ;; __builtin_sin
declare void %sincos(double,double*,double*)  ;; __builtin_sincos
declare void %sincosf(float,float*,float*)  ;; __builtin_sincosf
declare void %sincosl(double,double*,double*)  ;; __builtin_sincosl
declare float %sinf(float)  ;; __builtin_sinf
declare double %sinh(double)  ;; __builtin_sinh
declare float %sinhf(float)  ;; __builtin_sinhf
declare double %sinhl(double)  ;; __builtin_sinhl
declare double %sinl(double)  ;; __builtin_sinl
declare double %sqrt(double)  ;; __builtin_sqrt
declare float %sqrtf(float)  ;; __builtin_sqrtf
declare double %sqrtl(double)  ;; __builtin_sqrtl
declare double %tan(double)  ;; __builtin_tan
declare float %tanf(float)  ;; __builtin_tanf
declare double %tanh(double)  ;; __builtin_tanh
declare float %tanhf(float)  ;; __builtin_tanhf
declare double %tanhl(double)  ;; __builtin_tanhl
declare double %tanl(double)  ;; __builtin_tanl
declare double %tgamma(double)  ;; __builtin_tgamma
declare float %tgammaf(float)  ;; __builtin_tgammaf
declare double %tgammal(double)  ;; __builtin_tgammal
declare double %trunc(double)  ;; __builtin_trunc
declare float %truncf(float)  ;; __builtin_truncf
declare double %truncl(double)  ;; __builtin_truncl
declare double %y0(double)  ;; __builtin_y0
declare float %y0f(float)  ;; __builtin_y0f
declare double %y0l(double)  ;; __builtin_y0l
declare double %y1(double)  ;; __builtin_y1
declare float %y1f(float)  ;; __builtin_y1f
declare double %y1l(double)  ;; __builtin_y1l
declare double %yn(int,double)  ;; __builtin_yn
declare float %ynf(int,float)  ;; __builtin_ynf
declare double %ynl(int,double)  ;; __builtin_ynl
declare double %cabs(double,double)  ;; __builtin_cabs
declare float %cabsf(float,float)  ;; __builtin_cabsf
declare double %cabsl(double,double)  ;; __builtin_cabsl
declare void %cacos("complex double"*,double,double)  ;; __builtin_cacos
declare void %cacosf("complex float"*,float,float)  ;; __builtin_cacosf
declare void %cacosh("complex double"*,double,double)  ;; __builtin_cacosh
declare void %cacoshf("complex float"*,float,float)  ;; __builtin_cacoshf
declare void %cacoshl("complex long double"*,double,double)  ;; __builtin_cacoshl
declare void %cacosl("complex long double"*,double,double)  ;; __builtin_cacosl
declare double %carg(double,double)  ;; __builtin_carg
declare float %cargf(float,float)  ;; __builtin_cargf
declare double %cargl(double,double)  ;; __builtin_cargl
declare void %casin("complex double"*,double,double)  ;; __builtin_casin
declare void %casinf("complex float"*,float,float)  ;; __builtin_casinf
declare void %casinh("complex double"*,double,double)  ;; __builtin_casinh
declare void %casinhf("complex float"*,float,float)  ;; __builtin_casinhf
declare void %casinhl("complex long double"*,double,double)  ;; __builtin_casinhl
declare void %casinl("complex long double"*,double,double)  ;; __builtin_casinl
declare void %catan("complex double"*,double,double)  ;; __builtin_catan
declare void %catanf("complex float"*,float,float)  ;; __builtin_catanf
declare void %catanh("complex double"*,double,double)  ;; __builtin_catanh
declare void %catanhf("complex float"*,float,float)  ;; __builtin_catanhf
declare void %catanhl("complex long double"*,double,double)  ;; __builtin_catanhl
declare void %catanl("complex long double"*,double,double)  ;; __builtin_catanl
declare void %ccos("complex double"*,double,double)  ;; __builtin_ccos
declare void %ccosf("complex float"*,float,float)  ;; __builtin_ccosf
declare void %ccosh("complex double"*,double,double)  ;; __builtin_ccosh
declare void %ccoshf("complex float"*,float,float)  ;; __builtin_ccoshf
declare void %ccoshl("complex long double"*,double,double)  ;; __builtin_ccoshl
declare void %ccosl("complex long double"*,double,double)  ;; __builtin_ccosl
declare void %cexp("complex double"*,double,double)  ;; __builtin_cexp
declare void %cexpf("complex float"*,float,float)  ;; __builtin_cexpf
declare void %cexpl("complex long double"*,double,double)  ;; __builtin_cexpl
declare double %cimag(double,double)  ;; __builtin_cimag
declare float %cimagf(float,float)  ;; __builtin_cimagf
declare double %cimagl(double,double)  ;; __builtin_cimagl
declare void %conj("complex double"*,double,double)  ;; __builtin_conj
declare void %conjf("complex float"*,float,float)  ;; __builtin_conjf
declare void %conjl("complex long double"*,double,double)  ;; __builtin_conjl
declare void %cpow("complex double"*,double,double,double,double)  ;; __builtin_cpow
declare void %cpowf("complex float"*,float,float,float,float)  ;; __builtin_cpowf
declare void %cpowl("complex long double"*,double,double,double,double)  ;; __builtin_cpowl
declare void %cproj("complex double"*,double,double)  ;; __builtin_cproj
declare void %cprojf("complex float"*,float,float)  ;; __builtin_cprojf
declare void %cprojl("complex long double"*,double,double)  ;; __builtin_cprojl
declare double %creal(double,double)  ;; __builtin_creal
declare float %crealf(float,float)  ;; __builtin_crealf
declare double %creall(double,double)  ;; __builtin_creall
declare void %csin("complex double"*,double,double)  ;; __builtin_csin
declare void %csinf("complex float"*,float,float)  ;; __builtin_csinf
declare void %csinh("complex double"*,double,double)  ;; __builtin_csinh
declare void %csinhf("complex float"*,float,float)  ;; __builtin_csinhf
declare void %csinhl("complex long double"*,double,double)  ;; __builtin_csinhl
declare void %csinl("complex long double"*,double,double)  ;; __builtin_csinl
declare void %csqrt("complex double"*,double,double)  ;; __builtin_csqrt
declare void %csqrtf("complex float"*,float,float)  ;; __builtin_csqrtf
declare void %csqrtl("complex long double"*,double,double)  ;; __builtin_csqrtl
declare void %ctan("complex double"*,double,double)  ;; __builtin_ctan
declare void %ctanf("complex float"*,float,float)  ;; __builtin_ctanf
declare void %ctanh("complex double"*,double,double)  ;; __builtin_ctanh
declare void %ctanhf("complex float"*,float,float)  ;; __builtin_ctanhf
declare void %ctanhl("complex long double"*,double,double)  ;; __builtin_ctanhl
declare void %ctanl("complex long double"*,double,double)  ;; __builtin_ctanl
declare int %bcmp(sbyte*,sbyte*,uint)  ;; __builtin_bcmp
declare void %bcopy(sbyte*,sbyte*,uint)  ;; __builtin_bcopy
declare void %bzero(sbyte*,uint)  ;; __builtin_bzero
declare int %ffs(int)  ;; __builtin_ffs
declare int %ffsl(int)  ;; __builtin_ffsl
declare int %ffsll(long)  ;; __builtin_ffsll
declare sbyte* %index(sbyte*,int)  ;; __builtin_index
declare int %memcmp(sbyte*,sbyte*,uint)  ;; __builtin_memcmp
declare sbyte* %memcpy(sbyte*,sbyte*,uint)  ;; __builtin_memcpy
declare sbyte* %memmove(sbyte*,sbyte*,uint)  ;; __builtin_memmove
declare sbyte* %mempcpy(sbyte*,sbyte*,uint)  ;; __builtin_mempcpy
declare sbyte* %memset(sbyte*,int,uint)  ;; __builtin_memset
declare sbyte* %rindex(sbyte*,int)  ;; __builtin_rindex
declare sbyte* %stpcpy(sbyte*,sbyte*)  ;; __builtin_stpcpy
declare sbyte* %strcat(sbyte*,sbyte*)  ;; __builtin_strcat
declare sbyte* %strchr(sbyte*,int)  ;; __builtin_strchr
declare int %strcmp(sbyte*,sbyte*)  ;; __builtin_strcmp
declare sbyte* %strcpy(sbyte*,sbyte*)  ;; __builtin_strcpy
declare uint %strcspn(sbyte*,sbyte*)  ;; __builtin_strcspn
declare sbyte* %strdup(sbyte*)  ;; __builtin_strdup
declare uint %strlen(sbyte*)  ;; __builtin_strlen
declare sbyte* %strncat(sbyte*,sbyte*,uint)  ;; __builtin_strncat
declare int %strncmp(sbyte*,sbyte*,uint)  ;; __builtin_strncmp
declare sbyte* %strncpy(sbyte*,sbyte*,uint)  ;; __builtin_strncpy
declare sbyte* %strpbrk(sbyte*,sbyte*)  ;; __builtin_strpbrk
declare sbyte* %strrchr(sbyte*,int)  ;; __builtin_strrchr
declare uint %strspn(sbyte*,sbyte*)  ;; __builtin_strspn
declare sbyte* %strstr(sbyte*,sbyte*)  ;; __builtin_strstr
declare int %fprintf(sbyte*,sbyte*, ...)  ;; __builtin_fprintf
declare int %fprintf_unlocked(sbyte*,sbyte*, ...)  ;; __builtin_fprintf_unlocked
declare int %fputc(int,sbyte*)  ;; __builtin_fputc
declare int %fputc_unlocked(int,sbyte*)  ;; __builtin_fputc_unlocked
declare int %fputs(sbyte*,sbyte*)  ;; __builtin_fputs
declare int %fputs_unlocked(sbyte*,sbyte*)  ;; __builtin_fputs_unlocked
declare int %fscanf(sbyte*,sbyte*, ...)  ;; __builtin_fscanf
declare uint %fwrite(sbyte*,uint,uint,sbyte*)  ;; __builtin_fwrite
declare uint %fwrite_unlocked(sbyte*,uint,uint,sbyte*)  ;; __builtin_fwrite_unlocked
declare int %printf(sbyte*, ...)  ;; __builtin_printf
declare int %printf_unlocked(sbyte*, ...)  ;; __builtin_printf_unlocked
declare int %putchar(int)  ;; __builtin_putchar
declare int %putchar_unlocked(int)  ;; __builtin_putchar_unlocked
declare int %puts(sbyte*)  ;; __builtin_puts
declare int %puts_unlocked(sbyte*)  ;; __builtin_puts_unlocked
declare int %scanf(sbyte*, ...)  ;; __builtin_scanf
declare int %snprintf(sbyte*,uint,sbyte*, ...)  ;; __builtin_snprintf
declare int %sprintf(sbyte*,sbyte*, ...)  ;; __builtin_sprintf
declare int %sscanf(sbyte*,sbyte*, ...)  ;; __builtin_sscanf
declare int %vfprintf(sbyte*,sbyte*,sbyte*)  ;; __builtin_vfprintf
declare int %vfscanf(sbyte*,sbyte*,sbyte*)  ;; __builtin_vfscanf
declare int %vprintf(sbyte*,sbyte*)  ;; __builtin_vprintf
declare int %vscanf(sbyte*,sbyte*)  ;; __builtin_vscanf
declare int %vsnprintf(sbyte*,uint,sbyte*,sbyte*)  ;; __builtin_vsnprintf
declare int %vsprintf(sbyte*,sbyte*,sbyte*)  ;; __builtin_vsprintf
declare int %vsscanf(sbyte*,sbyte*,sbyte*)  ;; __builtin_vsscanf
declare void %abort()  ;; __builtin_abort
declare int %abs(int)  ;; __builtin_abs
declare sbyte* %__builtin_aggregate_incoming_address(...)
declare sbyte* %alloca(uint)  ;; __builtin_alloca
declare sbyte* %__builtin_apply(void (...)*,sbyte*,uint)
declare sbyte* %__builtin_apply_args(...)
declare int %__builtin_args_info(int)
declare sbyte* %calloc(uint,uint)  ;; __builtin_calloc
declare int %__builtin_classify_type(...)
declare int %__builtin_clz(int)
declare int %__builtin_clzl(int)
declare int %__builtin_clzll(long)
declare int %__builtin_constant_p(...)
declare int %__builtin_ctz(int)
declare int %__builtin_ctzl(int)
declare int %__builtin_ctzll(long)
declare sbyte* %dcgettext(sbyte*,sbyte*,int)  ;; __builtin_dcgettext
declare sbyte* %dgettext(sbyte*,sbyte*)  ;; __builtin_dgettext
declare sbyte* %__builtin_dwarf_cfa()
declare uint %__builtin_dwarf_sp_column()
declare void %__builtin_eh_return(int,sbyte*)
declare int %__builtin_eh_return_data_regno(int)
declare void %exit(int)  ;; __builtin_exit
declare int %__builtin_expect(int,int)
declare sbyte* %__builtin_extract_return_addr(sbyte*)
declare sbyte* %__builtin_frame_address(uint)
declare sbyte* %__builtin_frob_return_addr(sbyte*)
declare sbyte* %gettext(sbyte*)  ;; __builtin_gettext
declare long %imaxabs(long)  ;; __builtin_imaxabs
declare void %__builtin_init_dwarf_reg_size_table(sbyte*)
declare int %__builtin_isgreater(...)
declare int %__builtin_isgreaterequal(...)
declare int %__builtin_isless(...)
declare int %__builtin_islessequal(...)
declare int %__builtin_islessgreater(...)
declare int %__builtin_isunordered(...)
declare int %labs(int)  ;; __builtin_labs
declare long %llabs(long)  ;; __builtin_llabs
declare void %__builtin_longjmp(sbyte*,int)
declare sbyte* %malloc(uint)  ;; __builtin_malloc
declare sbyte* %__builtin_next_arg(...)
declare int %__builtin_parity(int)
declare int %__builtin_parityl(int)
declare int %__builtin_parityll(long)
declare int %__builtin_popcount(int)
declare int %__builtin_popcountl(int)
declare int %__builtin_popcountll(long)
declare void %__builtin_prefetch(sbyte*, ...)
declare void %__builtin_return(sbyte*)
declare sbyte* %__builtin_return_address(uint)
declare sbyte* %__builtin_saveregs(...)
declare int %__builtin_setjmp(sbyte*)
declare void %__builtin_stdarg_start(sbyte**, ...)
declare int %strfmon(sbyte*,uint,sbyte*, ...)  ;; __builtin_strfmon
declare uint %strftime(sbyte*,uint,sbyte*,sbyte*)  ;; __builtin_strftime
declare void %__builtin_trap()
declare void %__builtin_unwind_init()
declare void %__builtin_va_copy(sbyte**,sbyte*)
declare void %__builtin_va_end(sbyte**)
declare void %__builtin_va_start(sbyte**, ...)
declare void %_exit(int)  ;; __builtin__exit
declare void %_Exit(int)  ;; __builtin__Exit

int %add(int %n, int %y) {  
entry:
	%n_addr = alloca int		 ; ty=int*
	%y_addr = alloca int		 ; ty=int*
	%result = alloca int		 ; ty=int*
	store int %n, int* %n_addr
	store int %y, int* %y_addr
	%tmp.0 = load int* %n_addr		 ; ty=int
	%tmp.1 = load int* %y_addr		 ; ty=int
	%tmp.2 = add int %tmp.0, %tmp.1		 ; ty=int
	store int %tmp.2, int* %result
	br label %return
after_ret:
	br label %return
return:
	%tmp.3 = load int* %result		 ; ty=int
	ret int %tmp.3
}

;; Created by "GCC: (GNU) 3.4-llvm 20051104 (LLVM 1.6)"
