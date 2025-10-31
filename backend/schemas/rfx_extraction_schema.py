"""
RFX Function Calling Schema - OpenAI Function Definition
Mapea directamente a la estructura de base de datos V2.2
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, time
from pydantic import BaseModel, validator, Field
from enum import Enum
import json

# ============================================================================
# ENUMS COMPATIBLES CON BASE DE DATOS
# ============================================================================

class RFXType(str, Enum):
    """Tipos de RFX compatibles con DB"""
    RFQ = "rfq"  # Request for Quote
    RFP = "rfp"  # Request for Proposal  
    RFI = "rfi"  # Request for Information

class PriorityLevel(str, Enum):
    """Niveles de prioridad"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"

class ProductCategory(str, Enum):
    """
    ⚠️ DEPRECATED: Categorías rígidas - Usar solo como referencia
    ✅ AI-FIRST: El LLM decide la categoría apropiada según el dominio
    """
    COMIDA = "comida"
    BEBIDA = "bebida"
    SERVICIO = "servicio"
    EQUIPO = "equipo"
    PERSONAL = "personal"
    DECORACION = "decoracion"
    TRANSPORTE = "transporte"
    MATERIAL = "material"  # ✅ Construcción
    HERRAMIENTA = "herramienta"  # ✅ Construcción
    MOBILIARIO = "mobiliario"  # ✅ Oficina/Equipamiento
    TECNOLOGIA = "tecnologia"  # ✅ IT/Electrónica
    OTRO = "otro"

class UnitOfMeasure(str, Enum):
    """
    ⚠️ DEPRECATED: Unidades rígidas - Usar solo como referencia
    ✅ AI-FIRST: El LLM decide la unidad apropiada según el producto
    """
    UNIDADES = "unidades"
    PERSONAS = "personas"
    PAX = "pax"
    KG = "kg"
    GRAMOS = "g"
    LITROS = "litros"
    ML = "ml"
    PORCIONES = "porciones"
    SERVICIOS = "servicios"
    HORAS = "horas"
    DIAS = "dias"
    CAJAS = "cajas"
    PAQUETES = "paquetes"
    VASOS = "vasos"
    # ✅ Agregadas unidades para construcción y otros dominios
    SACO = "saco"
    BARRA = "barra"
    M3 = "m³"
    M2 = "m²"
    METRO = "metro"
    TONELADA = "tonelada"

# ============================================================================
# ESQUEMA PRINCIPAL DE FUNCTION CALLING PARA OPENAI
# ============================================================================

