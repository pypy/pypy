from ctypes import *

import pypy.rpython.rctypes.implementation
from pypy.rpython.rctypes.tool import util
from pypy.rpython.rctypes.tool.ctypes_platform import Library, configure

prefix = '/usr/local'

class CConfig:
    _header_ = ''
    _includes_ = ['cairo.h']
    _include_dirs_ = [prefix+'/include/cairo']
    cairo = Library('cairo')

cconfig = configure(CConfig)
libcairo = cconfig['cairo']

STRING = c_char_p


CAIRO_SUBPIXEL_ORDER_RGB = 1
CAIRO_OPERATOR_CLEAR = 0
CAIRO_LINE_JOIN_MITER = 0
CAIRO_STATUS_SURFACE_TYPE_MISMATCH = 13
CAIRO_OPERATOR_DEST_IN = 8
CAIRO_PATTERN_TYPE_SOLID = 0
CAIRO_FILTER_FAST = 0
CAIRO_PATTERN_TYPE_SURFACE = 1
CAIRO_ANTIALIAS_NONE = 1
CAIRO_STATUS_INVALID_DSC_COMMENT = 20
CAIRO_EXTEND_PAD = 3
CAIRO_OPERATOR_DEST_OUT = 9
CAIRO_FONT_SLANT_NORMAL = 0
CAIRO_LINE_CAP_BUTT = 0
CAIRO_FILTER_BILINEAR = 4
CAIRO_STATUS_INVALID_STRING = 8
CAIRO_OPERATOR_DEST_ATOP = 10
CAIRO_PATH_CURVE_TO = 2
CAIRO_FONT_SLANT_OBLIQUE = 2
CAIRO_CONTENT_COLOR_ALPHA = 12288
CAIRO_STATUS_PATTERN_TYPE_MISMATCH = 14
CAIRO_ANTIALIAS_SUBPIXEL = 3
CAIRO_SUBPIXEL_ORDER_BGR = 2
CAIRO_HINT_STYLE_FULL = 4
CAIRO_STATUS_NO_CURRENT_POINT = 4
CAIRO_CONTENT_ALPHA = 8192
CAIRO_STATUS_INVALID_DASH = 19
CAIRO_EXTEND_NONE = 0
CAIRO_SURFACE_TYPE_SVG = 10
CAIRO_FONT_TYPE_TOY = 0
CAIRO_OPERATOR_ATOP = 5
CAIRO_STATUS_INVALID_PATH_DATA = 9
CAIRO_FILTER_GAUSSIAN = 5
CAIRO_SURFACE_TYPE_GLITZ = 5
CAIRO_SURFACE_TYPE_XCB = 4
CAIRO_STATUS_INVALID_RESTORE = 2
CAIRO_OPERATOR_DEST = 6
CAIRO_OPERATOR_OVER = 2
CAIRO_STATUS_INVALID_POP_GROUP = 3
CAIRO_FILTER_GOOD = 1
CAIRO_LINE_JOIN_ROUND = 1
CAIRO_STATUS_NO_MEMORY = 1
CAIRO_SURFACE_TYPE_PS = 2
CAIRO_FORMAT_A1 = 3
CAIRO_HINT_METRICS_OFF = 1
CAIRO_FONT_TYPE_WIN32 = 2
CAIRO_STATUS_FILE_NOT_FOUND = 18
CAIRO_PATTERN_TYPE_RADIAL = 3
CAIRO_SURFACE_TYPE_WIN32 = 7
CAIRO_FORMAT_A8 = 2
CAIRO_FONT_WEIGHT_NORMAL = 0
CAIRO_OPERATOR_XOR = 11
CAIRO_HINT_METRICS_DEFAULT = 0
CAIRO_FILL_RULE_EVEN_ODD = 1
CAIRO_FONT_TYPE_FT = 1
CAIRO_HINT_METRICS_ON = 2
CAIRO_FILTER_BEST = 2
CAIRO_OPERATOR_ADD = 12
CAIRO_FORMAT_RGB16_565 = 4
CAIRO_STATUS_INVALID_FORMAT = 16
CAIRO_FILL_RULE_WINDING = 0
CAIRO_STATUS_WRITE_ERROR = 11
CAIRO_STATUS_SURFACE_FINISHED = 12
CAIRO_SURFACE_TYPE_IMAGE = 0
CAIRO_PATH_LINE_TO = 1
CAIRO_SUBPIXEL_ORDER_DEFAULT = 0
CAIRO_OPERATOR_SATURATE = 13
CAIRO_FORMAT_RGB24 = 1
CAIRO_SURFACE_TYPE_BEOS = 8
CAIRO_OPERATOR_OUT = 4
CAIRO_FORMAT_ARGB32 = 0
CAIRO_FILTER_NEAREST = 3
CAIRO_PATH_CLOSE_PATH = 3
CAIRO_FONT_WEIGHT_BOLD = 1
CAIRO_OPERATOR_SOURCE = 1
CAIRO_STATUS_INVALID_MATRIX = 5
CAIRO_STATUS_INVALID_STATUS = 6
CAIRO_CONTENT_COLOR = 4096
CAIRO_SUBPIXEL_ORDER_VBGR = 4
CAIRO_HINT_STYLE_SLIGHT = 2
CAIRO_OPERATOR_IN = 3
CAIRO_LINE_CAP_SQUARE = 2
CAIRO_SUBPIXEL_ORDER_VRGB = 3
CAIRO_EXTEND_REFLECT = 2
CAIRO_SURFACE_TYPE_DIRECTFB = 9
CAIRO_STATUS_NULL_POINTER = 7
CAIRO_ANTIALIAS_GRAY = 2
CAIRO_PATTERN_TYPE_LINEAR = 2
CAIRO_SURFACE_TYPE_QUARTZ = 6
CAIRO_ANTIALIAS_DEFAULT = 0
CAIRO_HINT_STYLE_NONE = 1
CAIRO_EXTEND_REPEAT = 1
CAIRO_LINE_JOIN_BEVEL = 2
CAIRO_STATUS_SUCCESS = 0
CAIRO_STATUS_INVALID_VISUAL = 17
CAIRO_SURFACE_TYPE_XLIB = 3
CAIRO_STATUS_READ_ERROR = 10
CAIRO_HINT_STYLE_MEDIUM = 3
CAIRO_HINT_STYLE_DEFAULT = 0
CAIRO_STATUS_INVALID_CONTENT = 15
CAIRO_PATH_MOVE_TO = 0
CAIRO_FONT_SLANT_ITALIC = 1
CAIRO_LINE_CAP_ROUND = 1
CAIRO_SURFACE_TYPE_PDF = 1
CAIRO_FONT_TYPE_ATSUI = 3
CAIRO_OPERATOR_DEST_OVER = 7
cairo_version = libcairo.cairo_version
cairo_version.restype = c_int
cairo_version.argtypes = []
cairo_version_string = libcairo.cairo_version_string
cairo_version_string.restype = STRING
cairo_version_string.argtypes = []
cairo_bool_t = c_int
class _cairo(Structure):
    pass
