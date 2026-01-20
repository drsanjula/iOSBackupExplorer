"""
UI Styles - Modern PyQt6 styling with system theme support.

This module provides a consistent, modern look that respects macOS
system theme (light/dark mode) while adding custom styling for
the iOS Backup Explorer.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


def is_dark_mode() -> bool:
    """Check if the system is in dark mode."""
    palette = QApplication.palette()
    window_color = palette.color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


def get_accent_color() -> str:
    """Get the system accent color or default."""
    palette = QApplication.palette()
    accent = palette.color(QPalette.ColorRole.Highlight)
    return accent.name()


class Colors:
    """Color constants that adapt to system theme."""
    
    @staticmethod
    def background() -> str:
        return "#1c1c1e" if is_dark_mode() else "#f5f5f7"
    
    @staticmethod
    def surface() -> str:
        return "#2c2c2e" if is_dark_mode() else "#ffffff"
    
    @staticmethod
    def surface_secondary() -> str:
        return "#3a3a3c" if is_dark_mode() else "#f2f2f7"
    
    @staticmethod
    def text_primary() -> str:
        return "#ffffff" if is_dark_mode() else "#1d1d1f"
    
    @staticmethod
    def text_secondary() -> str:
        return "#98989d" if is_dark_mode() else "#86868b"
    
    @staticmethod
    def border() -> str:
        return "#48484a" if is_dark_mode() else "#d2d2d7"
    
    @staticmethod
    def primary() -> str:
        return get_accent_color()
    
    @staticmethod
    def success() -> str:
        return "#32d74b" if is_dark_mode() else "#34c759"
    
    @staticmethod
    def error() -> str:
        return "#ff453a" if is_dark_mode() else "#ff3b30"


def get_stylesheet() -> str:
    """Generate the main application stylesheet."""
    dark = is_dark_mode()
    
    bg = Colors.background()
    surface = Colors.surface()
    surface_sec = Colors.surface_secondary()
    text = Colors.text_primary()
    text_sec = Colors.text_secondary()
    border = Colors.border()
    accent = Colors.primary()
    
    return f"""
    /* ===== Global Styles ===== */
    QMainWindow {{
        background-color: {bg};
    }}
    
    QWidget {{
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
        font-size: 13px;
        color: {text};
    }}
    
    /* ===== Sidebar ===== */
    #sidebar {{
        background-color: {surface_sec};
        border-right: 1px solid {border};
    }}
    
    #sidebar QLabel#sidebarTitle {{
        font-size: 11px;
        font-weight: 600;
        color: {text_sec};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 16px 16px 8px 16px;
    }}
    
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
        padding: 8px;
    }}
    
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 2px;
        color: {text};
    }}
    
    QListWidget::item:hover {{
        background-color: {"#3a3a3c" if dark else "#e5e5ea"};
    }}
    
    QListWidget::item:selected {{
        background-color: {accent};
        color: white;
    }}
    
    /* ===== Content Area ===== */
    #contentArea {{
        background-color: {bg};
    }}
    
    #contentHeader {{
        background-color: {bg};
        border-bottom: 1px solid {border};
        padding: 24px 32px;
    }}
    
    #contentHeader QLabel#headerTitle {{
        font-size: 24px;
        font-weight: 700;
        color: {text};
        margin-bottom: 4px;
    }}
    
    #contentHeader QLabel#headerSubtitle {{
        font-size: 14px;
        color: {text_sec};
    }}
    
    /* ===== Stats Cards ===== */
    #statsCard {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 20px;
    }}
    
    #statsCard QLabel#statValue {{
        font-size: 28px;
        font-weight: 700;
        color: {text};
    }}
    
    #statsCard QLabel#statLabel {{
        font-size: 12px;
        font-weight: 600;
        color: {text_sec};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    /* ===== Table View ===== */
    QTableWidget {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 10px;
        gridline-color: {border};
        selection-background-color: {accent};
        outline: none;
    }}
    
    QTableWidget::item {{
        padding: 8px 12px;
        border-bottom: 1px solid {border};
    }}
    
    QTableWidget::item:selected {{
        background-color: {accent};
        color: white;
    }}
    
    QHeaderView::section {{
        background-color: {surface_sec};
        padding: 8px 12px;
        border: none;
        border-bottom: 1px solid {border};
        font-weight: 600;
        color: {text_sec};
        text-transform: uppercase;
        font-size: 11px;
    }}
    
    /* ===== Buttons ===== */
    QPushButton {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {surface_sec};
        border-color: {text_sec};
    }}
    
    QPushButton:pressed {{
        background-color: {border};
    }}
    
    QPushButton#primaryButton {{
        background-color: {accent};
        border: 1px solid {accent};
        color: white;
    }}
    
    QPushButton#primaryButton:hover {{
        opacity: 0.9;
    }}
    
    /* ===== Inputs ===== */
    QLineEdit {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px 12px;
    }}
    
    QLineEdit:focus {{
        border: 1px solid {accent};
    }}
    
    /* ===== Scrollbars ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 40px;
        border-radius: 6px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: {text_sec};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    /* ===== Tooltips ===== */
    QToolTip {{
        background-color: {surface_sec};
        color: {text};
        border: 1px solid {border};
        padding: 5px;
        border-radius: 4px;
    }}
    """


def get_lite_mode_additions() -> str:
    return """
    .proOnly { display: none; }
    """


def get_pro_mode_additions() -> str:
    return ""


def apply_stylesheet(app: QApplication, mode: str = "pro"):
    base = get_stylesheet()
    extra = get_lite_mode_additions() if mode == "lite" else get_pro_mode_additions()
    app.setStyleSheet(base + extra)