RFX_EXTRACTION_FUNCTION = {
    "type": "function",
    "function": {
        "name": "extract_rfx_data",
        "description": "✅ AI-FIRST MULTI-DOMINIO: Extrae información estructurada de documentos RFX/RFP/RFQ de CUALQUIER industria (catering, construcción, IT, logística, etc.), adaptando categorías y unidades al dominio detectado",
        "parameters": {
            "type": "object",
            "properties": {
                # ============================================================================
                # INFORMACIÓN BÁSICA DEL RFX (Tabla: rfx_v2)
                # ============================================================================
                "title": {
                    "type": "string",
                    "description": "Título descriptivo del proyecto o solicitud RFX. Ej: 'Evento Corporativo GlobalTech 120 personas'"
                },
                "description": {
                    "type": "string",
                    "description": "Descripción detallada del proyecto, evento o servicio solicitado"
                },
                "rfx_type": {
                    "type": "string",
                    "enum": ["rfq", "rfp", "rfi"],
                    "description": "Tipo de RFX detectado: rfq (cotización), rfp (propuesta), rfi (información)"
                },
                "priority": {
                    "type": "string", 
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Nivel de prioridad si se menciona explícitamente en el documento"
                },
                
                # ============================================================================
                # FECHAS CRÍTICAS (Tabla: rfx_v2)
                # ============================================================================
                "submission_deadline": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Fecha límite para envío de propuestas (formato ISO 8601: YYYY-MM-DDTHH:MM:SSZ)"
                },
                "expected_decision_date": {
                    "type": "string",
                    "format": "date-time", 
                    "description": "Fecha esperada de decisión (formato ISO 8601)"
                },
                "project_start_date": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Fecha de inicio del proyecto (formato ISO 8601)"
                },
                "project_end_date": {
                    "type": "string", 
                    "format": "date-time",
                    "description": "Fecha de finalización del proyecto (formato ISO 8601)"
                },
                "delivery_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Fecha de entrega del evento/servicio (formato YYYY-MM-DD). Usar mapeo correcto: enero=01, febrero=02, marzo=03, abril=04, mayo=05, junio=06, julio=07, agosto=08, septiembre=09, octubre=10, noviembre=11, diciembre=12"
                },
                "delivery_time": {
                    "type": "string",
                    "description": "Hora de entrega del evento/servicio (formato HH:MM)"
                },
                
                # ============================================================================
                # PRESUPUESTO Y MONEDA (Tabla: rfx_v2)
                # ============================================================================
                "budget_range_min": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Presupuesto mínimo mencionado en el documento"
                },
                "budget_range_max": {
                    "type": "number", 
                    "minimum": 0,
                    "description": "Presupuesto máximo mencionado en el documento"
                },
                "currency": {
                    "type": "string",
                    "enum": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "MXN", "BRL", "ARS", "COP", "PEN", "CLP", "CHF", "VES", "VED"],
                    "description": "Código de moneda ISO 4217. Analizar contexto geográfico y símbolos: $=USD por defecto, €=EUR, £=GBP, Bs=VES"
                },
                
                # ============================================================================
                # UBICACIÓN DEL EVENTO (Tabla: rfx_v2)
                # ============================================================================
                "event_location": {
                    "type": "string",
                    "description": "Ubicación completa del evento (dirección, venue, instalación específica)"
                },
                "event_city": {
                    "type": "string",
                    "description": "Ciudad donde se realizará el evento"
                },
                "event_state": {
                    "type": "string",
                    "description": "Estado, provincia, región o departamento del evento"
                },
                "event_country": {
                    "type": "string",
                    "description": "País del evento. Inferir desde dirección, idioma, o contexto cultural"
                },
                
                # ============================================================================
                # REQUIREMENTS Y ESPECIFICACIONES (Tabla: rfx_v2)
                # ============================================================================
                "requirements": {
                    "type": "string",
                    "description": "Requerimientos técnicos, funcionales y restricciones específicas del cliente. Incluir alergias, preferencias dietéticas, restricciones logísticas"
                },
                "requirements_confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Nivel de confianza 0.0-1.0 sobre la completitud y claridad de los requirements extraídos"
                },
                
                # ============================================================================
                # PRODUCTOS Y SERVICIOS SOLICITADOS (Tabla: rfx_products)
                # ============================================================================
                "requested_products": {
                    "type": "array",
                    "description": "Lista COMPLETA de todos los productos, servicios, comidas y elementos solicitados. CRÍTICO: encontrar TODOS los elementos mencionados",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {
                                "type": "string",
                                "description": "Nombre exacto del producto/servicio/comida/bebida tal como aparece en el documento"
                            },
                            "description": {
                                "type": "string",
                                "description": "Descripción detallada del producto, incluyendo especificaciones, sabores, características especiales"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["comida", "bebida", "servicio", "equipo", "personal", "decoracion", "transporte", "material", "herramienta", "mobiliario", "tecnologia", "otro"],
                                "description": "✅ AI-FIRST: Categoría del producto según el dominio (catering: comida/bebida, construcción: material/herramienta, oficina: mobiliario/tecnologia, etc.)"
                            },
                            "quantity": {
                                "type": "number",
                                "minimum": 1,
                                "description": "Cantidad numérica exacta del producto (convertir palabras a números: 'cien'=100, 'docena'=12)"
                            },
                            "unit_of_measure": {
                                "type": "string",
                                "enum": ["unidades", "personas", "pax", "kg", "g", "litros", "ml", "porciones", "servicios", "horas", "dias", "cajas", "paquetes", "vasos", "saco", "barra", "m³", "m²", "metro", "tonelada"],
                                "description": "✅ AI-FIRST: Unidad apropiada según el producto y dominio (catering: kg/litros/porciones, construcción: saco/barra/m³, etc.)"
                            },
                            "specifications": {
                                "type": "string",
                                "description": "Especificaciones técnicas adicionales: tamaño, ingredientes, preparación, presentación, etc."
                            },
                            "is_mandatory": {
                                "type": "boolean",
                                "description": "Si el producto es obligatorio (true) u opcional (false). Asumir true si no se especifica"
                            },
                            "priority_order": {
                                "type": "number",
                                "minimum": 1,
                                "description": "Orden de prioridad basado en posición en el documento (1=más importante)"
                            },
                            "costo_unitario": {
                                "type": "number",
                                "minimum": 0,
                                "description": "💰 COSTO UNITARIO DEL PROVEEDOR: Si hay lista de precios en los documentos, busca el costo de este producto. Matching flexible (ignora mayúsculas, acentos, plurales). Si NO encuentras el producto en la lista → 0.0. NUNCA inventes costos."
                            }
                        },
                        "required": ["product_name", "category", "quantity", "unit_of_measure"]
                    }
                },
                
                # ============================================================================
                # CRITERIOS DE EVALUACIÓN (Tabla: rfx_v2 - evaluation_criteria JSONB)
                # ============================================================================
                "evaluation_criteria": {
                    "type": "array",
                    "description": "Criterios de evaluación de propuestas mencionados explícitamente",
                    "items": {
                        "type": "object",
                        "properties": {
                            "criterion": {
                                "type": "string",
                                "description": "Nombre del criterio (precio, experiencia, calidad, tiempo de entrega, etc.)"
                            },
                            "weight": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                                "description": "Peso porcentual del criterio si se menciona explícitamente"
                            },
                            "description": {
                                "type": "string",
                                "description": "Descripción detallada del criterio y cómo se evaluará"
                            }
                        },
                        "required": ["criterion"]
                    }
                },
                
                # ============================================================================
                # INFORMACIÓN DE EMPRESA (Para tabla: companies)
                # ============================================================================
                "company_info": {
                    "type": "object",
                    "description": "Información de la empresa/organización que solicita el servicio",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Nombre completo de la empresa/organización (ej: Inversiones GlobalTech C.A., Chevron Corporation)"
                        },
                        "industry": {
                            "type": "string", 
                            "description": "Industria o sector de la empresa si se puede inferir"
                        },
                        "tax_id": {
                            "type": "string",
                            "description": "RIF, RFC, o identificador fiscal si se menciona"
                        },
                        "company_email": {
                            "type": "string",
                            "format": "email",
                            "description": "Email corporativo general (ej: info@empresa.com, contacto@empresa.com)"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Teléfono principal de la empresa"
                        },
                        "address": {
                            "type": "string",
                            "description": "Dirección completa de la empresa"
                        },
                        "city": {
                            "type": "string",
                            "description": "Ciudad de la empresa"
                        },
                        "state": {
                            "type": "string", 
                            "description": "Estado/provincia de la empresa"
                        },
                        "country": {
                            "type": "string",
                            "description": "País de la empresa"
                        }
                    }
                },
                
                # ============================================================================
                # INFORMACIÓN DE SOLICITANTE (Para tabla: requesters)  
                # ============================================================================
                "requester_info": {
                    "type": "object",
                    "description": "Información de la persona individual que hace la solicitud",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre completo de la persona solicitante"
                        },
                        "email": {
                            "type": "string",
                            "format": "email", 
                            "description": "Email personal/profesional del solicitante (ej: juan.perez@empresa.com)"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Teléfono directo del solicitante"
                        },
                        "position": {
                            "type": "string",
                            "description": "Cargo/puesto del solicitante en la empresa"
                        },
                        "department": {
                            "type": "string",
                            "description": "Departamento o área del solicitante (RRHH, Compras, Marketing, etc.)"
                        }
                    }
                },
                
                # ============================================================================
                # METADATOS Y CONFIANZA (Tabla: rfx_v2 - metadata_json JSONB)
                # ============================================================================
                "extraction_confidence": {
                    "type": "object",
                    "description": "Scores de confianza para diferentes aspectos de la extracción",
                    "properties": {
                        "overall_confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confianza general de toda la extracción (0.0-1.0)"
                        },
                        "products_confidence": {
                            "type": "number", 
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confianza en haber encontrado TODOS los productos mencionados"
                        },
                        "dates_confidence": {
                            "type": "number",
                            "minimum": 0.0, 
                            "maximum": 1.0,
                            "description": "Confianza en las fechas extraídas y su formato"
                        },
                        "contact_confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0, 
                            "description": "Confianza en la información de contacto (empresa/solicitante)"
                        }
                    },
                    "required": ["overall_confidence", "products_confidence"]
                },
                
                # ============================================================================
                # INFORMACIÓN ADICIONAL (metadata_json)
                # ============================================================================
                "additional_metadata": {
                    "type": "object",
                    "description": "Información adicional y contextual no categorizada",
                    "properties": {
                        "detected_language": {
                            "type": "string",
                            "description": "Idioma detectado del documento"
                        },
                        "document_structure": {
                            "type": "string",
                            "description": "Estructura del documento (formal, informal, lista, tabla, etc.)"
                        },
                        "special_requirements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Requerimientos especiales (halal, kosher, vegano, sin gluten, alergias específicas)"
                        },
                        "mentions_competitors": {
                            "type": "boolean",
                            "description": "Si el documento menciona otros proveedores o competidores"
                        },
                        "urgency_indicators": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Indicadores de urgencia encontrados en el texto"
                        },
                        "budget_indicators": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Frases que indican sensibilidad al precio o presupuesto"
                        },
                        "quality_indicators": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "Frases que indican enfoque en calidad sobre precio"
                        },
                        "original_text_sample": {
                            "type": "string",
                            "description": "Fragmento más relevante del texto original (máximo 500 chars)"
                        }
                    }
                }
            },
            "required": [
                "title", 
                "description", 
                "requested_products", 
                "extraction_confidence",
                "company_info",
                "requester_info"
            ]
        }
    }
}