_cairo._fields_ = [
]
cairo_t = _cairo
class _cairo_surface(Structure):
    pass
_cairo_surface._fields_ = [
]
cairo_surface_t = _cairo_surface
class _cairo_matrix(Structure):
    pass
_cairo_matrix._pack_ = 4
_cairo_matrix._fields_ = [
    ('xx', c_double),
    ('yx', c_double),
    ('xy', c_double),
    ('yy', c_double),
    ('x0', c_double),
    ('y0', c_double),
]
cairo_matrix_t = _cairo_matrix
class _cairo_pattern(Structure):
    pass
cairo_pattern_t = _cairo_pattern
_cairo_pattern._fields_ = [
]
cairo_destroy_func_t = CFUNCTYPE(None, c_void_p)
class _cairo_user_data_key(Structure):
    pass
_cairo_user_data_key._fields_ = [
    ('unused', c_int),
]
cairo_user_data_key_t = _cairo_user_data_key

# values for enumeration '_cairo_status'
_cairo_status = c_int # enum
cairo_status_t = _cairo_status

# values for enumeration '_cairo_content'
_cairo_content = c_int # enum
cairo_content_t = _cairo_content
cairo_write_func_t = CFUNCTYPE(cairo_status_t, c_void_p, POINTER(c_ubyte), c_uint)
cairo_read_func_t = CFUNCTYPE(cairo_status_t, c_void_p, POINTER(c_ubyte), c_uint)
cairo_create = libcairo.cairo_create
cairo_create.restype = POINTER(cairo_t)
cairo_create.argtypes = [POINTER(cairo_surface_t)]
cairo_reference = libcairo.cairo_reference
cairo_reference.restype = POINTER(cairo_t)
cairo_reference.argtypes = [POINTER(cairo_t)]
cairo_destroy = libcairo.cairo_destroy
cairo_destroy.restype = None
cairo_destroy.argtypes = [POINTER(cairo_t)]
cairo_save = libcairo.cairo_save
cairo_save.restype = None
cairo_save.argtypes = [POINTER(cairo_t)]
cairo_restore = libcairo.cairo_restore
cairo_restore.restype = None
cairo_restore.argtypes = [POINTER(cairo_t)]
cairo_push_group = libcairo.cairo_push_group
cairo_push_group.restype = None
cairo_push_group.argtypes = [POINTER(cairo_t)]
cairo_push_group_with_content = libcairo.cairo_push_group_with_content
cairo_push_group_with_content.restype = None
cairo_push_group_with_content.argtypes = [POINTER(cairo_t), cairo_content_t]
cairo_pop_group = libcairo.cairo_pop_group
cairo_pop_group.restype = POINTER(cairo_pattern_t)
cairo_pop_group.argtypes = [POINTER(cairo_t)]
cairo_pop_group_to_source = libcairo.cairo_pop_group_to_source
cairo_pop_group_to_source.restype = None
cairo_pop_group_to_source.argtypes = [POINTER(cairo_t)]

# values for enumeration '_cairo_operator'
_cairo_operator = c_int # enum
cairo_operator_t = _cairo_operator
cairo_set_operator = libcairo.cairo_set_operator
cairo_set_operator.restype = None
cairo_set_operator.argtypes = [POINTER(cairo_t), cairo_operator_t]
cairo_set_source = libcairo.cairo_set_source
cairo_set_source.restype = None
cairo_set_source.argtypes = [POINTER(cairo_t), POINTER(cairo_pattern_t)]
cairo_set_source_rgb = libcairo.cairo_set_source_rgb
cairo_set_source_rgb.restype = None
cairo_set_source_rgb.argtypes = [POINTER(cairo_t), c_double, c_double, c_double]
cairo_set_source_rgba = libcairo.cairo_set_source_rgba
cairo_set_source_rgba.restype = None
cairo_set_source_rgba.argtypes = [POINTER(cairo_t), c_double, c_double, c_double, c_double]
cairo_set_source_surface = libcairo.cairo_set_source_surface
cairo_set_source_surface.restype = None
cairo_set_source_surface.argtypes = [POINTER(cairo_t), POINTER(cairo_surface_t), c_double, c_double]
cairo_set_tolerance = libcairo.cairo_set_tolerance
cairo_set_tolerance.restype = None
cairo_set_tolerance.argtypes = [POINTER(cairo_t), c_double]

# values for enumeration '_cairo_antialias'
_cairo_antialias = c_int # enum
cairo_antialias_t = _cairo_antialias
cairo_set_antialias = libcairo.cairo_set_antialias
cairo_set_antialias.restype = None
cairo_set_antialias.argtypes = [POINTER(cairo_t), cairo_antialias_t]

# values for enumeration '_cairo_fill_rule'
_cairo_fill_rule = c_int # enum
cairo_fill_rule_t = _cairo_fill_rule
cairo_set_fill_rule = libcairo.cairo_set_fill_rule
cairo_set_fill_rule.restype = None
cairo_set_fill_rule.argtypes = [POINTER(cairo_t), cairo_fill_rule_t]
cairo_set_line_width = libcairo.cairo_set_line_width
cairo_set_line_width.restype = None
cairo_set_line_width.argtypes = [POINTER(cairo_t), c_double]

# values for enumeration '_cairo_line_cap'
_cairo_line_cap = c_int # enum
cairo_line_cap_t = _cairo_line_cap
cairo_set_line_cap = libcairo.cairo_set_line_cap
cairo_set_line_cap.restype = None
cairo_set_line_cap.argtypes = [POINTER(cairo_t), cairo_line_cap_t]

