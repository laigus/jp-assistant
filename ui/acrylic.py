"""Windows Acrylic (frosted glass) blur behind a transparent frameless window.

Uses SetWindowCompositionAttribute to apply blur behind the window.
Compatible with WA_TranslucentBackground + FramelessWindowHint.
"""
import ctypes
import sys


class AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_uint),
        ("Data", ctypes.POINTER(AccentPolicy)),
        ("SizeOfData", ctypes.c_uint),
    ]


ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWCP_ROUND = 2


def enable_rounded_corners(hwnd):
    """Enable native Win11 rounded corners + DWM shadow."""
    if sys.platform != "win32":
        return
    try:
        dwmapi = ctypes.windll.dwmapi

        val = ctypes.c_int(DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(val), ctypes.sizeof(val)
        )

        dark = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark), ctypes.sizeof(dark)
        )

        m = MARGINS(1, 1, 1, 1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))
    except Exception:
        pass


def enable_acrylic(hwnd, tint_color=0x30201520):
    """Apply acrylic blur behind a frameless transparent window.

    Args:
        hwnd: Native window handle
        tint_color: AABBGGRR tint. Low alpha (AA) = more see-through blur.
    """
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32

        for accent_state in [ACCENT_ENABLE_ACRYLICBLURBEHIND, ACCENT_ENABLE_BLURBEHIND]:
            accent = AccentPolicy()
            accent.AccentState = accent_state
            accent.AccentFlags = 2
            accent.GradientColor = tint_color

            data = WindowCompositionAttributeData()
            data.Attribute = WCA_ACCENT_POLICY
            data.Data = ctypes.pointer(accent)
            data.SizeOfData = ctypes.sizeof(accent)

            result = user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
            if result:
                enable_rounded_corners(hwnd)
                return True

        return False
    except Exception:
        return False