# ============================================================================
# MODELO PYDANTIC PARA VALIDACIÓN DE RESULTADOS
# ============================================================================

class ProductItem(BaseModel):
    """Modelo para productos individuales"""
    product_name: str
    description: Optional[str] = None
    category: ProductCategory
    quantity: float = Field(ge=1)
    unit_of_measure: UnitOfMeasure
    costo_unitario: Optional[float] = Field(default=0.0, ge=0)
    specifications: Optional[str] = None
    is_mandatory: bool = True
    priority_order: int = Field(ge=1, default=1)

    @validator('quantity')
    def validate_quantity_positive(cls, v):
        if v <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return v

class EvaluationCriterion(BaseModel):
    """Criterio de evaluación"""
    criterion: str
    weight: Optional[float] = Field(None, ge=0, le=100)
    description: Optional[str] = None

class CompanyInfo(BaseModel):
    """Información de la empresa"""
    company_name: Optional[str] = None
    industry: Optional[str] = None
    tax_id: Optional[str] = None
    company_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Mexico"  # Default según DB

class RequesterInfo(BaseModel):
    """Información del solicitante"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None

class ExtractionConfidence(BaseModel):
    """Scores de confianza"""
    overall_confidence: float = Field(ge=0.0, le=1.0)
    products_confidence: float = Field(ge=0.0, le=1.0)
    dates_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    contact_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class AdditionalMetadata(BaseModel):
    """Metadatos adicionales"""
    detected_language: Optional[str] = None
    document_structure: Optional[str] = None
    special_requirements: Optional[List[str]] = None
    mentions_competitors: Optional[bool] = None
    urgency_indicators: Optional[List[str]] = None
    budget_indicators: Optional[List[str]] = None
    quality_indicators: Optional[List[str]] = None
    original_text_sample: Optional[str] = None

class RFXFunctionResult(BaseModel):
    """Modelo principal para validar el resultado de function calling"""
    
    # Información básica
    title: str
    description: str
    rfx_type: Optional[RFXType] = RFXType.RFQ
    priority: Optional[PriorityLevel] = PriorityLevel.MEDIUM
    
    # Fechas (ISO format strings que se convertirán a datetime)
    submission_deadline: Optional[str] = None
    expected_decision_date: Optional[str] = None
    project_start_date: Optional[str] = None
    project_end_date: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time: Optional[str] = None
    
    # Presupuesto
    budget_range_min: Optional[float] = Field(None, ge=0)
    budget_range_max: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    
    # Ubicación
    event_location: Optional[str] = None
    event_city: Optional[str] = None
    event_state: Optional[str] = None
    event_country: Optional[str] = "Mexico"
    
    # Requirements
    requirements: Optional[str] = None
    requirements_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Productos (REQUERIDO)
    requested_products: List[ProductItem] = Field(min_items=1)
    
    # Evaluación
    evaluation_criteria: Optional[List[EvaluationCriterion]] = None
    
    # Contacto (REQUERIDO)
    company_info: CompanyInfo
    requester_info: RequesterInfo
    
    # Confianza (REQUERIDO)
    extraction_confidence: ExtractionConfidence
    
    # Metadatos adicionales
    additional_metadata: Optional[AdditionalMetadata] = None
    
    @validator('currency')
    def validate_currency_code(cls, v):
        """Validar código de moneda"""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "MXN", "BRL", "ARS", "COP", "PEN", "CLP", "CHF", "VES", "VED"]
        if v not in valid_currencies:
            return "USD"  # Default fallback
        return v
    
    @validator('budget_range_max')
    def validate_budget_range(cls, v, values):
        """Validar que budget_max >= budget_min"""
        if v is not None and values.get('budget_range_min') is not None:
            if v < values['budget_range_min']:
                raise ValueError("El presupuesto máximo debe ser mayor o igual al mínimo")
        return v
    
    @validator('requested_products')
    def validate_products_not_empty(cls, v):
        """Validar que hay al menos un producto"""
        if not v:
            raise ValueError("Se requiere al menos un producto en la solicitud")
        return v

    class Config:
        """Configuración del modelo"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # No permitir campos adicionales