# values for enumeration '_cairo_line_join'
_cairo_line_join = c_int # enum
cairo_line_join_t = _cairo_line_join
cairo_set_line_join = libcairo.cairo_set_line_join
cairo_set_line_join.restype = None
cairo_set_line_join.argtypes = [POINTER(cairo_t), cairo_line_join_t]
cairo_set_dash = libcairo.cairo_set_dash
cairo_set_dash.restype = None
cairo_set_dash.argtypes = [POINTER(cairo_t), POINTER(c_double), c_int, c_double]
cairo_set_miter_limit = libcairo.cairo_set_miter_limit
cairo_set_miter_limit.restype = None
cairo_set_miter_limit.argtypes = [POINTER(cairo_t), c_double]
cairo_translate = libcairo.cairo_translate
cairo_translate.restype = None
cairo_translate.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_scale = libcairo.cairo_scale
cairo_scale.restype = None
cairo_scale.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_rotate = libcairo.cairo_rotate
cairo_rotate.restype = None
cairo_rotate.argtypes = [POINTER(cairo_t), c_double]
cairo_transform = libcairo.cairo_transform
cairo_transform.restype = None
cairo_transform.argtypes = [POINTER(cairo_t), POINTER(cairo_matrix_t)]
cairo_set_matrix = libcairo.cairo_set_matrix
cairo_set_matrix.restype = None
cairo_set_matrix.argtypes = [POINTER(cairo_t), POINTER(cairo_matrix_t)]
cairo_identity_matrix = libcairo.cairo_identity_matrix
cairo_identity_matrix.restype = None
cairo_identity_matrix.argtypes = [POINTER(cairo_t)]
cairo_user_to_device = libcairo.cairo_user_to_device
cairo_user_to_device.restype = None
cairo_user_to_device.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double)]
cairo_user_to_device_distance = libcairo.cairo_user_to_device_distance
cairo_user_to_device_distance.restype = None
cairo_user_to_device_distance.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double)]
cairo_device_to_user = libcairo.cairo_device_to_user
cairo_device_to_user.restype = None
cairo_device_to_user.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double)]
cairo_device_to_user_distance = libcairo.cairo_device_to_user_distance
cairo_device_to_user_distance.restype = None
cairo_device_to_user_distance.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double)]
cairo_new_path = libcairo.cairo_new_path
cairo_new_path.restype = None
cairo_new_path.argtypes = [POINTER(cairo_t)]
cairo_move_to = libcairo.cairo_move_to
cairo_move_to.restype = None
cairo_move_to.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_new_sub_path = libcairo.cairo_new_sub_path
cairo_new_sub_path.restype = None
cairo_new_sub_path.argtypes = [POINTER(cairo_t)]
cairo_line_to = libcairo.cairo_line_to
cairo_line_to.restype = None
cairo_line_to.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_curve_to = libcairo.cairo_curve_to
cairo_curve_to.restype = None
cairo_curve_to.argtypes = [POINTER(cairo_t), c_double, c_double, c_double, c_double, c_double, c_double]
cairo_arc = libcairo.cairo_arc
cairo_arc.restype = None
cairo_arc.argtypes = [POINTER(cairo_t), c_double, c_double, c_double, c_double, c_double]
cairo_arc_negative = libcairo.cairo_arc_negative
cairo_arc_negative.restype = None
cairo_arc_negative.argtypes = [POINTER(cairo_t), c_double, c_double, c_double, c_double, c_double]
cairo_rel_move_to = libcairo.cairo_rel_move_to
cairo_rel_move_to.restype = None
cairo_rel_move_to.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_rel_line_to = libcairo.cairo_rel_line_to
cairo_rel_line_to.restype = None
cairo_rel_line_to.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_rel_curve_to = libcairo.cairo_rel_curve_to
cairo_rel_curve_to.restype = None
cairo_rel_curve_to.argtypes = [POINTER(cairo_t), c_double, c_double, c_double, c_double, c_double, c_double]
cairo_rectangle = libcairo.cairo_rectangle
cairo_rectangle.restype = None
cairo_rectangle.argtypes = [POINTER(cairo_t), c_double, c_double, c_double, c_double]
cairo_close_path = libcairo.cairo_close_path
cairo_close_path.restype = None
cairo_close_path.argtypes = [POINTER(cairo_t)]
cairo_paint = libcairo.cairo_paint
cairo_paint.restype = None
cairo_paint.argtypes = [POINTER(cairo_t)]
cairo_paint_with_alpha = libcairo.cairo_paint_with_alpha
cairo_paint_with_alpha.restype = None
cairo_paint_with_alpha.argtypes = [POINTER(cairo_t), c_double]
cairo_mask = libcairo.cairo_mask
cairo_mask.restype = None
cairo_mask.argtypes = [POINTER(cairo_t), POINTER(cairo_pattern_t)]
cairo_mask_surface = libcairo.cairo_mask_surface
cairo_mask_surface.restype = None
cairo_mask_surface.argtypes = [POINTER(cairo_t), POINTER(cairo_surface_t), c_double, c_double]
cairo_stroke = libcairo.cairo_stroke
cairo_stroke.restype = None
cairo_stroke.argtypes = [POINTER(cairo_t)]
cairo_stroke_preserve = libcairo.cairo_stroke_preserve
cairo_stroke_preserve.restype = None
cairo_stroke_preserve.argtypes = [POINTER(cairo_t)]
cairo_fill = libcairo.cairo_fill
cairo_fill.restype = None
cairo_fill.argtypes = [POINTER(cairo_t)]
cairo_fill_preserve = libcairo.cairo_fill_preserve
cairo_fill_preserve.restype = None
cairo_fill_preserve.argtypes = [POINTER(cairo_t)]
cairo_copy_page = libcairo.cairo_copy_page
cairo_copy_page.restype = None
cairo_copy_page.argtypes = [POINTER(cairo_t)]
cairo_show_page = libcairo.cairo_show_page
cairo_show_page.restype = None
cairo_show_page.argtypes = [POINTER(cairo_t)]
cairo_in_stroke = libcairo.cairo_in_stroke
cairo_in_stroke.restype = cairo_bool_t
cairo_in_stroke.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_in_fill = libcairo.cairo_in_fill
cairo_in_fill.restype = cairo_bool_t
cairo_in_fill.argtypes = [POINTER(cairo_t), c_double, c_double]
cairo_stroke_extents = libcairo.cairo_stroke_extents
cairo_stroke_extents.restype = None
cairo_stroke_extents.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double)]
cairo_fill_extents = libcairo.cairo_fill_extents
cairo_fill_extents.restype = None
cairo_fill_extents.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double)]
cairo_reset_clip = libcairo.cairo_reset_clip
cairo_reset_clip.restype = None
cairo_reset_clip.argtypes = [POINTER(cairo_t)]
cairo_clip = libcairo.cairo_clip
cairo_clip.restype = None
cairo_clip.argtypes = [POINTER(cairo_t)]
cairo_clip_preserve = libcairo.cairo_clip_preserve
cairo_clip_preserve.restype = None
cairo_clip_preserve.argtypes = [POINTER(cairo_t)]
class _cairo_scaled_font(Structure):
    pass
