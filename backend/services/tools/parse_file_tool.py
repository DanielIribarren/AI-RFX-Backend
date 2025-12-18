"""
Tool: parse_file_tool

Propósito: Ayudar al agente a extraer productos de archivos (Excel, CSV, texto, imágenes)
Filosofía KISS: El LLM interpreta el contenido, la tool solo estructura

Fase 2 - Sprint 4
"""

from langchain.tools import tool
from typing import Dict, Any, List
import logging
import json
import re

logger = logging.getLogger(__name__)


@tool
def parse_file_tool(file_content: str, file_name: str = "") -> Dict[str, Any]:
    """
    Ayuda al agente a extraer productos de archivos.
    
    Esta tool NO hace parsing complejo. El LLM es quien interpreta el contenido.
    La tool solo proporciona el contenido estructurado para que el agente lo procese.
    
    Args:
        file_content: Contenido del archivo (texto, CSV, JSON, o texto extraído de imagen/PDF)
        file_name: Nombre del archivo (opcional, ayuda a determinar el tipo)
    
    Returns:
        Dict con el contenido estructurado y sugerencias para el agente
    
    Ejemplos de uso:
        Usuario: "Agrega los productos de este archivo Excel"
        Agente: 
          1. Recibe file_content del archivo
          2. Llama a parse_file_tool(file_content, "productos.xlsx")
          3. Interpreta el resultado
          4. Llama a add_products_tool con los productos extraídos
    
    IMPORTANTE:
    - El agente es quien decide qué hacer con el contenido
    - Esta tool solo facilita el acceso estructurado
    - El LLM es mejor parseando que código rígido
    """
    
    try:
        logger.info(f"📄 parse_file_tool called: file_name={file_name}, content_length={len(file_content)}")
        
        if not file_content or len(file_content.strip()) == 0:
            logger.warning("⚠️ Empty file content")
            return {
                "status": "error",
                "message": "El archivo está vacío o no se pudo leer",
                "products": [],
                "raw_content": ""
            }
        
        # Detectar tipo de contenido
        content_type = _detect_content_type(file_content, file_name)
        
        logger.info(f"📊 Detected content type: {content_type}")
        
        # Retornar contenido estructurado para que el LLM lo interprete
        result = {
            "status": "success",
            "content_type": content_type,
            "raw_content": file_content,
            "file_name": file_name,
            "suggestions": _get_parsing_suggestions(content_type),
            "message": f"Archivo '{file_name}' listo para procesar. Tipo detectado: {content_type}"
        }
        
        # Si detectamos estructura tabular simple, intentar pre-parsear
        if content_type in ["csv", "tsv", "table"]:
            try:
                parsed_data = _simple_table_parse(file_content)
                if parsed_data:
                    result["parsed_data"] = parsed_data
                    result["message"] += f". Se detectaron {len(parsed_data)} filas de datos."
            except Exception as e:
                logger.warning(f"⚠️ Could not pre-parse table: {e}")
        
        logger.info(f"✅ File parsed successfully: {file_name}")
        
        return result
    
    except Exception as e:
        error_msg = f"Error parsing file: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "raw_content": file_content[:500] if file_content else ""
        }


def _detect_content_type(content: str, file_name: str) -> str:
    """
    Detecta el tipo de contenido del archivo.
    
    KISS: Solo detectamos tipos básicos, el LLM hace el resto.
    """
    
    # Por extensión
    if file_name:
        lower_name = file_name.lower()
        if lower_name.endswith('.csv'):
            return "csv"
        elif lower_name.endswith('.tsv'):
            return "tsv"
        elif lower_name.endswith('.json'):
            return "json"
        elif lower_name.endswith(('.xlsx', '.xls')):
            return "excel"
        elif lower_name.endswith('.txt'):
            return "text"
        elif lower_name.endswith(('.jpg', '.jpeg', '.png', '.pdf')):
            return "ocr"  # Ya viene procesado por OCR del frontend
    
    # Por contenido
    content_sample = content[:1000].strip()
    
    # JSON
    if content_sample.startswith('{') or content_sample.startswith('['):
        try:
            json.loads(content_sample)
            return "json"
        except:
            pass
    
    # CSV/TSV (detectar separadores)
    lines = content_sample.split('\n')[:5]
    if len(lines) > 1:
        # Contar comas y tabs
        comma_count = sum(line.count(',') for line in lines)
        tab_count = sum(line.count('\t') for line in lines)
        
        if comma_count > tab_count and comma_count > len(lines):
            return "csv"
        elif tab_count > comma_count and tab_count > len(lines):
            return "tsv"
    
    # Detectar si parece tabla (múltiples líneas con estructura similar)
    if len(lines) > 2:
        # Si las líneas tienen longitudes similares, probablemente es tabla
        line_lengths = [len(line.split()) for line in lines if line.strip()]
        if line_lengths and max(line_lengths) - min(line_lengths) <= 2:
            return "table"
    
    return "text"


def _get_parsing_suggestions(content_type: str) -> List[str]:
    """
    Retorna sugerencias para que el agente sepa cómo interpretar el contenido.
    
    KISS: Solo sugerencias simples, el LLM decide.
    """
    
    suggestions = {
        "csv": [
            "Busca la fila de encabezados (nombre, cantidad, precio, etc.)",
            "Cada fila después del encabezado es un producto",
            "Ignora filas vacías o con datos incompletos"
        ],
        "tsv": [
            "Similar a CSV pero separado por tabs",
            "Busca columnas: nombre, cantidad, precio unitario"
        ],
        "json": [
            "Busca arrays de productos",
            "Mapea campos JSON a: name, quantity, price_unit"
        ],
        "excel": [
            "El contenido ya fue convertido a texto",
            "Busca estructura tabular (filas y columnas)"
        ],
        "table": [
            "Detecta la estructura de columnas",
            "Primera fila suele ser encabezados"
        ],
        "text": [
            "Busca patrones como: '10 sillas a $150'",
            "Extrae: cantidad, nombre del producto, precio"
        ],
        "ocr": [
            "Texto extraído de imagen/PDF",
            "Puede tener errores de OCR",
            "Busca patrones de productos y precios"
        ]
    }
    
    return suggestions.get(content_type, [
        "Analiza el contenido y extrae productos",
        "Busca: nombre, cantidad, precio unitario"
    ])


def _simple_table_parse(content: str) -> List[Dict[str, str]]:
    """
    Intenta parsear contenido tabular simple (CSV/TSV).
    
    KISS: Solo casos simples, el LLM maneja casos complejos.
    """
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    if len(lines) < 2:
        return []
    
    # Detectar separador
    separator = ','
    if '\t' in lines[0]:
        separator = '\t'
    
    # Primera línea = headers
    headers = [h.strip() for h in lines[0].split(separator)]
    
    # Resto = datos
    parsed_rows = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(separator)]
        
        # Solo si tiene el mismo número de columnas
        if len(values) == len(headers):
            row = dict(zip(headers, values))
            parsed_rows.append(row)
    
    return parsed_rows
