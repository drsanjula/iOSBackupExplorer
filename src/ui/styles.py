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
    # Dark mode if window background is dark
    return window_color.lightness() < 128


def get_accent_color() -> str:
    """Get the system accent color or default."""
    palette = QApplication.palette()
    accent = palette.color(QPalette.ColorRole.Highlight)
    return accent.name()


# Color palette - adapts to system theme
class Colors:
    """Color constants that adapt to system theme."""
    
    @staticmethod
    def primary() -> str:
        return get_accent_color()
    
    @staticmethod
    def background() -> str:
        return "#1e1e1e" if is_dark_mode() else "#f5f5f7"
    
    @staticmethod
    def surface() -> str:
        return "#2d2d2d" if is_dark_mode() else "#ffffff"
    
    @staticmethod
    def surface_variant() -> str:
        return "#3d3d3d" if is_dark_mode() else "#f0f0f0"
    
    @staticmethod
    def text_primary() -> str:
        return "#ffffff" if is_dark_mode() else "#1d1d1f"
    
    @staticmethod
    def text_secondary() -> str:
        return "#a0a0a0" if is_dark_mode() else "#6e6e73"
    
    @staticmethod
    def border() -> str:
        return "#404040" if is_dark_mode() else "#d2d2d7"
    
    @staticmethod
    def success() -> str:
        return "#34c759"
    
    @staticmethod
    def warning() -> str:
        return "#ff9f0a"
    
    @staticmethod
    def error() -> str:
        return "#ff3b30"
    
    @staticmethod
    def info() -> str:
        return "#007aff"