_cairo_scaled_font._fields_ = [
]
cairo_scaled_font_t = _cairo_scaled_font
class _cairo_font_face(Structure):
    pass
_cairo_font_face._fields_ = [
]
cairo_font_face_t = _cairo_font_face
class cairo_glyph_t(Structure):
    pass
cairo_glyph_t._pack_ = 4
cairo_glyph_t._fields_ = [
    ('index', c_ulong),
    ('x', c_double),
    ('y', c_double),
]
class cairo_text_extents_t(Structure):
    pass
cairo_text_extents_t._pack_ = 4
cairo_text_extents_t._fields_ = [
    ('x_bearing', c_double),
    ('y_bearing', c_double),
    ('width', c_double),
    ('height', c_double),
    ('x_advance', c_double),
    ('y_advance', c_double),
]
class cairo_font_extents_t(Structure):
    pass
cairo_font_extents_t._pack_ = 4
cairo_font_extents_t._fields_ = [
    ('ascent', c_double),
    ('descent', c_double),
    ('height', c_double),
    ('max_x_advance', c_double),
    ('max_y_advance', c_double),
]

# values for enumeration '_cairo_font_slant'
_cairo_font_slant = c_int # enum
cairo_font_slant_t = _cairo_font_slant

# values for enumeration '_cairo_font_weight'
_cairo_font_weight = c_int # enum
cairo_font_weight_t = _cairo_font_weight

# values for enumeration '_cairo_subpixel_order'
_cairo_subpixel_order = c_int # enum
cairo_subpixel_order_t = _cairo_subpixel_order

# values for enumeration '_cairo_hint_style'
_cairo_hint_style = c_int # enum
cairo_hint_style_t = _cairo_hint_style

# values for enumeration '_cairo_hint_metrics'
_cairo_hint_metrics = c_int # enum
cairo_hint_metrics_t = _cairo_hint_metrics
class _cairo_font_options(Structure):
    pass
cairo_font_options_t = _cairo_font_options
_cairo_font_options._fields_ = [
]
cairo_font_options_create = libcairo.cairo_font_options_create
cairo_font_options_create.restype = POINTER(cairo_font_options_t)
cairo_font_options_create.argtypes = []
cairo_font_options_copy = libcairo.cairo_font_options_copy
cairo_font_options_copy.restype = POINTER(cairo_font_options_t)
cairo_font_options_copy.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_destroy = libcairo.cairo_font_options_destroy
cairo_font_options_destroy.restype = None
cairo_font_options_destroy.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_status = libcairo.cairo_font_options_status
cairo_font_options_status.restype = cairo_status_t
cairo_font_options_status.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_merge = libcairo.cairo_font_options_merge
cairo_font_options_merge.restype = None
cairo_font_options_merge.argtypes = [POINTER(cairo_font_options_t), POINTER(cairo_font_options_t)]
cairo_font_options_equal = libcairo.cairo_font_options_equal
cairo_font_options_equal.restype = cairo_bool_t
cairo_font_options_equal.argtypes = [POINTER(cairo_font_options_t), POINTER(cairo_font_options_t)]
cairo_font_options_hash = libcairo.cairo_font_options_hash
cairo_font_options_hash.restype = c_ulong
cairo_font_options_hash.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_set_antialias = libcairo.cairo_font_options_set_antialias
cairo_font_options_set_antialias.restype = None
cairo_font_options_set_antialias.argtypes = [POINTER(cairo_font_options_t), cairo_antialias_t]
cairo_font_options_get_antialias = libcairo.cairo_font_options_get_antialias
cairo_font_options_get_antialias.restype = cairo_antialias_t
cairo_font_options_get_antialias.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_set_subpixel_order = libcairo.cairo_font_options_set_subpixel_order
cairo_font_options_set_subpixel_order.restype = None
cairo_font_options_set_subpixel_order.argtypes = [POINTER(cairo_font_options_t), cairo_subpixel_order_t]
cairo_font_options_get_subpixel_order = libcairo.cairo_font_options_get_subpixel_order
cairo_font_options_get_subpixel_order.restype = cairo_subpixel_order_t
cairo_font_options_get_subpixel_order.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_set_hint_style = libcairo.cairo_font_options_set_hint_style
cairo_font_options_set_hint_style.restype = None
cairo_font_options_set_hint_style.argtypes = [POINTER(cairo_font_options_t), cairo_hint_style_t]
cairo_font_options_get_hint_style = libcairo.cairo_font_options_get_hint_style
cairo_font_options_get_hint_style.restype = cairo_hint_style_t
cairo_font_options_get_hint_style.argtypes = [POINTER(cairo_font_options_t)]
cairo_font_options_set_hint_metrics = libcairo.cairo_font_options_set_hint_metrics
cairo_font_options_set_hint_metrics.restype = None
cairo_font_options_set_hint_metrics.argtypes = [POINTER(cairo_font_options_t), cairo_hint_metrics_t]
cairo_font_options_get_hint_metrics = libcairo.cairo_font_options_get_hint_metrics
cairo_font_options_get_hint_metrics.restype = cairo_hint_metrics_t
cairo_font_options_get_hint_metrics.argtypes = [POINTER(cairo_font_options_t)]
cairo_select_font_face = libcairo.cairo_select_font_face
cairo_select_font_face.restype = None
cairo_select_font_face.argtypes = [POINTER(cairo_t), STRING, cairo_font_slant_t, cairo_font_weight_t]
cairo_set_font_size = libcairo.cairo_set_font_size
cairo_set_font_size.restype = None
cairo_set_font_size.argtypes = [POINTER(cairo_t), c_double]
cairo_set_font_matrix = libcairo.cairo_set_font_matrix
cairo_set_font_matrix.restype = None
cairo_set_font_matrix.argtypes = [POINTER(cairo_t), POINTER(cairo_matrix_t)]
cairo_get_font_matrix = libcairo.cairo_get_font_matrix
cairo_get_font_matrix.restype = None
cairo_get_font_matrix.argtypes = [POINTER(cairo_t), POINTER(cairo_matrix_t)]
cairo_set_font_options = libcairo.cairo_set_font_options
cairo_set_font_options.restype = None
cairo_set_font_options.argtypes = [POINTER(cairo_t), POINTER(cairo_font_options_t)]
cairo_get_font_options = libcairo.cairo_get_font_options
cairo_get_font_options.restype = None
cairo_get_font_options.argtypes = [POINTER(cairo_t), POINTER(cairo_font_options_t)]
cairo_set_scaled_font = libcairo.cairo_set_scaled_font
cairo_set_scaled_font.restype = None
cairo_set_scaled_font.argtypes = [POINTER(cairo_t), POINTER(cairo_scaled_font_t)]
cairo_show_text = libcairo.cairo_show_text
cairo_show_text.restype = None
cairo_show_text.argtypes = [POINTER(cairo_t), STRING]
cairo_show_glyphs = libcairo.cairo_show_glyphs
cairo_show_glyphs.restype = None
cairo_show_glyphs.argtypes = [POINTER(cairo_t), POINTER(cairo_glyph_t), c_int]
cairo_get_font_face = libcairo.cairo_get_font_face
cairo_get_font_face.restype = POINTER(cairo_font_face_t)
cairo_get_font_face.argtypes = [POINTER(cairo_t)]
cairo_font_extents = libcairo.cairo_font_extents
cairo_font_extents.restype = None
cairo_font_extents.argtypes = [POINTER(cairo_t), POINTER(cairo_font_extents_t)]
cairo_set_font_face = libcairo.cairo_set_font_face
cairo_set_font_face.restype = None
cairo_set_font_face.argtypes = [POINTER(cairo_t), POINTER(cairo_font_face_t)]
cairo_text_extents = libcairo.cairo_text_extents
cairo_text_extents.restype = None
cairo_text_extents.argtypes = [POINTER(cairo_t), STRING, POINTER(cairo_text_extents_t)]
cairo_glyph_extents = libcairo.cairo_glyph_extents
cairo_glyph_extents.restype = None
cairo_glyph_extents.argtypes = [POINTER(cairo_t), POINTER(cairo_glyph_t), c_int, POINTER(cairo_text_extents_t)]
cairo_text_path = libcairo.cairo_text_path
cairo_text_path.restype = None
cairo_text_path.argtypes = [POINTER(cairo_t), STRING]
cairo_glyph_path = libcairo.cairo_glyph_path
cairo_glyph_path.restype = None
cairo_glyph_path.argtypes = [POINTER(cairo_t), POINTER(cairo_glyph_t), c_int]
cairo_font_face_reference = libcairo.cairo_font_face_reference
cairo_font_face_reference.restype = POINTER(cairo_font_face_t)
cairo_font_face_reference.argtypes = [POINTER(cairo_font_face_t)]
cairo_font_face_destroy = libcairo.cairo_font_face_destroy
cairo_font_face_destroy.restype = None
cairo_font_face_destroy.argtypes = [POINTER(cairo_font_face_t)]
cairo_font_face_status = libcairo.cairo_font_face_status
cairo_font_face_status.restype = cairo_status_t
cairo_font_face_status.argtypes = [POINTER(cairo_font_face_t)]

