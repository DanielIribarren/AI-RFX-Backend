"""
🎨 Template Configuration - Metadata de estilos para cada tipo de presupuesto
Cada template define colores, tipografía, tono y estructura que se inyectan en el prompt del LLM.
El LLM usa esta metadata como instrucciones de estilo para generar HTML consistente.
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
import unicodedata
import logging

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


class TemplateType(str, Enum):
    CORPORATE = "corporate"
    WEDDING = "wedding"
    CELEBRATION = "celebration"
    EVENT = "event"
    INVOICE = "invoice"
    CUSTOM = "custom"


# Mapeo de template_type a archivo HTML de referencia
TEMPLATE_FILES = {
    TemplateType.CORPORATE: "corporativo.html",
    TemplateType.WEDDING: "boda.html",
    TemplateType.CELEBRATION: "celebracion.html",
    TemplateType.EVENT: "evento.html",
    TemplateType.INVOICE: "factura.html",
}


TEMPLATE_CONFIGS: Dict[str, Dict[str, Any]] = {
    TemplateType.CORPORATE: {
        "id": "corporate",
        "name": "Corporativo",
        "emoji": "🏢",
        "description": "Diseño formal y profesional para empresas y negocios",
        "tone": "formal, profesional, ejecutivo",
        "colors": {
            "primary": "#2c3e50",
            "secondary": "#34495e",
            "accent": "#3498db",
            "text": "#2c3e50",
            "text_light": "#ffffff",
            "background": "#ffffff",
            "header_bg": "#2c3e50",
            "header_text": "#ffffff",
            "table_header_bg": "#2c3e50",
            "table_header_text": "#ffffff",
            "table_border": "#ddd",
            "border": "#2c3e50",
        },
        "typography": {
            "font_family": "Arial, Helvetica, sans-serif",
            "title_size": "26px",
            "body_size": "13px",
        },
        "layout": {
            "header_style": "fondo sólido oscuro con texto blanco, logo a la izquierda, datos de propuesta a la derecha",
            "container_border": "2px solid #2c3e50",
            "header_background": "sólido #2c3e50",
            "sections": ["header", "client_info", "proposal_details", "products_table", "totals", "comments", "footer"],
        },
        "style_notes": """
