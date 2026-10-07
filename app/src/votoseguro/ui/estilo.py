"""Estilo visual minimalista: fondo claro, un solo color de acento, tarjetas blancas con bordes
suaves, mucho espacio en blanco y letra legible. Los estados siempre se indican con color + texto.
"""

# Paleta (neutra + un acento)
FONDO = "#f7f8fa"
SUPERFICIE = "#ffffff"
TEXTO = "#1f2328"
SECUNDARIO = "#6b7280"
BORDE = "#e5e7eb"
BORDE_FUERTE = "#d1d5db"
ACENTO = "#2563eb"
ACENTO_SUAVE = "#eff4ff"
VERDE = "#15803d"
ROJO = "#c62828"
AMBAR = "#b45309"
GRIS = SECUNDARIO

HOJA = f"""
* {{ font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif; }}
QWidget {{ font-size: 15px; color: {TEXTO}; background: {FONDO}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: {FONDO}; }}
QLabel {{ background: transparent; }}
QLabel#marca {{ font-size: 17px; font-weight: 700; color: {TEXTO}; letter-spacing: 1px; }}
QLabel#titulo {{ font-size: 24px; font-weight: 600; color: {TEXTO}; padding: 4px 0 8px 0; }}
QLabel#subtitulo {{ font-size: 16px; font-weight: 600; color: {TEXTO}; }}
QLabel#ayuda {{ color: {SECUNDARIO}; font-size: 14px; }}
QLabel#estado {{ font-size: 13px; font-weight: 700; padding: 5px 14px; border-radius: 13px; }}

QListWidget#navegacion {{ background: {SUPERFICIE}; border: none; border-right: 1px solid {BORDE};
                         font-size: 15px; padding: 12px 8px; outline: 0; }}
QListWidget#navegacion::item {{ padding: 11px 14px; margin: 2px 0; border-radius: 8px; color: {TEXTO}; }}
QListWidget#navegacion::item:hover {{ background: {FONDO}; }}
QListWidget#navegacion::item:selected {{ background: {ACENTO_SUAVE}; color: {ACENTO}; font-weight: 600; }}
QListWidget#navegacion::item:disabled {{ color: #b6bcc6; }}

QPushButton {{ background: {ACENTO}; color: white; border: none; border-radius: 8px; padding: 10px 18px;
              font-weight: 600; }}
QPushButton:hover {{ background: #1d4ed8; }}
QPushButton:disabled {{ background: #e5e7eb; color: #9ca3af; }}
QPushButton#secundario {{ background: {SUPERFICIE}; color: {TEXTO}; border: 1px solid {BORDE_FUERTE}; }}
QPushButton#secundario:hover {{ background: {FONDO}; border-color: {SECUNDARIO}; }}
QPushButton#secundario:disabled, QPushButton#peligro:disabled {{ background: {FONDO}; color: #b6bcc6;
              border: 1px dashed {BORDE}; }}
QPushButton#peligro {{ background: {SUPERFICIE}; color: {ROJO}; border: 1px solid {ROJO}; }}
QPushButton#peligro:hover {{ background: #fdecea; }}
QPushButton#salir {{ background: transparent; color: {SECUNDARIO}; border: 1px solid {BORDE_FUERTE};
                    padding: 7px 14px; font-weight: 500; }}
QPushButton#salir:hover {{ color: {ROJO}; border-color: {ROJO}; }}

QLineEdit, QSpinBox, QPlainTextEdit, QComboBox {{ background: {SUPERFICIE}; border: 1px solid {BORDE_FUERTE};
              border-radius: 8px; padding: 7px 10px; selection-background-color: {ACENTO}; }}
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 1px solid {ACENTO}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}
QCheckBox {{ background: transparent; spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {BORDE_FUERTE}; border-radius: 5px;
                        background: {SUPERFICIE}; }}
QCheckBox::indicator:checked {{ background: {ACENTO}; border-color: {ACENTO}; }}
QCheckBox::indicator:disabled {{ background: #f1f3f5; }}

QGroupBox {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 12px; margin-top: 22px;
             padding: 18px 16px 14px 16px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 4px; padding: 0 4px; color: {SECUNDARIO};
                    font-size: 13px; font-weight: 600; }}

QTableWidget, QTreeWidget, QListWidget {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 8px;
              gridline-color: {BORDE}; alternate-background-color: #fafbfc; }}
QHeaderView::section {{ background: {SUPERFICIE}; color: {SECUNDARIO}; padding: 8px 6px; border: none;
                        border-bottom: 1px solid {BORDE}; font-weight: 600; font-size: 13px; }}
QTableCornerButton::section {{ background: {SUPERFICIE}; border: none; }}
QProgressBar {{ border: none; border-radius: 6px; background: #eef0f3; text-align: center; height: 16px; }}
QProgressBar::chunk {{ background: {ACENTO}; border-radius: 6px; }}
QStatusBar {{ background: {SUPERFICIE}; border-top: 1px solid {BORDE}; color: {SECUNDARIO}; }}
QToolTip {{ background: {TEXTO}; color: white; border: none; padding: 6px; }}
"""