# values for enumeration '_cairo_font_type'
_cairo_font_type = c_int # enum
cairo_font_type_t = _cairo_font_type
cairo_font_face_get_type = libcairo.cairo_font_face_get_type
cairo_font_face_get_type.restype = cairo_font_type_t
cairo_font_face_get_type.argtypes = [POINTER(cairo_font_face_t)]
cairo_font_face_get_user_data = libcairo.cairo_font_face_get_user_data
cairo_font_face_get_user_data.restype = c_void_p
cairo_font_face_get_user_data.argtypes = [POINTER(cairo_font_face_t), POINTER(cairo_user_data_key_t)]
cairo_font_face_set_user_data = libcairo.cairo_font_face_set_user_data
cairo_font_face_set_user_data.restype = cairo_status_t
cairo_font_face_set_user_data.argtypes = [POINTER(cairo_font_face_t), POINTER(cairo_user_data_key_t), c_void_p, cairo_destroy_func_t]
cairo_scaled_font_create = libcairo.cairo_scaled_font_create
cairo_scaled_font_create.restype = POINTER(cairo_scaled_font_t)
cairo_scaled_font_create.argtypes = [POINTER(cairo_font_face_t), POINTER(cairo_matrix_t), POINTER(cairo_matrix_t), POINTER(cairo_font_options_t)]
cairo_scaled_font_reference = libcairo.cairo_scaled_font_reference
cairo_scaled_font_reference.restype = POINTER(cairo_scaled_font_t)
cairo_scaled_font_reference.argtypes = [POINTER(cairo_scaled_font_t)]
cairo_scaled_font_destroy = libcairo.cairo_scaled_font_destroy
cairo_scaled_font_destroy.restype = None
cairo_scaled_font_destroy.argtypes = [POINTER(cairo_scaled_font_t)]
cairo_scaled_font_status = libcairo.cairo_scaled_font_status
cairo_scaled_font_status.restype = cairo_status_t
cairo_scaled_font_status.argtypes = [POINTER(cairo_scaled_font_t)]
cairo_scaled_font_get_type = libcairo.cairo_scaled_font_get_type
cairo_scaled_font_get_type.restype = cairo_font_type_t
cairo_scaled_font_get_type.argtypes = [POINTER(cairo_scaled_font_t)]
cairo_scaled_font_extents = libcairo.cairo_scaled_font_extents
cairo_scaled_font_extents.restype = None
cairo_scaled_font_extents.argtypes = [POINTER(cairo_scaled_font_t), POINTER(cairo_font_extents_t)]
cairo_scaled_font_text_extents = libcairo.cairo_scaled_font_text_extents
cairo_scaled_font_text_extents.restype = None
cairo_scaled_font_text_extents.argtypes = [POINTER(cairo_scaled_font_t), STRING, POINTER(cairo_text_extents_t)]
cairo_scaled_font_glyph_extents = libcairo.cairo_scaled_font_glyph_extents
cairo_scaled_font_glyph_extents.restype = None
cairo_scaled_font_glyph_extents.argtypes = [POINTER(cairo_scaled_font_t), POINTER(cairo_glyph_t), c_int, POINTER(cairo_text_extents_t)]
cairo_scaled_font_get_font_face = libcairo.cairo_scaled_font_get_font_face
cairo_scaled_font_get_font_face.restype = POINTER(cairo_font_face_t)
cairo_scaled_font_get_font_face.argtypes = [POINTER(cairo_scaled_font_t)]
cairo_scaled_font_get_font_matrix = libcairo.cairo_scaled_font_get_font_matrix
cairo_scaled_font_get_font_matrix.restype = None
cairo_scaled_font_get_font_matrix.argtypes = [POINTER(cairo_scaled_font_t), POINTER(cairo_matrix_t)]
cairo_scaled_font_get_ctm = libcairo.cairo_scaled_font_get_ctm
cairo_scaled_font_get_ctm.restype = None
cairo_scaled_font_get_ctm.argtypes = [POINTER(cairo_scaled_font_t), POINTER(cairo_matrix_t)]
cairo_scaled_font_get_font_options = libcairo.cairo_scaled_font_get_font_options
cairo_scaled_font_get_font_options.restype = None
cairo_scaled_font_get_font_options.argtypes = [POINTER(cairo_scaled_font_t), POINTER(cairo_font_options_t)]
cairo_get_operator = libcairo.cairo_get_operator
cairo_get_operator.restype = cairo_operator_t
cairo_get_operator.argtypes = [POINTER(cairo_t)]
cairo_get_source = libcairo.cairo_get_source
cairo_get_source.restype = POINTER(cairo_pattern_t)
cairo_get_source.argtypes = [POINTER(cairo_t)]
cairo_get_tolerance = libcairo.cairo_get_tolerance
cairo_get_tolerance.restype = c_double
cairo_get_tolerance.argtypes = [POINTER(cairo_t)]
cairo_get_antialias = libcairo.cairo_get_antialias
cairo_get_antialias.restype = cairo_antialias_t
cairo_get_antialias.argtypes = [POINTER(cairo_t)]
cairo_get_current_point = libcairo.cairo_get_current_point
cairo_get_current_point.restype = None
cairo_get_current_point.argtypes = [POINTER(cairo_t), POINTER(c_double), POINTER(c_double)]
cairo_get_fill_rule = libcairo.cairo_get_fill_rule
cairo_get_fill_rule.restype = cairo_fill_rule_t
cairo_get_fill_rule.argtypes = [POINTER(cairo_t)]
cairo_get_line_width = libcairo.cairo_get_line_width
cairo_get_line_width.restype = c_double
cairo_get_line_width.argtypes = [POINTER(cairo_t)]
cairo_get_line_cap = libcairo.cairo_get_line_cap
cairo_get_line_cap.restype = cairo_line_cap_t
cairo_get_line_cap.argtypes = [POINTER(cairo_t)]
cairo_get_line_join = libcairo.cairo_get_line_join
cairo_get_line_join.restype = cairo_line_join_t
cairo_get_line_join.argtypes = [POINTER(cairo_t)]
cairo_get_miter_limit = libcairo.cairo_get_miter_limit
cairo_get_miter_limit.restype = c_double
cairo_get_miter_limit.argtypes = [POINTER(cairo_t)]
cairo_get_matrix = libcairo.cairo_get_matrix
cairo_get_matrix.restype = None
cairo_get_matrix.argtypes = [POINTER(cairo_t), POINTER(cairo_matrix_t)]
cairo_get_target = libcairo.cairo_get_target
cairo_get_target.restype = POINTER(cairo_surface_t)
cairo_get_target.argtypes = [POINTER(cairo_t)]
cairo_get_group_target = libcairo.cairo_get_group_target
cairo_get_group_target.restype = POINTER(cairo_surface_t)
cairo_get_group_target.argtypes = [POINTER(cairo_t)]

