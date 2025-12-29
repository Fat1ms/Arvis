"""
UI Styles for Arvis Launcher - matching Arvis Client dark theme
"""

# Color Palette (matching Arvis Client)
COLORS = {
    "bg_primary": "rgb(43, 43, 43)",       # Main background
    "bg_secondary": "rgb(35, 35, 35)",     # Darker areas
    "bg_tertiary": "rgb(50, 50, 50)",      # Lighter areas
    "bg_hover": "rgba(255, 255, 255, 0.1)", # Hover state
    "bg_pressed": "rgb(30, 30, 30)",       # Pressed state
    "bg_selected": "rgb(60, 60, 60)",      # Selected items
    "surface": "rgb(50, 50, 50)",          # Card/panel surfaces
    "border": "rgb(60, 60, 60)",           # Borders/separators
    "text_primary": "white",               # Main text
    "text_secondary": "rgb(180, 180, 180)", # Secondary text
    "text_muted": "rgb(100, 100, 100)",    # Muted text
    "accent": "rgb(100, 150, 255)",        # Accent color
    "accent_hover": "rgb(120, 170, 255)",  # Accent hover
    "success": "rgb(80, 200, 120)",        # Success/running
    "warning": "rgb(255, 180, 50)",        # Warning
    "error": "rgb(200, 50, 50)",           # Error/stop
    "error_hover": "rgb(220, 70, 70)",     # Error hover
    "danger": "rgb(200, 50, 50)",          # Danger/destructive actions
    "danger_hover": "rgb(220, 70, 70)",    # Danger hover
}

# Main window style
MAIN_WINDOW_STYLE = f"""
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}
"""

# Title bar style
TITLE_BAR_STYLE = f"""
    QWidget#title_bar {{
        background-color: {COLORS['bg_primary']};
    }}
    QLabel {{
        background-color: transparent;
        border: none;
        color: {COLORS['text_primary']};
    }}
    QPushButton {{
        background-color: transparent;
        border: none;
    }}
"""

TITLE_LABEL_STYLE = f"""
    QLabel {{
        color: {COLORS['text_primary']};
        font-weight: bold;
        font-size: 12px;
        border: none;
    }}
"""

# Window control buttons
WINDOW_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_muted']};
        border: none;
        font-size: 11px;
        font-weight: bold;
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border-radius: 3px;
        margin: 1px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['bg_pressed']};
    }}
"""

CLOSE_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_muted']};
        border: none;
        font-size: 11px;
        font-weight: bold;
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border-radius: 3px;
        margin: 1px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['error']};
        color: {COLORS['text_primary']};
    }}
    QPushButton:pressed {{
        background-color: rgb(180, 30, 30);
    }}
"""

# Navigation panel style
NAV_PANEL_STYLE = f"""
    QWidget#nav_panel {{
        background-color: {COLORS['bg_secondary']};
        border-right: 1px solid {COLORS['border']};
    }}
"""

NAV_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS['text_secondary']};
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_hover']};
        color: {COLORS['text_primary']};
    }}
    QPushButton:checked {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        font-weight: bold;
    }}
"""

# Content area
CONTENT_STYLE = f"""
    QWidget#content_area {{
        background-color: {COLORS['bg_primary']};
    }}
"""

# Page title
PAGE_TITLE_STYLE = f"""
    QLabel {{
        color: {COLORS['text_primary']};
        font-size: 20px;
        font-weight: bold;
        padding: 0;
        margin: 0;
    }}
"""

PAGE_SUBTITLE_STYLE = f"""
    QLabel {{
        color: {COLORS['text_secondary']};
        font-size: 12px;
        padding: 0;
        margin: 0;
    }}
"""

# Primary action button (large)
PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['accent']};
        color: {COLORS['text_primary']};
        border: none;
        border-radius: 8px;
        padding: 16px 32px;
        font-size: 16px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: rgb(80, 130, 235);
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_muted']};
    }}
"""

# Secondary button
SECONDARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_selected']};
        border-color: {COLORS['text_muted']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['bg_pressed']};
    }}
    QPushButton:disabled {{
        color: {COLORS['text_muted']};
    }}
