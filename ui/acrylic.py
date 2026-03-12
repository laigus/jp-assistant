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


def enable_acrylic(hwnd, tint_color=0x30201520):
    """Apply acrylic blur behind a frameless transparent window.

    IMPORTANT: Do NOT combine with DwmExtendFrameIntoClientArea(-1,-1,-1,-1)
    as that will fill the window with an opaque DWM frame.

    Args:
        hwnd: Native window handle
        tint_color: AABBGGRR tint. Low alpha (AA) = more see-through blur.
    """
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32

        # Try acrylic first (Win10 1803+), fall back to blur-behind
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
                return True

        return False
    except Exception:
        return False