# values for enumeration '_cairo_path_data_type'
_cairo_path_data_type = c_int # enum
cairo_path_data_type_t = _cairo_path_data_type
class _cairo_path_data_t(Union):
    pass
cairo_path_data_t = _cairo_path_data_t
class N18_cairo_path_data_t3DOT_3E(Structure):
    pass
N18_cairo_path_data_t3DOT_3E._fields_ = [
    ('type', cairo_path_data_type_t),
    ('length', c_int),
]
class N18_cairo_path_data_t3DOT_4E(Structure):
    pass
N18_cairo_path_data_t3DOT_4E._pack_ = 4
N18_cairo_path_data_t3DOT_4E._fields_ = [
    ('x', c_double),
    ('y', c_double),
]
_cairo_path_data_t._fields_ = [
    ('header', N18_cairo_path_data_t3DOT_3E),
    ('point', N18_cairo_path_data_t3DOT_4E),
]
class cairo_path(Structure):
    pass
cairo_path._fields_ = [
    ('status', cairo_status_t),
    ('data', POINTER(cairo_path_data_t)),
    ('num_data', c_int),
]
cairo_path_t = cairo_path
cairo_copy_path = libcairo.cairo_copy_path
cairo_copy_path.restype = POINTER(cairo_path_t)
cairo_copy_path.argtypes = [POINTER(cairo_t)]
cairo_copy_path_flat = libcairo.cairo_copy_path_flat
cairo_copy_path_flat.restype = POINTER(cairo_path_t)
cairo_copy_path_flat.argtypes = [POINTER(cairo_t)]
cairo_append_path = libcairo.cairo_append_path
cairo_append_path.restype = None
cairo_append_path.argtypes = [POINTER(cairo_t), POINTER(cairo_path_t)]
cairo_path_destroy = libcairo.cairo_path_destroy
cairo_path_destroy.restype = None
cairo_path_destroy.argtypes = [POINTER(cairo_path_t)]
cairo_status = libcairo.cairo_status
cairo_status.restype = cairo_status_t
cairo_status.argtypes = [POINTER(cairo_t)]
cairo_status_to_string = libcairo.cairo_status_to_string
cairo_status_to_string.restype = STRING
cairo_status_to_string.argtypes = [cairo_status_t]
cairo_surface_create_similar = libcairo.cairo_surface_create_similar
cairo_surface_create_similar.restype = POINTER(cairo_surface_t)
cairo_surface_create_similar.argtypes = [POINTER(cairo_surface_t), cairo_content_t, c_int, c_int]
cairo_surface_reference = libcairo.cairo_surface_reference
cairo_surface_reference.restype = POINTER(cairo_surface_t)
cairo_surface_reference.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_finish = libcairo.cairo_surface_finish
cairo_surface_finish.restype = None
cairo_surface_finish.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_destroy = libcairo.cairo_surface_destroy
cairo_surface_destroy.restype = None
cairo_surface_destroy.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_status = libcairo.cairo_surface_status
cairo_surface_status.restype = cairo_status_t
cairo_surface_status.argtypes = [POINTER(cairo_surface_t)]

