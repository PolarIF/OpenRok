# ==========================================================
# DARK THEME
# ==========================================================

VERDE = "#21E05A"   # answer from the database (or image cache)
AMARELO = "#FFC928"  # AI suggestion

FUNDO = "#15181D"
PAINEL = "#1E232A"
TEXTO = "#E8ECF1"
SECUNDARIO = "#8A94A3"
BORDA = "#2C333D"

QSS = f"""
QWidget {{ background: {FUNDO}; color: {TEXTO}; font-size: 13px; }}
QTabWidget::pane {{ border: none; border-top: 1px solid {BORDA}; }}
QTabBar::tab {{ background: #0F1215; color: {SECUNDARIO}; padding: 8px 14px; border: none; }}
QTabBar::tab:selected {{ color: {TEXTO}; border-bottom: 2px solid {VERDE}; }}
QLineEdit, QComboBox, QListWidget {{
    background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 6px; padding: 6px;
}}
QPushButton {{
    background: {PAINEL}; border: 1px solid {BORDA}; border-radius: 6px; padding: 6px 12px;
}}
QPushButton:hover {{ border-color: {VERDE}; }}
QPushButton#principal {{ background: {VERDE}; color: #0D2E12; font-weight: bold; border: none; }}
QPushButton:checked {{ border: 1px solid {VERDE}; color: {VERDE}; }}
QLabel, QCheckBox {{ background: transparent; }}
QLabel#secundario {{ color: {SECUNDARIO}; font-size: 12px; }}
QLabel#resposta {{ font-size: 20px; font-weight: bold; color: {VERDE}; }}
QLabel#numero {{ font-size: 17px; font-weight: bold; }}
QListWidget::item {{ padding: 8px 4px; border-bottom: 1px solid {BORDA}; }}
QListWidget::item:selected {{ background: {BORDA}; color: {TEXTO}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {SECUNDARIO}; }}
QCheckBox::indicator:checked {{ background: {VERDE}; border-color: {VERDE}; }}
QFrame#cartao {{ background: {PAINEL}; border-radius: 8px; border-left: 4px solid {VERDE}; }}
QFrame#estatistica {{ background: {PAINEL}; border-radius: 6px; }}
QSlider::handle:horizontal {{ background: {VERDE}; width: 14px; border-radius: 7px; margin: -5px 0; }}
QSlider::groove:horizontal {{ background: {BORDA}; height: 4px; border-radius: 2px; }}
"""
