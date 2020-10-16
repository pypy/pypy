from .support import HPyTest, DefaultExtensionTemplate
from .test_hpytype import PointTemplate

class TestSlots(HPyTest):

    ExtensionTemplate = PointTemplate

    def test_tp_init(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_xy
            HPyDef_SLOT(Point_new, HPyType_GenericNew, HPy_tp_new)

            HPyDef_SLOT(Point_init, Point_init_impl, HPy_tp_init)
            static int Point_init_impl(HPyContext ctx, HPy self, HPy *args,
                                       HPy_ssize_t nargs, HPy kw)
            {
                long x, y;
                if (!HPyArg_Parse(ctx, args, nargs, "ll", &x, &y))
                    return -1;

                PointObject *p = HPy_CAST(ctx, PointObject, self);
                p->x = x;
                p->y = y;
                return 0;
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_init, &Point_x, &Point_y)
            @INIT
        """)
        p = mod.Point(1, 2)
        assert p.x == 1
        assert p.y == 2

    def test_sq_item(self):
        mod = self.make_module("""
            @DEFINE_PointObject

            HPyDef_SLOT(Point_getitem, Point_getitem_impl, HPy_sq_item);
            static HPy Point_getitem_impl(HPyContext ctx, HPy self, HPy_ssize_t idx)
            {
                return HPyLong_FromLong(ctx, (long)idx*2);
            }

            @EXPORT_POINT_TYPE(&Point_getitem)
            @INIT
        """)
        p = mod.Point()
        assert p[4] == 8
        assert p[21] == 42

    def test_tp_destroy(self):
        import gc
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new

            static long destroyed_x;

            HPyDef_SLOT(Point_destroy, Point_destroy_impl, HPy_tp_destroy)
            static void Point_destroy_impl(void *obj)
            {
                PointObject *point = (PointObject *)obj;
                destroyed_x += point->x;
            }

            HPyDef_METH(get_destroyed_x, "get_destroyed_x", get_destroyed_x_impl, HPyFunc_NOARGS)
            static HPy get_destroyed_x_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, destroyed_x);
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_destroy)
            @EXPORT(get_destroyed_x)
            @INIT
        """)
        point = mod.Point(7, 3)
        assert mod.get_destroyed_x() == 0
        del point
        gc.collect()
        assert mod.get_destroyed_x() == 7
        gc.collect()
        assert mod.get_destroyed_x() == 7

    def test_nb_ops_binary(self):
        import operator
        mod = self.make_module(r"""
            @DEFINE_PointObject

            #define MYSLOT(NAME)                                               \
                HPyDef_SLOT(p_##NAME, NAME##_impl, HPy_nb_##NAME);             \
                static HPy NAME##_impl(HPyContext ctx, HPy self, HPy other)    \
                {                                                              \
                    HPy s = HPyUnicode_FromString(ctx, #NAME);                 \
                    HPy res = HPyTuple_Pack(ctx, 3, self, s, other);           \
                    HPy_Close(ctx, s);                                         \
                    return res;                                                \
                }

            MYSLOT(add)
            MYSLOT(and)
            MYSLOT(divmod)
            MYSLOT(floor_divide)
            MYSLOT(lshift)
            MYSLOT(multiply)
            MYSLOT(or)
            MYSLOT(remainder)
            MYSLOT(rshift)
            MYSLOT(subtract)
            MYSLOT(true_divide)
            MYSLOT(xor)
            MYSLOT(matrix_multiply)

            @EXPORT_POINT_TYPE(&p_add, &p_and, &p_divmod, &p_floor_divide, &p_lshift, &p_multiply, &p_or, &p_remainder, &p_rshift, &p_subtract, &p_true_divide, &p_xor, &p_matrix_multiply)
            @INIT
        """)
        p = mod.Point()
        assert p + 42 == (p, "add", 42)
        assert p & 42 == (p, "and", 42)
        assert divmod(p, 42) == (p, "divmod", 42)
        assert p // 42 == (p, "floor_divide", 42)
        assert p << 42 == (p, "lshift", 42)
        assert p * 42 == (p, "multiply", 42)
        assert p | 42 == (p, "or", 42)
        assert p % 42 == (p, "remainder", 42)
        assert p >> 42 == (p, "rshift", 42)
        assert p - 42 == (p, "subtract", 42)
        assert p / 42 == (p, "true_divide", 42)
        assert p ^ 42 == (p, "xor", 42)
        # we can't use '@' because we want to be importable on py27
        assert operator.matmul(p, 42) == (p, "matrix_multiply", 42)

    def test_nb_ops_inplace(self):
        import operator
        mod = self.make_module(r"""
            @DEFINE_PointObject

            #define MYSLOT(NAME)                                               \
                HPyDef_SLOT(p_##NAME, NAME##_impl, HPy_nb_##NAME);             \
                static HPy NAME##_impl(HPyContext ctx, HPy self, HPy other)    \
                {                                                              \
                    HPy s = HPyUnicode_FromString(ctx, #NAME);                 \
                    HPy res = HPyTuple_Pack(ctx, 3, self, s, other);           \
                    HPy_Close(ctx, s);                                         \
                    return res;                                                \
                }

            MYSLOT(inplace_add)
            MYSLOT(inplace_and)
            MYSLOT(inplace_floor_divide)
            MYSLOT(inplace_lshift)
            MYSLOT(inplace_multiply)
            MYSLOT(inplace_or)
            MYSLOT(inplace_remainder)
            MYSLOT(inplace_rshift)
            MYSLOT(inplace_subtract)
            MYSLOT(inplace_true_divide)
            MYSLOT(inplace_xor)
            MYSLOT(inplace_matrix_multiply)

            @EXPORT_POINT_TYPE(&p_inplace_add, &p_inplace_and, &p_inplace_floor_divide, &p_inplace_lshift, &p_inplace_multiply, &p_inplace_or, &p_inplace_remainder, &p_inplace_rshift, &p_inplace_subtract, &p_inplace_true_divide, &p_inplace_xor, &p_inplace_matrix_multiply)
            @INIT
        """)
        p = mod.Point()
        tmp = p; tmp += 42; assert tmp == (p, "inplace_add", 42)
        tmp = p; tmp &= 42; assert tmp == (p, "inplace_and", 42)
        tmp = p; tmp //= 42; assert tmp == (p, "inplace_floor_divide", 42)
        tmp = p; tmp <<= 42; assert tmp == (p, "inplace_lshift", 42)
        tmp = p; tmp *= 42; assert tmp == (p, "inplace_multiply", 42)
        tmp = p; tmp |= 42; assert tmp == (p, "inplace_or", 42)
        tmp = p; tmp %= 42; assert tmp == (p, "inplace_remainder", 42)
        tmp = p; tmp >>= 42; assert tmp == (p, "inplace_rshift", 42)
        tmp = p; tmp -= 42; assert tmp == (p, "inplace_subtract", 42)
        tmp = p; tmp /= 42; assert tmp == (p, "inplace_true_divide", 42)
        tmp = p; tmp ^= 42; assert tmp == (p, "inplace_xor", 42)
        #
        # we can't use '@=' because we want to be importable on py27
        tmp = p
        tmp = operator.imatmul(p, 42)
        assert tmp == (p, "inplace_matrix_multiply", 42)

    def test_nb_ops_unary(self):
        mod = self.make_module(r"""
            @DEFINE_PointObject

            #define MYSLOT(NAME)                                               \
                HPyDef_SLOT(p_##NAME, NAME##_impl, HPy_nb_##NAME);             \
                static HPy NAME##_impl(HPyContext ctx, HPy self)               \
                {                                                              \
                    HPy s = HPyUnicode_FromString(ctx, #NAME);                 \
                    HPy res = HPyTuple_Pack(ctx, 2, s, self);                  \
                    HPy_Close(ctx, s);                                         \
                    return res;                                                \
                }

            MYSLOT(negative)
            MYSLOT(positive)
            MYSLOT(absolute)
            MYSLOT(invert)

            @EXPORT_POINT_TYPE(&p_negative, &p_positive, &p_absolute, &p_invert)
            @INIT
        """)
        p = mod.Point()
        assert +p == ('positive', p)
        assert -p == ('negative', p)
        assert abs(p) == ('absolute', p)
        assert ~p == ('invert', p)

    def test_nb_ops_type_conversion(self):
        import operator
        mod = self.make_module(r"""
            @DEFINE_PointObject
            @DEFINE_Point_new

            HPyDef_SLOT(p_int, p_int_impl, HPy_nb_int);
            static HPy p_int_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 42);
            }

            HPyDef_SLOT(p_float, p_float_impl, HPy_nb_float);
            static HPy p_float_impl(HPyContext ctx, HPy self)
            {
                return HPyFloat_FromDouble(ctx, 123.4);
            }

            HPyDef_SLOT(p_index, p_index_impl, HPy_nb_index);
            static HPy p_index_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, -456);
            }

            HPyDef_SLOT(p_bool, p_bool_impl, HPy_nb_bool);
            static int p_bool_impl(HPyContext ctx, HPy self)
            {
                PointObject *point = HPy_CAST(ctx, PointObject, self);
                return (point->x != 0);
            }

            @EXPORT_POINT_TYPE(&Point_new, &p_int, &p_float, &p_index, &p_bool)
            @INIT
        """)
        p = mod.Point(0, 0)
        assert int(p) == 42
        assert float(p) == 123.4
        assert operator.index(p) == -456
        #
        assert bool(mod.Point(0, 0)) is False
        assert bool(mod.Point(1, 0)) is True

    def test_nb_ops_power(self):
        mod = self.make_module(r"""
            @DEFINE_PointObject

            HPyDef_SLOT(p_power, p_power_impl, HPy_nb_power);
            static HPy p_power_impl(HPyContext ctx, HPy self, HPy x, HPy y)
            {
                HPy s = HPyUnicode_FromString(ctx, "power");
                HPy res = HPyTuple_Pack(ctx, 4, self, s, x, y);
                HPy_Close(ctx, s);
                return res;
            }

            HPyDef_SLOT(p_inplace_power, p_inplace_power_impl, HPy_nb_inplace_power);
            static HPy p_inplace_power_impl(HPyContext ctx, HPy self, HPy x, HPy y)
            {
                HPy s = HPyUnicode_FromString(ctx, "inplace_power");
                HPy res = HPyTuple_Pack(ctx, 4, self, s, x, y);
                HPy_Close(ctx, s);
                return res;
            }

            @EXPORT_POINT_TYPE(&p_power, &p_inplace_power)
            @INIT
        """)
        p = mod.Point()
        assert p**42 == (p, 'power', 42, None)
        assert pow(p, 42, 123) == (p, 'power', 42, 123)
        tmp = p
        tmp **= 42
        assert tmp == (p, 'inplace_power', 42, None)