# values for enumeration '_cairo_surface_type'
_cairo_surface_type = c_int # enum
cairo_surface_type_t = _cairo_surface_type
cairo_surface_get_type = libcairo.cairo_surface_get_type
cairo_surface_get_type.restype = cairo_surface_type_t
cairo_surface_get_type.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_get_content = libcairo.cairo_surface_get_content
cairo_surface_get_content.restype = cairo_content_t
cairo_surface_get_content.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_write_to_png = libcairo.cairo_surface_write_to_png
cairo_surface_write_to_png.restype = cairo_status_t
cairo_surface_write_to_png.argtypes = [POINTER(cairo_surface_t), STRING]
cairo_surface_write_to_png_stream = libcairo.cairo_surface_write_to_png_stream
cairo_surface_write_to_png_stream.restype = cairo_status_t
cairo_surface_write_to_png_stream.argtypes = [POINTER(cairo_surface_t), cairo_write_func_t, c_void_p]
cairo_surface_get_user_data = libcairo.cairo_surface_get_user_data
cairo_surface_get_user_data.restype = c_void_p
cairo_surface_get_user_data.argtypes = [POINTER(cairo_surface_t), POINTER(cairo_user_data_key_t)]
cairo_surface_set_user_data = libcairo.cairo_surface_set_user_data
cairo_surface_set_user_data.restype = cairo_status_t
cairo_surface_set_user_data.argtypes = [POINTER(cairo_surface_t), POINTER(cairo_user_data_key_t), c_void_p, cairo_destroy_func_t]
cairo_surface_get_font_options = libcairo.cairo_surface_get_font_options
cairo_surface_get_font_options.restype = None
cairo_surface_get_font_options.argtypes = [POINTER(cairo_surface_t), POINTER(cairo_font_options_t)]
cairo_surface_flush = libcairo.cairo_surface_flush
cairo_surface_flush.restype = None
cairo_surface_flush.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_mark_dirty = libcairo.cairo_surface_mark_dirty
cairo_surface_mark_dirty.restype = None
cairo_surface_mark_dirty.argtypes = [POINTER(cairo_surface_t)]
cairo_surface_mark_dirty_rectangle = libcairo.cairo_surface_mark_dirty_rectangle
cairo_surface_mark_dirty_rectangle.restype = None
cairo_surface_mark_dirty_rectangle.argtypes = [POINTER(cairo_surface_t), c_int, c_int, c_int, c_int]
cairo_surface_set_device_offset = libcairo.cairo_surface_set_device_offset
cairo_surface_set_device_offset.restype = None
cairo_surface_set_device_offset.argtypes = [POINTER(cairo_surface_t), c_double, c_double]
cairo_surface_get_device_offset = libcairo.cairo_surface_get_device_offset
cairo_surface_get_device_offset.restype = None
cairo_surface_get_device_offset.argtypes = [POINTER(cairo_surface_t), POINTER(c_double), POINTER(c_double)]
cairo_surface_set_fallback_resolution = libcairo.cairo_surface_set_fallback_resolution
cairo_surface_set_fallback_resolution.restype = None
cairo_surface_set_fallback_resolution.argtypes = [POINTER(cairo_surface_t), c_double, c_double]

# values for enumeration '_cairo_format'
_cairo_format = c_int # enum
cairo_format_t = _cairo_format
cairo_image_surface_create = libcairo.cairo_image_surface_create
cairo_image_surface_create.restype = POINTER(cairo_surface_t)
cairo_image_surface_create.argtypes = [cairo_format_t, c_int, c_int]
cairo_image_surface_create_for_data = libcairo.cairo_image_surface_create_for_data
cairo_image_surface_create_for_data.restype = POINTER(cairo_surface_t)
cairo_image_surface_create_for_data.argtypes = [POINTER(c_ubyte), cairo_format_t, c_int, c_int, c_int]
cairo_image_surface_get_data = libcairo.cairo_image_surface_get_data
cairo_image_surface_get_data.restype = POINTER(c_ubyte)
cairo_image_surface_get_data.argtypes = [POINTER(cairo_surface_t)]
cairo_image_surface_get_format = libcairo.cairo_image_surface_get_format
cairo_image_surface_get_format.restype = cairo_format_t
cairo_image_surface_get_format.argtypes = [POINTER(cairo_surface_t)]
cairo_image_surface_get_width = libcairo.cairo_image_surface_get_width
cairo_image_surface_get_width.restype = c_int
cairo_image_surface_get_width.argtypes = [POINTER(cairo_surface_t)]
cairo_image_surface_get_height = libcairo.cairo_image_surface_get_height
cairo_image_surface_get_height.restype = c_int
cairo_image_surface_get_height.argtypes = [POINTER(cairo_surface_t)]
cairo_image_surface_get_stride = libcairo.cairo_image_surface_get_stride
cairo_image_surface_get_stride.restype = c_int
cairo_image_surface_get_stride.argtypes = [POINTER(cairo_surface_t)]
cairo_image_surface_create_from_png = libcairo.cairo_image_surface_create_from_png
cairo_image_surface_create_from_png.restype = POINTER(cairo_surface_t)
cairo_image_surface_create_from_png.argtypes = [STRING]
cairo_image_surface_create_from_png_stream = libcairo.cairo_image_surface_create_from_png_stream
cairo_image_surface_create_from_png_stream.restype = POINTER(cairo_surface_t)
cairo_image_surface_create_from_png_stream.argtypes = [cairo_read_func_t, c_void_p]
cairo_pattern_create_rgb = libcairo.cairo_pattern_create_rgb
cairo_pattern_create_rgb.restype = POINTER(cairo_pattern_t)
cairo_pattern_create_rgb.argtypes = [c_double, c_double, c_double]
cairo_pattern_create_rgba = libcairo.cairo_pattern_create_rgba
cairo_pattern_create_rgba.restype = POINTER(cairo_pattern_t)
cairo_pattern_create_rgba.argtypes = [c_double, c_double, c_double, c_double]
cairo_pattern_create_for_surface = libcairo.cairo_pattern_create_for_surface
cairo_pattern_create_for_surface.restype = POINTER(cairo_pattern_t)
cairo_pattern_create_for_surface.argtypes = [POINTER(cairo_surface_t)]
cairo_pattern_create_linear = libcairo.cairo_pattern_create_linear
cairo_pattern_create_linear.restype = POINTER(cairo_pattern_t)
cairo_pattern_create_linear.argtypes = [c_double, c_double, c_double, c_double]
cairo_pattern_create_radial = libcairo.cairo_pattern_create_radial
cairo_pattern_create_radial.restype = POINTER(cairo_pattern_t)
cairo_pattern_create_radial.argtypes = [c_double, c_double, c_double, c_double, c_double, c_double]
cairo_pattern_reference = libcairo.cairo_pattern_reference
cairo_pattern_reference.restype = POINTER(cairo_pattern_t)
cairo_pattern_reference.argtypes = [POINTER(cairo_pattern_t)]
cairo_pattern_destroy = libcairo.cairo_pattern_destroy
cairo_pattern_destroy.restype = None
cairo_pattern_destroy.argtypes = [POINTER(cairo_pattern_t)]
cairo_pattern_status = libcairo.cairo_pattern_status
cairo_pattern_status.restype = cairo_status_t
cairo_pattern_status.argtypes = [POINTER(cairo_pattern_t)]