def get_stylesheet() -> str:
    """
    Generate the main application stylesheet.
    
    Returns:
        QSS stylesheet string
    """
    dark = is_dark_mode()
    
    # Adaptive colors
    bg = Colors.background()
    surface = Colors.surface()
    surface_var = Colors.surface_variant()
    text = Colors.text_primary()
    text_sec = Colors.text_secondary()
    border = Colors.border()
    accent = Colors.primary()
    
    # Scrollbar colors
    scrollbar_bg = "#2a2a2a" if dark else "#f0f0f0"
    scrollbar_handle = "#5a5a5a" if dark else "#c0c0c0"
    scrollbar_handle_hover = "#7a7a7a" if dark else "#a0a0a0"
    
    return f"""
    /* ===== Global Styles ===== */
    QMainWindow {{
        background-color: {bg};
    }}
    
    QWidget {{
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif;
        font-size: 13px;
        color: {text};
    }}
    
    /* ===== Sidebar ===== */
    #sidebar {{
        background-color: {surface};
        border-right: 1px solid {border};
    }}
    
    #sidebar QLabel#sidebarTitle {{
        font-size: 11px;
        font-weight: 600;
        color: {text_sec};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 12px 16px 8px 16px;
    }}
    
    /* ===== Sidebar List Items ===== */
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
        padding: 4px 8px;
    }}
    
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 8px;
        margin: 2px 0;
    }}
    
    QListWidget::item:hover {{
        background-color: {surface_var};
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
        background-color: {surface};
        border-bottom: 1px solid {border};
        padding: 16px 24px;
    }}
    
    #contentHeader QLabel#headerTitle {{
        font-size: 22px;
        font-weight: 600;
        color: {text};
    }}
    
    #contentHeader QLabel#headerSubtitle {{
        font-size: 13px;
        color: {text_sec};
    }}
    
    /* ===== Cards ===== */
    .card {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 16px;
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
        color: {text_sec};
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    
    /* ===== Buttons ===== */
    QPushButton {{
        background-color: {surface_var};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        color: {text};
    }}
    
    QPushButton:hover {{
        background-color: {"#4a4a4a" if dark else "#e5e5e5"};
    }}
    
    QPushButton:pressed {{
        background-color: {"#3a3a3a" if dark else "#d5d5d5"};
    }}
    
    QPushButton:disabled {{
        background-color: {surface_var};
        color: {text_sec};
        opacity: 0.5;
    }}
    
    QPushButton#primaryButton {{
        background-color: {accent};
        border: none;
        color: white;
    }}
    
    QPushButton#primaryButton:hover {{
        background-color: {accent};
        opacity: 0.9;
    }}
    
    QPushButton#successButton {{
        background-color: {Colors.success()};
        border: none;
        color: white;
    }}
    
    QPushButton#dangerButton {{
        background-color: {Colors.error()};
        border: none;
        color: white;
    }}
    
    /* ===== Progress Bar ===== */
    QProgressBar {{
        background-color: {surface_var};
        border: none;
        border-radius: 6px;
        height: 12px;
        text-align: center;
    }}
    
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 6px;
    }}
    
    /* ===== Input Fields ===== */
    QLineEdit {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 10px 12px;
        color: {text};
    }}
    
    QLineEdit:focus {{
        border-color: {accent};
    }}
    
    QLineEdit:disabled {{
        background-color: {surface_var};
        color: {text_sec};
    }}
    
    /* ===== Combo Box ===== */
    QComboBox {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px 12px;
        color: {text};
    }}
    
    QComboBox:hover {{
        border-color: {accent};
    }}
    
    QComboBox::drop-down {{
        border: none;
        padding-right: 10px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        selection-background-color: {accent};
    }}
    
    /* ===== Scrollbars ===== */
    QScrollBar:vertical {{
        background-color: {scrollbar_bg};
        width: 12px;
        border-radius: 6px;
        margin: 4px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {scrollbar_handle};
        border-radius: 4px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {scrollbar_handle_hover};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    QScrollBar:horizontal {{
        background-color: {scrollbar_bg};
        height: 12px;
        border-radius: 6px;
        margin: 4px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {scrollbar_handle};
        border-radius: 4px;
        min-width: 30px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {scrollbar_handle_hover};
    }}
    
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    
    /* ===== Table / Tree View ===== */
    QTableWidget, QTreeWidget {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 8px;
        gridline-color: {border};
    }}
    
    QTableWidget::item, QTreeWidget::item {{
        padding: 8px;
    }}
    
    QTableWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {accent};
        color: white;
    }}
    
    QHeaderView::section {{
        background-color: {surface_var};
        border: none;
        border-bottom: 1px solid {border};
        padding: 10px;
        font-weight: 600;
        color: {text};
    }}
    
    /* ===== Tabs ===== */
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 8px;
        background-color: {surface};
    }}
    
    QTabBar::tab {{
        background-color: transparent;
        padding: 10px 20px;
        border-bottom: 2px solid transparent;
        color: {text_sec};
    }}
    
    QTabBar::tab:selected {{
        color: {accent};
        border-bottom-color: {accent};
    }}
    
    QTabBar::tab:hover {{
        color: {text};
    }}
    
    /* ===== Tooltips ===== */
    QToolTip {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px;
        color: {text};
    }}
    
    /* ===== Splitter ===== */
    QSplitter::handle {{
        background-color: {border};
    }}
    
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    
    /* ===== Mode Toggle ===== */
    #modeToggle {{
        background-color: {surface_var};
        border-radius: 20px;
        padding: 4px;
    }}
    
    #modeToggle QPushButton {{
        border-radius: 16px;
        padding: 8px 16px;
        font-size: 12px;
        border: none;
    }}
    
    #modeToggle QPushButton:checked {{
        background-color: {accent};
        color: white;
    }}
    
    /* ===== Empty State ===== */
    #emptyState {{
        background-color: transparent;
    }}
    
    #emptyState QLabel#emptyIcon {{
        font-size: 64px;
    }}
    
    #emptyState QLabel#emptyTitle {{
        font-size: 20px;
        font-weight: 600;
        color: {text};
    }}
    
    #emptyState QLabel#emptyMessage {{
        font-size: 14px;
        color: {text_sec};
    }}
    """


def get_lite_mode_additions() -> str:
    """
    Get additional styles for Lite mode (simplified UI).
    
    Returns:
        Additional QSS string
    """
    return """
    /* Hide pro-only features in Lite mode */
    .proOnly {
        display: none;
    }
    """


def get_pro_mode_additions() -> str:
    """
    Get additional styles for Pro mode.
    
    Returns:
        Additional QSS string
    """
    # Pro mode has all features, no hiding needed
    return ""


def apply_stylesheet(app: QApplication, mode: str = "pro"):
    """
    Apply the stylesheet to the application.
    
    Args:
        app: QApplication instance
        mode: "lite" or "pro"
    """
    base_style = get_stylesheet()
    
    if mode == "lite":
        full_style = base_style + get_lite_mode_additions()
    else:
        full_style = base_style + get_pro_mode_additions()
    
    app.setStyleSheet(full_style)
