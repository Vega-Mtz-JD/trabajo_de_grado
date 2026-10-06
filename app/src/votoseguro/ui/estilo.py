"""Estilo visual: alto contraste, letras grandes y estados con color + texto (no solo color)."""

AZUL = "#0b3d91"
AZUL_CLARO = "#e8eefb"
VERDE = "#1b7f3b"
ROJO = "#b3261e"
AMBAR = "#8a5a00"
GRIS = "#5f6368"

HOJA = f"""
QWidget {{ font-size: 15px; color: #1a1a1a; background: #ffffff; }}
QMainWindow, QDialog {{ background: #f5f7fb; }}
QLabel#titulo {{ font-size: 24px; font-weight: 700; color: {AZUL}; }}
QLabel#subtitulo {{ font-size: 17px; font-weight: 600; color: #333; }}
QLabel#ayuda {{ color: {GRIS}; }}
QLabel#estado {{ font-weight: 700; padding: 4px 12px; border-radius: 10px; color: white; background: {AZUL}; }}
QListWidget#navegacion {{ background: {AZUL}; color: white; border: none; font-size: 16px; padding-top: 8px; }}
QListWidget#navegacion::item {{ padding: 12px 16px; }}
QListWidget#navegacion::item:selected {{ background: #ffffff; color: {AZUL}; font-weight: 700; }}
QListWidget#navegacion::item:disabled {{ color: #9fb3d9; }}
QPushButton {{ background: {AZUL}; color: white; border: none; border-radius: 6px; padding: 10px 18px;
              font-weight: 600; }}
QPushButton:hover {{ background: #154fb3; }}
QPushButton:disabled {{ background: #b8c2d6; color: #f0f0f0; }}
QPushButton#secundario {{ background: white; color: {AZUL}; border: 2px solid {AZUL}; }}
QPushButton#peligro {{ background: {ROJO}; }}
QLineEdit, QSpinBox, QPlainTextEdit, QComboBox, QTableWidget {{ border: 1px solid #b9c3d6; border-radius: 4px;
              padding: 6px; background: white; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 2px solid {AZUL}; }}
QGroupBox {{ font-weight: 700; border: 1px solid #c9d2e3; border-radius: 6px; margin-top: 14px; padding: 10px;
             background: white; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {AZUL}; }}
QHeaderView::section {{ background: {AZUL_CLARO}; padding: 6px; border: none; font-weight: 700; }}
"""

# Kiosco del votante: muy grande y simple (adultos mayores, baja visión).
HOJA_KIOSCO = f"""
QWidget {{ background: #ffffff; color: #111; font-size: 26px; }}
QLabel#titulo {{ font-size: 40px; font-weight: 800; color: {AZUL}; }}
QLabel#grande {{ font-size: 34px; font-weight: 700; }}
QLabel#ayuda {{ font-size: 24px; color: #333; }}
QPushButton#opcion {{ text-align: left; padding: 22px 28px; border: 3px solid {AZUL}; border-radius: 14px;
                      background: white; color: #111; font-size: 30px; }}
QPushButton#opcion:hover, QPushButton#opcion:focus {{ background: {AZUL_CLARO}; border: 5px solid {AZUL}; }}
QPushButton#opcion_especial {{ text-align: left; padding: 18px 28px; border: 3px dashed {GRIS}; border-radius: 14px;
                               background: #fafafa; color: #333; font-size: 26px; }}
QPushButton#confirmar {{ background: {VERDE}; color: white; border-radius: 14px; padding: 26px; font-size: 32px;
                         font-weight: 800; }}
QPushButton#corregir {{ background: white; color: {AZUL}; border: 3px solid {AZUL}; border-radius: 14px;
                        padding: 26px; font-size: 30px; font-weight: 700; }}
QPushButton#salida {{ background: transparent; color: #c9c9c9; border: none; font-size: 14px; }}
"""


def color_estado(estado: str) -> str:
    return {"CONFIGURACION": GRIS, "EMPADRONAMIENTO": AMBAR, "LISTA": AZUL, "ABIERTA": VERDE,
            "CERRADA": ROJO, "ESCRUTADA": "#6a1b9a", "EXPORTADA": "#37474f"}.get(estado, GRIS)