# values for enumeration '_cairo_pattern_type'
_cairo_pattern_type = c_int # enum
cairo_pattern_type_t = _cairo_pattern_type
cairo_pattern_get_type = libcairo.cairo_pattern_get_type
cairo_pattern_get_type.restype = cairo_pattern_type_t
cairo_pattern_get_type.argtypes = [POINTER(cairo_pattern_t)]
cairo_pattern_add_color_stop_rgb = libcairo.cairo_pattern_add_color_stop_rgb
cairo_pattern_add_color_stop_rgb.restype = None
cairo_pattern_add_color_stop_rgb.argtypes = [POINTER(cairo_pattern_t), c_double, c_double, c_double, c_double]
cairo_pattern_add_color_stop_rgba = libcairo.cairo_pattern_add_color_stop_rgba
cairo_pattern_add_color_stop_rgba.restype = None
cairo_pattern_add_color_stop_rgba.argtypes = [POINTER(cairo_pattern_t), c_double, c_double, c_double, c_double, c_double]
cairo_pattern_set_matrix = libcairo.cairo_pattern_set_matrix
cairo_pattern_set_matrix.restype = None
cairo_pattern_set_matrix.argtypes = [POINTER(cairo_pattern_t), POINTER(cairo_matrix_t)]
cairo_pattern_get_matrix = libcairo.cairo_pattern_get_matrix
cairo_pattern_get_matrix.restype = None
cairo_pattern_get_matrix.argtypes = [POINTER(cairo_pattern_t), POINTER(cairo_matrix_t)]

# values for enumeration '_cairo_extend'
_cairo_extend = c_int # enum
cairo_extend_t = _cairo_extend
cairo_pattern_set_extend = libcairo.cairo_pattern_set_extend
cairo_pattern_set_extend.restype = None
cairo_pattern_set_extend.argtypes = [POINTER(cairo_pattern_t), cairo_extend_t]
cairo_pattern_get_extend = libcairo.cairo_pattern_get_extend
cairo_pattern_get_extend.restype = cairo_extend_t
cairo_pattern_get_extend.argtypes = [POINTER(cairo_pattern_t)]

# values for enumeration '_cairo_filter'
_cairo_filter = c_int # enum
cairo_filter_t = _cairo_filter
cairo_pattern_set_filter = libcairo.cairo_pattern_set_filter
cairo_pattern_set_filter.restype = None
cairo_pattern_set_filter.argtypes = [POINTER(cairo_pattern_t), cairo_filter_t]
cairo_pattern_get_filter = libcairo.cairo_pattern_get_filter
cairo_pattern_get_filter.restype = cairo_filter_t
cairo_pattern_get_filter.argtypes = [POINTER(cairo_pattern_t)]
cairo_matrix_init = libcairo.cairo_matrix_init
cairo_matrix_init.restype = None
cairo_matrix_init.argtypes = [POINTER(cairo_matrix_t), c_double, c_double, c_double, c_double, c_double, c_double]
cairo_matrix_init_identity = libcairo.cairo_matrix_init_identity
cairo_matrix_init_identity.restype = None
cairo_matrix_init_identity.argtypes = [POINTER(cairo_matrix_t)]
cairo_matrix_init_translate = libcairo.cairo_matrix_init_translate
cairo_matrix_init_translate.restype = None
cairo_matrix_init_translate.argtypes = [POINTER(cairo_matrix_t), c_double, c_double]
cairo_matrix_init_scale = libcairo.cairo_matrix_init_scale
cairo_matrix_init_scale.restype = None
cairo_matrix_init_scale.argtypes = [POINTER(cairo_matrix_t), c_double, c_double]
cairo_matrix_init_rotate = libcairo.cairo_matrix_init_rotate
cairo_matrix_init_rotate.restype = None
cairo_matrix_init_rotate.argtypes = [POINTER(cairo_matrix_t), c_double]
cairo_matrix_translate = libcairo.cairo_matrix_translate
cairo_matrix_translate.restype = None
cairo_matrix_translate.argtypes = [POINTER(cairo_matrix_t), c_double, c_double]
cairo_matrix_scale = libcairo.cairo_matrix_scale
cairo_matrix_scale.restype = None
cairo_matrix_scale.argtypes = [POINTER(cairo_matrix_t), c_double, c_double]
cairo_matrix_rotate = libcairo.cairo_matrix_rotate
cairo_matrix_rotate.restype = None
cairo_matrix_rotate.argtypes = [POINTER(cairo_matrix_t), c_double]
cairo_matrix_invert = libcairo.cairo_matrix_invert
cairo_matrix_invert.restype = cairo_status_t
cairo_matrix_invert.argtypes = [POINTER(cairo_matrix_t)]
cairo_matrix_multiply = libcairo.cairo_matrix_multiply
cairo_matrix_multiply.restype = None
cairo_matrix_multiply.argtypes = [POINTER(cairo_matrix_t), POINTER(cairo_matrix_t), POINTER(cairo_matrix_t)]
cairo_matrix_transform_distance = libcairo.cairo_matrix_transform_distance
cairo_matrix_transform_distance.restype = None
cairo_matrix_transform_distance.argtypes = [POINTER(cairo_matrix_t), POINTER(c_double), POINTER(c_double)]
cairo_matrix_transform_point = libcairo.cairo_matrix_transform_point
cairo_matrix_transform_point.restype = None
cairo_matrix_transform_point.argtypes = [POINTER(cairo_matrix_t), POINTER(c_double), POINTER(c_double)]
cairo_debug_reset_static_data = libcairo.cairo_debug_reset_static_data
cairo_debug_reset_static_data.restype = None
cairo_debug_reset_static_data.argtypes = []