"""

# Danger button (stop, remove)
DANGER_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['error']};
        color: {COLORS['text_primary']};
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['error_hover']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_muted']};
    }}
"""

# Success button
SUCCESS_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['success']};
        color: {COLORS['text_primary']};
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: rgb(100, 220, 140);
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_muted']};
    }}
"""

# Status indicator
STATUS_LABEL_STYLE = {
    "stopped": f"color: {COLORS['text_muted']}; font-size: 14px;",
    "starting": f"color: {COLORS['warning']}; font-size: 14px;",
    "running": f"color: {COLORS['success']}; font-size: 14px;",
    "error": f"color: {COLORS['error']}; font-size: 14px;",
    "updating": f"color: {COLORS['accent']}; font-size: 14px;",
}

# Log view
LOG_VIEW_STYLE = f"""
    QTextEdit {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px;
        font-family: Consolas, Monaco, monospace;
        font-size: 11px;
    }}
"""

# Progress bar
PROGRESS_BAR_STYLE = f"""
    QProgressBar {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        text-align: center;
        color: {COLORS['text_primary']};
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS['accent']};
        border-radius: 3px;
    }}
"""

# Group box
GROUP_BOX_STYLE = f"""
    QGroupBox {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 8px;
        font-size: 13px;
        color: {COLORS['text_primary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {COLORS['text_secondary']};
    }}
"""

# Combo box
COMBO_BOX_STYLE = f"""
    QComboBox {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-width: 150px;
    }}
    QComboBox:hover {{
        border-color: {COLORS['text_muted']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['bg_selected']};
    }}
"""

# Check box
CHECK_BOX_STYLE = f"""
    QCheckBox {{
        color: {COLORS['text_primary']};
        font-size: 13px;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        background-color: {COLORS['bg_tertiary']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {COLORS['text_muted']};
    }}
"""

# Scroll area
SCROLL_AREA_STYLE = f"""
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {COLORS['bg_secondary']};
        width: 10px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {COLORS['bg_tertiary']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {COLORS['bg_secondary']};
        height: 10px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {COLORS['bg_tertiary']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {COLORS['text_muted']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
"""

# List widget / Table
LIST_WIDGET_STYLE = f"""
    QListWidget, QTableWidget {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QListWidget::item, QTableWidget::item {{
        padding: 8px;
        border-radius: 4px;
    }}
    QListWidget::item:hover, QTableWidget::item:hover {{
        background-color: {COLORS['bg_hover']};
    }}
    QListWidget::item:selected, QTableWidget::item:selected {{
        background-color: {COLORS['bg_selected']};
    }}
    QHeaderView::section {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: none;
        padding: 8px;
        font-weight: bold;
    }}
"""

# Card/Panel style for model items
CARD_STYLE = f"""
    QFrame#card {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
    }}
    QFrame#card:hover {{
        border-color: {COLORS['text_muted']};
    }}
"""

# Input fields
LINE_EDIT_STYLE = f"""
    QLineEdit {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border-color: {COLORS['accent']};
    }}
    QLineEdit:disabled {{
        color: {COLORS['text_muted']};
        background-color: {COLORS['bg_secondary']};
    }}
"""

# Separator line
SEPARATOR_STYLE = f"""
    QFrame {{
        background-color: {COLORS['border']};
        border: none;
    }}
"""

# Tooltip
TOOLTIP_STYLE = f"""
    QToolTip {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        padding: 6px;
        border-radius: 4px;
    }}
"""

# Tab widget
TAB_WIDGET_STYLE = f"""
    QTabWidget::pane {{
        background-color: {COLORS['bg_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        margin-top: -1px;
    }}
    QTabBar::tab {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        border-bottom: 1px solid {COLORS['bg_primary']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {COLORS['bg_tertiary']};
    }}
"""


def get_global_stylesheet() -> str:
    """Get the complete global stylesheet for the application"""
    return f"""
        * {{
            font-family: 'Segoe UI', 'Exo 2', sans-serif;
        }}
        QWidget {{
            background-color: {COLORS['bg_primary']};
            color: {COLORS['text_primary']};
        }}
        {TOOLTIP_STYLE}
        {SCROLL_AREA_STYLE}
    """