# ============================================================================
# FUNCIÓN DE UTILIDAD PARA CONVERSIÓN
# ============================================================================

def function_result_to_db_dict(result: RFXFunctionResult) -> Dict[str, Any]:
    """
    Convierte un RFXFunctionResult a diccionario compatible con BD v2.2
    
    Args:
        result: Resultado validado del function calling
        
    Returns:
        Dict mapeado para inserción en BD
    """
    # Información básica para tabla rfx_v2
    rfx_data = {
        "title": result.title,
        "description": result.description,
        "rfx_type": result.rfx_type if result.rfx_type else "rfq",
        "priority": result.priority if result.priority else "medium",
        "currency": result.currency,
        
        # Fechas (convertir strings ISO a datetime si están presentes)
        "submission_deadline": result.submission_deadline,
        "expected_decision_date": result.expected_decision_date,
        "project_start_date": result.project_start_date,
        "project_end_date": result.project_end_date,
        "delivery_date": result.delivery_date,
        "delivery_time": result.delivery_time,
        
        # Presupuesto
        "budget_range_min": result.budget_range_min,
        "budget_range_max": result.budget_range_max,
        
        # Ubicación del evento
        "event_location": result.event_location,
        "event_city": result.event_city,
        "event_state": result.event_state,
        "event_country": result.event_country,
        
        # Requirements
        "requirements": result.requirements,
        "requirements_confidence": result.requirements_confidence,
        
        # Metadatos JSON
        "evaluation_criteria": [c.dict() for c in result.evaluation_criteria] if result.evaluation_criteria else None,
        "metadata_json": {
            "extraction_confidence": result.extraction_confidence.dict(),
            "additional_metadata": result.additional_metadata.dict() if result.additional_metadata else {},
            "extracted_by": "function_calling_v2a",
            "schema_version": "2.2"
        }
    }
    
    # Productos para tabla rfx_products
    products_data = []
    for i, product in enumerate(result.requested_products, 1):
        products_data.append({
            "product_name": product.product_name,
            "description": product.description,
            "category": product.category.value,  # 🔧 FIX: Convertir enum a string
            "quantity": int(product.quantity),
            "unit_cost": product.costo_unitario if product.costo_unitario and product.costo_unitario > 0 else 0.0,  # ✅ Mapear costo_unitario a unit_cost
            "unit_of_measure": product.unit_of_measure.value,  # 🔧 FIX: Convertir enum a string
            "specifications": {"details": product.specifications} if product.specifications else None,
            "is_mandatory": product.is_mandatory,
            "priority_order": product.priority_order,
            "notes": None  # Se puede agregar si se necesita
        })
    
    # Información de empresa y solicitante
    company_data = result.company_info.dict(exclude_none=True) if result.company_info else {}
    requester_data = result.requester_info.dict(exclude_none=True) if result.requester_info else {}
    
    return {
        "rfx_data": rfx_data,
        "products_data": products_data,
        "company_data": company_data,
        "requester_data": requester_data
    }
