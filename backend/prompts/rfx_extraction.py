"""
🎯 RFX Extraction Prompts - AI-FIRST approach
Prompts centralizados para extracción de datos RFX, separados de la lógica de negocio.
"""


class RFXExtractionPrompt:
    """
    Prompts para extracción de datos RFX con OpenAI Function Calling.
    
    Principio AI-FIRST: El LLM hace el trabajo inteligente de extracción,
    validación y normalización. El código solo orquesta.
    """
    
    SYSTEM_PROMPT = """Eres un experto en análisis de documentos RFX (Request for Quote/Proposal/Information).

Tu trabajo es extraer TODA la información estructurada de documentos de cualquier industria:
- Catering y eventos
- Construcción y materiales
- IT y tecnología
- Logística y transporte
- Servicios profesionales
- Cualquier otro dominio

CAPACIDADES CLAVE:
1. **Detección de dominio**: Identifica automáticamente la industria del documento
2. **Adaptación de categorías**: Usa categorías apropiadas al dominio detectado
3. **Normalización de unidades**: Convierte unidades a formato estándar
4. **Extracción completa**: TODOS los productos, fechas, contactos, requisitos
5. **Validación inteligente**: Emails, teléfonos, fechas en cualquier formato

REGLAS ESTRICTAS:
- Si un campo no existe en el documento → usar null (no inventar datos)
- Extraer TODOS los productos encontrados (no limitar a 5 o 10)
- Normalizar cantidades a números enteros
- Detectar fechas en CUALQUIER formato (DD/MM/YYYY, MM-DD-YYYY, "15 de marzo", etc.)
- Emails y teléfonos deben ser válidos o null"""

    USER_TEMPLATE = """Analiza el siguiente documento RFX y extrae TODA la información estructurada.

{multi_doc_warning}

DOCUMENTO:
{document_text}

INSTRUCCIONES ESPECÍFICAS:
1. **Título**: Genera un título descriptivo si no existe explícito
2. **Productos**: Extrae TODOS los productos con cantidad, unidad y categoría apropiada
3. **Fechas**: Detecta fecha de entrega, fecha límite de respuesta
4. **Contactos**: Email, teléfono, nombre del solicitante y empresa
5. **Ubicación**: Lugar del evento o entrega
6. **Requisitos**: Cualquier requisito especial o nota importante

VALIDACIONES:
- Cantidades deben ser números positivos
- Unidades deben ser apropiadas al producto (personas, kg, unidades, m², etc.)
- Emails deben tener formato válido
- Fechas en formato ISO 8601 (YYYY-MM-DD)

Usa la función extract_rfx_data para proporcionar la respuesta estructurada."""

    @classmethod
    def build_messages(cls, document_text: str, has_multiple_docs: bool = False) -> list:
        """
        Construye los mensajes para OpenAI Chat Completion.
        
        Args:
            document_text: Texto del documento a analizar
            has_multiple_docs: Si el texto contiene múltiples documentos separados
            
        Returns:
            Lista de mensajes en formato OpenAI
        """
        # Warning para múltiples documentos
        multi_doc_warning = ""
        if has_multiple_docs:
            doc_count = document_text.count("### SOURCE:")
            multi_doc_warning = f"""⚠️ ATENCIÓN: Este texto contiene {doc_count} DOCUMENTOS DIFERENTES separados por "### SOURCE:".
Analiza TODOS los documentos antes de extraer la información.
Consolida productos duplicados y prioriza la información más reciente."""
        
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": cls.USER_TEMPLATE.format(
                document_text=document_text,
                multi_doc_warning=multi_doc_warning
            )}
        ]
    
    @classmethod
    def build_retry_messages(cls, document_text: str, previous_error: str) -> list:
        """
        Construye mensajes para retry después de un error.
        
        Args:
            document_text: Texto del documento
            previous_error: Descripción del error anterior
            
        Returns:
            Lista de mensajes con contexto del error
        """
        retry_prompt = f"""El intento anterior falló con el siguiente error:
{previous_error}

Por favor, intenta nuevamente con más cuidado en:
- Validación de formatos (emails, fechas, teléfonos)
- Normalización de unidades
- Cantidades como números enteros positivos

DOCUMENTO:
{document_text}

Usa la función extract_rfx_data para proporcionar la respuesta estructurada."""
        
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": retry_prompt}
        ]