- Header con fondo azul oscuro sólido (#2c3e50) y texto blanco
- Borde del contenedor en azul oscuro
- Tabla con header azul oscuro y texto blanco
- Secciones de info del cliente con labels en fondo azul oscuro
- Estilo sobrio, sin gradientes, sin decoraciones
- Tipografía sans-serif limpia
""",
    },

    TemplateType.WEDDING: {
        "id": "wedding",
        "name": "Boda",
        "emoji": "💒",
        "description": "Diseño elegante y romántico para bodas y ceremonias",
        "tone": "elegante, romántico, sofisticado, cálido",
        "colors": {
            "primary": "#d4af37",
            "secondary": "#8b7355",
            "accent": "#e8b4b8",
            "text": "#5a5a5a",
            "text_light": "#ffffff",
            "background": "#ffffff",
            "header_bg": "linear-gradient(to right, #f5f5dc 0%, #fef5f5 100%)",
            "header_text": "#d4af37",
            "table_header_bg": "#d4af37",
            "table_header_text": "#ffffff",
            "table_border": "#e8d5b5",
            "border": "#d4af37",
        },
        "typography": {
            "font_family": "Arial, Helvetica, sans-serif",
            "title_size": "24px",
            "body_size": "13px",
        },
        "layout": {
            "header_style": "fondo con gradiente beige a rosa suave, título dorado, nombres de la pareja a la derecha con corazón",
            "container_border": "2px solid #d4af37",
            "header_background": "gradiente beige-rosa",
            "sections": ["header_with_couple_names", "client_info", "event_details", "products_table", "totals", "comments", "footer"],
            "special_section": "couple_names - Mostrar nombres de la pareja con un corazón (♥) entre ellos",
        },
        "style_notes": """
- Header con gradiente suave de beige (#f5f5dc) a rosa (#fef5f5)
- Color primario dorado (#d4af37) para títulos y acentos
- Nombres de la pareja prominentes con corazón rosa (#e8b4b8)
- Tabla con header dorado y texto blanco
- Bordes suaves en tonos dorados/beige
- Secciones de info con labels en fondo dorado
- Estilo elegante y romántico, sin ser recargado
- Footer con mensaje de agradecimiento cálido
""",
    },

    TemplateType.CELEBRATION: {
        "id": "celebration",
        "name": "Celebración",
        "emoji": "🎉",
        "description": "Diseño festivo y colorido para cumpleaños y fiestas",
        "tone": "festivo, alegre, casual, divertido",
        "colors": {
            "primary": "#ff6b6b",
            "secondary": "#4ecdc4",
            "accent": "#ffe66d",
            "text": "#333333",
            "text_light": "#ffffff",
            "background": "#ffffff",
            "header_bg": "linear-gradient(to right, #fff5e6 0%, #ffe6f0 100%)",
            "header_text": "#ff6b6b",
            "table_header_bg": "#ff6b6b",
            "table_header_text": "#ffffff",
            "table_border": "#ffcdd2",
            "border": "#ff6b6b",
        },
        "typography": {
            "font_family": "Arial, Helvetica, sans-serif",
            "title_size": "24px",
            "body_size": "13px",
        },
        "layout": {
            "header_style": "fondo con gradiente cálido naranja a rosa, título rojo coral, nombre de celebración a la derecha con badge turquesa",
            "container_border": "2px solid #ff6b6b",
            "header_background": "gradiente naranja-rosa",
            "sections": ["header_with_celebration", "client_info", "event_details", "products_table", "totals", "comments", "footer"],
            "special_section": "celebration_tag - Badge turquesa con tipo de celebración (ej: 'Cumpleaños #30')",
        },
        "style_notes": """
- Header con gradiente cálido de naranja (#fff5e6) a rosa (#ffe6f0)
- Color primario rojo coral (#ff6b6b) para títulos y acentos
- Badge turquesa (#4ecdc4) para tipo de celebración
- Tabla con header rojo coral y texto blanco
- Bordes suaves en tonos rosados
- Secciones de info con labels en fondo rojo coral
- Estilo festivo pero profesional
- Detalles coloridos sin ser infantil
""",
    },

    TemplateType.EVENT: {
        "id": "event",
        "name": "Evento",
        "emoji": "🎪",
        "description": "Diseño moderno y dinámico para eventos corporativos y conferencias",
        "tone": "moderno, dinámico, profesional, innovador",
        "colors": {
            "primary": "#5d5fef",
            "secondary": "#9b9bff",
            "accent": "#ff7b7b",
            "text": "#333333",
            "text_light": "#ffffff",
            "background": "#ffffff",
            "header_bg": "linear-gradient(to right, #f8f8ff 0%, #fff5f0 100%)",
            "header_text": "#5d5fef",
            "table_header_bg": "#5d5fef",
            "table_header_text": "#ffffff",
            "table_border": "#d0d0ff",
            "border": "#5d5fef",
        },
        "typography": {
            "font_family": "Arial, Helvetica, sans-serif",
            "title_size": "24px",
            "body_size": "13px",
        },
        "layout": {
            "header_style": "fondo con gradiente lavanda a melocotón suave, título púrpura, nombre del evento a la derecha con badge coral",
            "container_border": "2px solid #5d5fef",
            "header_background": "gradiente lavanda-melocotón",
            "sections": ["header_with_event", "client_info", "event_details", "products_table", "totals", "comments", "footer"],
            "special_section": "event_tag - Badge coral con tipo de evento (ej: 'Conferencia • 2 Días')",
        },
        "style_notes": """
- Header con gradiente suave de lavanda (#f8f8ff) a melocotón (#fff5f0)
- Color primario púrpura (#5d5fef) para títulos y acentos
- Badge coral (#ff7b7b) para tipo de evento
- Tabla con header púrpura y texto blanco
- Bordes suaves en tonos lavanda
- Secciones de info con labels en fondo púrpura
- Estilo moderno y tech-friendly
- Grid layout para detalles del evento
""",
    },

    TemplateType.INVOICE: {
        "id": "invoice",
        "name": "Factura / Cotización",
        "emoji": "📄",
        "description": "Diseño minimalista y limpio estilo factura o cotización formal",
        "tone": "minimalista, limpio, formal, directo",
        "colors": {
            "primary": "#000000",
            "secondary": "#666666",
            "accent": "#0066cc",
            "text": "#000000",
            "text_light": "#ffffff",
            "background": "#ffffff",
            "header_bg": "#ffffff",
            "header_text": "#000000",
            "table_header_bg": "#f5f5f5",
            "table_header_text": "#000000",
            "table_border": "#000000",
            "border": "#000000",
        },
        "typography": {
            "font_family": "Arial, Helvetica, sans-serif",
            "title_size": "28px",
            "body_size": "12px",
        },
        "layout": {
            "header_style": "fondo blanco limpio, nombre de empresa grande y bold, datos de factura a la derecha",
            "container_border": "1px solid #000",
            "header_background": "blanco limpio",
            "sections": ["header", "client_info", "invoice_details", "products_table", "totals", "terms_conditions", "footer"],
            "special_section": "terms_conditions - Incluir sección de términos y condiciones con texto legal",
        },
        "style_notes": """
- Header blanco limpio sin fondo de color, solo bordes negros
- Tipografía grande y bold para nombre de empresa
- Tabla con header gris claro (#f5f5f5) y texto negro
- Bordes negros sólidos en toda la tabla
- Estilo minimalista: solo blanco, negro y gris
- Sección de términos y condiciones al final
- Números de factura/cotización prominentes
- Sin decoraciones, sin gradientes, sin colores
- Totales con fondo gris claro para destacar
""",
    },

    TemplateType.CUSTOM: {
        "id": "custom",
        "name": "Personalizado",
        "emoji": "🎨",
        "description": "Usa tu branding personalizado (logo, colores, estilo propio)",
        "tone": "según branding del usuario",
        "colors": {},
        "typography": {},
        "layout": {
            "sections": ["header", "client_info", "products_table", "totals", "footer"],
        },
        "style_notes": "Usa el branding personalizado del usuario. Si no tiene branding, usa estilo corporativo por defecto.",
    },
}


TEMPLATE_ALIASES = {
    # ES -> EN
    "corporativo": TemplateType.CORPORATE.value,
    "boda": TemplateType.WEDDING.value,
    "celebracion": TemplateType.CELEBRATION.value,
    "fiesta": TemplateType.CELEBRATION.value,
    "evento": TemplateType.EVENT.value,
    "factura": TemplateType.INVOICE.value,
    "cotizacion": TemplateType.INVOICE.value,
    "personalizado": TemplateType.CUSTOM.value,
}


def normalize_template_type(template_type: Optional[str]) -> TemplateType:
    """Normaliza alias ES/EN de template_type y retorna un TemplateType válido."""
    raw = (template_type or "").strip().lower()
    raw = "".join(
        ch for ch in unicodedata.normalize("NFKD", raw)
        if not unicodedata.combining(ch)
    )
    normalized = TEMPLATE_ALIASES.get(raw, raw)

    try:
        return TemplateType(normalized)
    except ValueError:
        logger.warning(f"⚠️ Unknown template_type '{template_type}', falling back to 'custom'")
        return TemplateType.CUSTOM


def get_template_config(template_type: str) -> Dict[str, Any]:
    """Obtiene la configuración de un template por su tipo."""
    t_type = normalize_template_type(template_type)
    return TEMPLATE_CONFIGS.get(t_type, TEMPLATE_CONFIGS[TemplateType.CUSTOM])


def get_template_html_reference(template_type: str) -> Optional[str]:
    """Lee el HTML de referencia del template desde el archivo."""
    t_type = normalize_template_type(template_type)
    
    filename = TEMPLATE_FILES.get(t_type)
    if not filename:
        return None
    
    filepath = TEMPLATES_DIR / filename
    if not filepath.exists():
        logger.warning(f"⚠️ Template file not found: {filepath}")
        return None
    
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"❌ Error reading template file {filepath}: {e}")
        return None


def get_all_templates_metadata() -> List[Dict[str, Any]]:
    """Retorna metadata de todos los templates para el frontend (sin HTML)."""
    templates = []
    for t_type, config in TEMPLATE_CONFIGS.items():
        templates.append({
            "id": config["id"],
            "name": config["name"],
            "emoji": config["emoji"],
            "description": config["description"],
            "tone": config["tone"],
            "colors": {
                "primary": config.get("colors", {}).get("primary", "#000000"),
                "secondary": config.get("colors", {}).get("secondary", "#666666"),
                "accent": config.get("colors", {}).get("accent", "#0066cc"),
            },
            "is_custom": t_type == TemplateType.CUSTOM,
        })
    return templates


def build_template_style_instructions(template_type: str) -> str:
    """
    Construye las instrucciones de estilo para inyectar en el prompt del LLM.
    Esta es la función clave: traduce la metadata del template a instrucciones
    claras que el LLM puede seguir para generar HTML con el estilo correcto.
    """
    normalized_template = normalize_template_type(template_type)
    config = get_template_config(normalized_template.value)
    
    if normalized_template == TemplateType.CUSTOM or not config.get("colors"):
        return ""
    
    colors = config["colors"]
    typography = config.get("typography", {})
    layout = config.get("layout", {})
    style_notes = config.get("style_notes", "")
    
    instructions = f"""
## 🎨 ESTILO DEL TEMPLATE: {config['name']} {config['emoji']}

### TONO DEL DOCUMENTO
{config['tone']}

### PALETA DE COLORES (USAR EXACTAMENTE ESTOS COLORES)
- **Color primario:** {colors.get('primary', '#000000')}
- **Color secundario:** {colors.get('secondary', '#666666')}
- **Color de acento:** {colors.get('accent', '#0066cc')}
- **Texto principal:** {colors.get('text', '#333333')}
- **Texto sobre fondo oscuro:** {colors.get('text_light', '#ffffff')}
- **Fondo:** {colors.get('background', '#ffffff')}
- **Header fondo:** {colors.get('header_bg', '#ffffff')}
- **Header texto:** {colors.get('header_text', '#000000')}
- **Tabla header fondo:** {colors.get('table_header_bg', '#f5f5f5')}
- **Tabla header texto:** {colors.get('table_header_text', '#000000')}
- **Tabla bordes:** {colors.get('table_border', '#ddd')}
- **Borde contenedor:** {colors.get('border', '#000000')}

### TIPOGRAFÍA
- **Fuente:** {typography.get('font_family', 'Arial, Helvetica, sans-serif')}
- **Tamaño título:** {typography.get('title_size', '24px')}
- **Tamaño cuerpo:** {typography.get('body_size', '13px')}

### LAYOUT Y ESTRUCTURA
- **Estilo del header:** {layout.get('header_style', 'estándar')}
- **Borde del contenedor:** {layout.get('container_border', '1px solid #000')}
- **Secciones requeridas:** {', '.join(layout.get('sections', []))}
{f"- **Sección especial:** {layout.get('special_section', '')}" if layout.get('special_section') else ''}

### NOTAS DE ESTILO ESPECÍFICAS
{style_notes}

### REGLA CRÍTICA
Genera el HTML siguiendo EXACTAMENTE este estilo visual. NO mezcles con otros estilos.
El documento debe verse como un presupuesto profesional de tipo "{config['name']}".
"""
    return instructions