# Kiosco del votante: aún más simple y grande (adultos mayores, baja visión).
HOJA_KIOSCO = f"""
* {{ font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif; }}
QWidget {{ background: {SUPERFICIE}; color: {TEXTO}; font-size: 26px; }}
QLabel {{ background: transparent; }}
QLabel#titulo {{ font-size: 38px; font-weight: 600; color: {TEXTO}; }}
QLabel#grande {{ font-size: 34px; font-weight: 600; color: {TEXTO}; }}
QLabel#ayuda {{ font-size: 22px; color: {SECUNDARIO}; }}
QLabel#teclas {{ font-size: 22px; color: {SECUNDARIO}; padding: 8px; }}
QLabel#cuenta {{ font-size: 20px; color: {SECUNDARIO}; padding: 6px; }}
QPushButton#opcion {{ text-align: left; padding: 22px 28px; border: 2px solid {BORDE}; border-radius: 16px;
                      background: {SUPERFICIE}; color: {TEXTO}; font-size: 30px; font-weight: 500; }}
QPushButton#opcion:hover, QPushButton#opcion:focus {{ border: 3px solid {ACENTO}; background: {ACENTO_SUAVE}; }}
QPushButton#opcion_especial {{ text-align: left; padding: 18px 28px; border: 2px dashed {BORDE_FUERTE};
                               border-radius: 16px; background: {FONDO}; color: {SECUNDARIO}; font-size: 26px; }}
QPushButton#opcion_especial:hover, QPushButton#opcion_especial:focus {{ border: 3px solid {ACENTO}; color: {TEXTO}; }}
QPushButton#confirmar {{ background: {VERDE}; color: white; border: none; border-radius: 16px; padding: 26px;
                         font-size: 30px; font-weight: 700; }}
QPushButton#corregir {{ background: {SUPERFICIE}; color: {TEXTO}; border: 2px solid {BORDE_FUERTE};
                        border-radius: 16px; padding: 26px; font-size: 30px; font-weight: 600; }}
QPushButton#salida {{ background: transparent; color: #c4c9d1; border: none; font-size: 13px; }}
"""


def color_estado(estado: str) -> tuple[str, str]:
    """Colores (texto, fondo) de la etiqueta de estado de la elección: tonos suaves."""
    return {
        "CONFIGURACION": (SECUNDARIO, "#f1f3f5"),
        "EMPADRONAMIENTO": (AMBAR, "#fef3e2"),
        "LISTA": (ACENTO, ACENTO_SUAVE),
        "ABIERTA": (VERDE, "#e8f5ec"),
        "CERRADA": (ROJO, "#fdecea"),
        "ESCRUTADA": ("#6d28d9", "#f3effd"),
        "EXPORTADA": ("#374151", "#eef0f3"),
    }.get(estado, (SECUNDARIO, "#f1f3f5"))
