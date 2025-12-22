# 🤖 DOCUMENTACIÓN BACKEND - CHAT CONVERSACIONAL RFX
## Agente de IA para Actualización de RFX

**Proyecto:** AI-RFX Backend  
**Feature:** API de Chat Conversacional con IA  
**Fecha:** Diciembre 1, 2025  
**Versión:** 1.0  
**Filosofía:** AI-FIRST + KISS + No Hardcoded Logic

---

## 📋 TABLA DE CONTENIDOS

1. [Visión General](#visión-general)
2. [Principios de Arquitectura](#principios-de-arquitectura)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Endpoints de API](#endpoints-de-api)
5. [Agente de IA](#agente-de-ia)
6. [System Prompt Design](#system-prompt-design)
7. [Procesamiento de Mensajes](#procesamiento-de-mensajes)
8. [Generación de Cambios](#generación-de-cambios)
9. [Persistencia de Datos](#persistencia-de-datos)
10. [Casos de Uso Implementados](#casos-de-uso-implementados)
11. [Testing y Validación](#testing-y-validación)

---

## 🎯 VISIÓN GENERAL

### ¿Qué es?

Un **agente de IA conversacional** que procesa solicitudes en lenguaje natural y genera cambios estructurados para actualizar RFX.

**Flujo:**
```
Usuario: "Agregar 20 refrescos"
    ↓
Backend recibe mensaje + contexto del RFX
    ↓
Agente de IA analiza intención
    ↓
IA genera cambios estructurados: [{ type: "add_product", data: {...} }]
    ↓
Backend retorna respuesta + cambios
    ↓
Frontend aplica cambios en UI
```

### Responsabilidades del Backend

1. ✅ **Recibir mensajes** del frontend con contexto
2. ✅ **Procesar con IA** (OpenAI/Anthropic)
3. ✅ **Generar cambios estructurados** (JSON)
4. ✅ **Validar cambios** antes de retornar
5. ✅ **Persistir historial** de conversación
6. ✅ **Procesar archivos** adjuntos si los hay
7. ✅ **Detectar ambigüedades** y pedir confirmación

---

## 🏛️ PRINCIPIOS DE ARQUITECTURA

### 1. AI-FIRST (La IA es el Cerebro)

```python
# ❌ MAL: Lógica hardcoded
def process_message(message: str):
    if "agregar" in message.lower():
        # Parsear manualmente...
        product_name = extract_product_name(message)
        quantity = extract_quantity(message)
        return add_product(product_name, quantity)
    elif "eliminar" in message.lower():
        # Más lógica hardcoded...
        
# ✅ BIEN: IA decide todo
def process_message(message: str, context: dict):
    # System prompt + contexto + mensaje del usuario
    response = ai_agent.process(
        system_prompt=CHAT_SYSTEM_PROMPT,
        context=context,
        user_message=message
    )
    
    # IA retorna JSON estructurado con cambios
    return response.changes
```

**Principio:** El backend NO interpreta el mensaje, solo lo pasa a la IA y ejecuta lo que la IA decide.

### 2. KISS (Keep It Simple)

**Estructura simple:**
```
routes/
  └── rfx_chat.py          # Endpoints del chat

services/
  └── chat_agent.py        # Agente de IA (un solo archivo)

prompts/
  └── chat_system_prompt.py # System prompt

models/
  └── chat_models.py       # Pydantic models
```

**No crear:**
- ❌ Múltiples clases de "IntentDetector", "ActionParser", etc.
- ❌ Abstracciones prematuras
- ❌ Patrones complejos de diseño

**Crear:**
- ✅ Un agente simple que llama a la IA
- ✅ Un system prompt robusto
- ✅ Validación de respuestas

### 3. Structured Outputs (JSON Schema)

```python
# IA debe retornar JSON estructurado, no texto libre
response_schema = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "confidence": {"type": "number"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"enum": ["add_product", "update_product", "delete_product", "update_field"]},
                    "target": {"type": "string"},
                    "data": {"type": "object"}
                }
            }
        },
        "requires_confirmation": {"type": "boolean"},
        "options": {"type": "array"}
    }
}
```

### 4. Observabilidad

```python
# Cada request debe ser trazable
logger.info("chat_message_received", extra={
    "rfx_id": rfx_id,
    "user_id": user_id,
    "message_length": len(message),
    "has_files": len(files) > 0,
    "correlation_id": correlation_id
})

# Cada respuesta de IA debe ser loggeada
logger.info("ai_response_generated", extra={
    "rfx_id": rfx_id,
    "confidence": response.confidence,
    "changes_count": len(response.changes),
    "requires_confirmation": response.requires_confirmation,
    "tokens_used": response.usage.total_tokens,
    "cost_usd": calculate_cost(response.usage),
    "correlation_id": correlation_id
})
```

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  Usuario escribe: "Agregar 20 refrescos"                    │
└────────────────────────┬────────────────────────────────────┘
                         │ POST /api/rfx/{id}/chat
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER (Flask/FastAPI)                │
│  - Validar request                                          │
│  - Extraer contexto del RFX                                 │
│  - Llamar al agente de IA                                   │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    CHAT AGENT SERVICE                       │
│  - Construir prompt con contexto                            │
│  - Llamar a OpenAI/Anthropic                                │
│  - Validar respuesta                                        │
│  - Generar cambios estructurados                            │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      IA (OpenAI)                  │
│  - Analizar intención del usuario                           │
│  - Generar respuesta en lenguaje natural                    │
│  - Generar cambios en formato JSON                          │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION LAYER                         │
│  - Validar cambios generados                                │
│  - Detectar conflictos                                      │
│  - Determinar si requiere confirmación                      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                        │
│  - Guardar mensaje en historial                             │
│  - Guardar cambios aplicados                                │
│  - Actualizar RFX en BD (si no requiere confirmación)       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
                    Response al Frontend
```

### Stack Tecnológico

```python
# Framework
FastAPI  # Recomendado (async, type hints, auto docs)
# o Flask (si ya lo usas)

# IA
OpenAI Python SDK  # GPT-4o, GPT-4o-mini
# o Anthropic SDK (Claude 3.5 Sonnet)

# Base de Datos
Supabase (PostgreSQL)  # Ya lo usas

# Validación
Pydantic v2  # Structured outputs

# Logging
structlog  # Logs estructurados
```

---

## 🔌 ENDPOINTS DE API

### 1. Enviar Mensaje al Chat

```python
POST /api/rfx/{rfx_id}/chat
```

**Request:**
```json
{
  "message": "Agregar 20 refrescos",
  "files": [],  // Opcional: archivos adjuntos
  "context": {
    "current_products": [
      {
        "id": "prod_1",
        "nombre": "Pasos salados variados",
        "cantidad": 50,
        "precio": 5.0,
        "unidad": "unidades"
      },
      {
        "id": "prod_2",
        "nombre": "Café y té",
        "cantidad": 20,
        "precio": 2.0,
        "unidad": "servicios"
      }
    ],
    "current_total": 290.0,
    "delivery_date": "2025-12-05",
    "delivery_location": "Oficina Central",
    "client_name": "Sofia Elena Camejo",
    "client_email": "sofia@example.com"
  }
}
```

**Response (Éxito - Sin Confirmación):**
```json
{
  "status": "success",
  "message": "✅ ¡Listo! He agregado:\n\n📦 Refrescos variados\n   20 unidades\n   $2.50 c/u\n\n💰 Total actualizado: $290 → $340\n\n¿Necesitas algo más?",
  "confidence": 0.95,
  "changes": [
    {
      "type": "add_product",
      "target": "new",
      "data": {
        "nombre": "Refrescos variados",
        "cantidad": 20,
        "precio": 2.50,
        "unidad": "unidades",
        "costo_unitario": 1.50
      },
      "description": "Agregado: Refrescos variados (20 unidades)"
    }
  ],
  "requires_confirmation": false,
  "metadata": {
    "tokens_used": 1250,
    "cost_usd": 0.0125,
    "processing_time_ms": 1850,
    "model_used": "gpt-4o-mini"
  }
}
```

**Response (Requiere Confirmación):**
```json
{
  "status": "success",
  "message": "⚠️ Encontré un producto similar:\n\nYa existe:\n• Pasos salados variados (50 unidades)\n\n¿Qué deseas hacer?",
  "confidence": 0.75,
  "changes": [],
  "requires_confirmation": true,
  "options": [
    {
      "value": "increase_quantity",
      "label": "Aumentar cantidad a 100",
      "emoji": "1️⃣",
      "context": {
        "product_id": "prod_1",
        "new_quantity": 100
      }
    },
    {
      "value": "add_new",
      "label": "Agregar como producto nuevo",
      "emoji": "2️⃣",
      "context": {
        "new_product": {
          "nombre": "Pasos salados",
          "cantidad": 50,
          "precio": 5.0
        }
      }
    },
    {
      "value": "cancel",
      "label": "Cancelar",
      "emoji": "3️⃣",
      "context": null
    }
  ],
  "metadata": {
    "tokens_used": 1100,
    "cost_usd": 0.011,
    "processing_time_ms": 1650,
    "model_used": "gpt-4o-mini"
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "No se pudo procesar el mensaje",
  "error_code": "AI_PROCESSING_ERROR",
  "message": "Lo siento, no pude entender tu solicitud. ¿Podrías reformularla?",
  "details": "La IA no pudo generar cambios válidos",
  "metadata": {
    "correlation_id": "req_abc123"
  }
}
```

**Implementación:**

```python
# routes/rfx_chat.py

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
from services.chat_agent import ChatAgent
from services.rfx_service import RFXService
from utils.logger import logger
import uuid

router = APIRouter(prefix="/api/rfx", tags=["chat"])

class ChatContext(BaseModel):
    current_products: List[dict]
    current_total: float
    delivery_date: str
    delivery_location: str
    client_name: str
    client_email: str

class ChatRequest(BaseModel):
    message: str
    files: Optional[List[str]] = []
    context: ChatContext

@router.post("/{rfx_id}/chat")
async def send_chat_message(
    rfx_id: str,
    request: ChatRequest,
    files: List[UploadFile] = File(None)
):
    """
    Procesa un mensaje del chat conversacional y retorna cambios a aplicar.
    
    Flujo:
    1. Validar que el RFX existe
    2. Procesar archivos adjuntos si los hay
    3. Llamar al agente de IA con contexto completo
    4. Validar respuesta de la IA
    5. Guardar en historial
    6. Retornar respuesta
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info("chat_message_received", extra={
        "rfx_id": rfx_id,
        "message_length": len(request.message),
        "has_files": len(files) > 0 if files else False,
        "correlation_id": correlation_id
    })
    
    try:
        # 1. Validar que el RFX existe
        rfx_service = RFXService()
        rfx = await rfx_service.get_rfx(rfx_id)
        
        if not rfx:
            raise HTTPException(status_code=404, detail="RFX no encontrado")
        
        # 2. Procesar archivos adjuntos si los hay
        file_contents = []
        if files:
            for file in files:
                content = await file.read()
                file_contents.append({
                    "name": file.filename,
                    "content": content,
                    "type": file.content_type
                })
        
        # 3. Llamar al agente de IA
        chat_agent = ChatAgent()
        response = await chat_agent.process_message(
            rfx_id=rfx_id,
            message=request.message,
            context=request.context.dict(),
            files=file_contents,
            correlation_id=correlation_id
        )
        
        # 4. Guardar en historial
        await rfx_service.save_chat_message(
            rfx_id=rfx_id,
            user_message=request.message,
            assistant_message=response.message,
            changes=response.changes,
            files=file_contents
        )
        
        logger.info("chat_message_processed", extra={
            "rfx_id": rfx_id,
            "confidence": response.confidence,
            "changes_count": len(response.changes),
            "requires_confirmation": response.requires_confirmation,
            "correlation_id": correlation_id
        })
        
        # 5. Retornar respuesta
        return {
            "status": "success",
            "message": response.message,
            "confidence": response.confidence,
            "changes": response.changes,
            "requires_confirmation": response.requires_confirmation,
            "options": response.options if response.requires_confirmation else [],
            "metadata": {
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
                "processing_time_ms": response.processing_time_ms,
                "model_used": response.model_used
            }
        }
        
    except Exception as e:
        logger.error("chat_message_error", extra={
            "rfx_id": rfx_id,
            "error": str(e),
            "correlation_id": correlation_id
        })
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": "Error al procesar el mensaje",
                "message": "Lo siento, ocurrió un error. Por favor, intenta de nuevo.",
                "correlation_id": correlation_id
            }
        )
```

---

### 2. Confirmar Opción

```python
POST /api/rfx/{rfx_id}/chat/confirm
```

**Request:**
```json
{
  "option_value": "increase_quantity",
  "context": {
    "product_id": "prod_1",
    "new_quantity": 100
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "✅ Perfecto! He actualizado:\n\n📦 Pasos salados variados\n   50 → 100 unidades\n\n💰 Total: $290 → $540",
  "changes": [
    {
      "type": "update_product",
      "target": "prod_1",
      "data": {
        "cantidad": 100
      },
      "description": "Actualizado: Pasos salados variados - cantidad 50 → 100"
    }
  ]
}
```

**Implementación:**

```python
# routes/rfx_chat.py

class ConfirmRequest(BaseModel):
    option_value: str
    context: dict

@router.post("/{rfx_id}/chat/confirm")
async def confirm_option(
    rfx_id: str,
    request: ConfirmRequest
):
    """
    Confirma una opción seleccionada por el usuario.
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info("chat_confirmation_received", extra={
        "rfx_id": rfx_id,
        "option_value": request.option_value,
        "correlation_id": correlation_id
    })
    
    try:
        chat_agent = ChatAgent()
        response = await chat_agent.process_confirmation(
            rfx_id=rfx_id,
            option_value=request.option_value,
            context=request.context,
            correlation_id=correlation_id
        )
        
        # Guardar en historial
        rfx_service = RFXService()
        await rfx_service.save_chat_message(
            rfx_id=rfx_id,
            user_message=f"Opción seleccionada: {request.option_value}",
            assistant_message=response.message,
            changes=response.changes
        )
        
        return {
            "status": "success",
            "message": response.message,
            "changes": response.changes
        }
        
    except Exception as e:
        logger.error("chat_confirmation_error", extra={
            "rfx_id": rfx_id,
            "error": str(e),
            "correlation_id": correlation_id
        })
        
        raise HTTPException(status_code=500, detail="Error al confirmar opción")
```

---

### 3. Obtener Historial de Chat

```python
GET /api/rfx/{rfx_id}/chat/history?limit=50&offset=0
```

**Response:**
```json
{
  "status": "success",
  "messages": [
    {
      "id": "msg_1",
      "role": "user",
      "content": "Agregar 20 refrescos",
      "timestamp": "2025-12-01T12:00:00Z",
      "files": []
    },
    {
      "id": "msg_2",
      "role": "assistant",
      "content": "✅ ¡Listo! He agregado...",
      "timestamp": "2025-12-01T12:00:02Z",
      "metadata": {
        "confidence": 0.95,
        "changes": [...],
        "tokens_used": 1250
      }
    }
  ],
  "total": 2,
  "has_more": false
}
```

**Implementación:**

```python
@router.get("/{rfx_id}/chat/history")
async def get_chat_history(
    rfx_id: str,
    limit: int = 50,
    offset: int = 0
):
    """
    Obtiene el historial de conversación de un RFX.
    """
    try:
        rfx_service = RFXService()
        messages = await rfx_service.get_chat_history(
            rfx_id=rfx_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "messages": messages,
            "total": len(messages),
            "has_more": len(messages) == limit
        }
        
    except Exception as e:
        logger.error("get_chat_history_error", extra={
            "rfx_id": rfx_id,
            "error": str(e)
        })
        
        raise HTTPException(status_code=500, detail="Error al obtener historial")
```

---

## 🤖 AGENTE DE IA

### Arquitectura del Agente

```python
# services/chat_agent.py

from openai import AsyncOpenAI
from typing import List, Dict, Optional
from pydantic import BaseModel
from prompts.chat_system_prompt import CHAT_SYSTEM_PROMPT
from utils.logger import logger
import time

class RFXChange(BaseModel):
    type: str  # "add_product" | "update_product" | "delete_product" | "update_field"
    target: str  # ID del producto o nombre del campo
    data: dict
    description: str

class ConfirmationOption(BaseModel):
    value: str
    label: str
    emoji: str
    context: Optional[dict]

class ChatResponse(BaseModel):
    message: str
    confidence: float
    changes: List[RFXChange]
    requires_confirmation: bool
    options: List[ConfirmationOption] = []
    tokens_used: int
    cost_usd: float
    processing_time_ms: int
    model_used: str

class ChatAgent:
    """
    Agente de IA para procesar mensajes del chat conversacional.
    
    Responsabilidades:
    - Construir prompt con contexto
    - Llamar a OpenAI con structured outputs
    - Validar respuesta
    - Generar cambios estructurados
    """
    
    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4o-mini"  # o "gpt-4o" para mayor precisión
        
    async def process_message(
        self,
        rfx_id: str,
        message: str,
        context: dict,
        files: List[dict] = [],
        correlation_id: str = ""
    ) -> ChatResponse:
        """
        Procesa un mensaje del usuario y genera cambios.
        """
        start_time = time.time()
        
        try:
            # 1. Construir prompt con contexto
            user_prompt = self._build_user_prompt(message, context, files)
            
            logger.info("ai_request_sent", extra={
                "rfx_id": rfx_id,
                "model": self.model,
                "correlation_id": correlation_id
            })
            
            # 2. Llamar a OpenAI con structured outputs
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "rfx_chat_response",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Respuesta en lenguaje natural para el usuario"
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "Nivel de confianza de 0.0 a 1.0"
                                },
                                "changes": {
                                    "type": "array",
                                    "description": "Lista de cambios a aplicar",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "enum": ["add_product", "update_product", "delete_product", "update_field"]
                                            },
                                            "target": {
                                                "type": "string",
                                                "description": "ID del producto o nombre del campo"
                                            },
                                            "data": {
                                                "type": "object",
                                                "description": "Datos del cambio"
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "Descripción legible del cambio"
                                            }
                                        },
                                        "required": ["type", "target", "data", "description"],
                                        "additionalProperties": False
                                    }
                                },
                                "requires_confirmation": {
                                    "type": "boolean",
                                    "description": "Si requiere confirmación del usuario"
                                },
                                "options": {
                                    "type": "array",
                                    "description": "Opciones si requiere confirmación",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "value": {"type": "string"},
                                            "label": {"type": "string"},
                                            "emoji": {"type": "string"},
                                            "context": {"type": "object"}
                                        },
                                        "required": ["value", "label", "emoji"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["message", "confidence", "changes", "requires_confirmation"],
                            "additionalProperties": False
                        }
                    }
                },
                temperature=0.3,  # Baja temperatura para respuestas consistentes
                max_tokens=2000
            )
            
            # 3. Parsear respuesta
            result = json.loads(response.choices[0].message.content)
            
            # 4. Calcular métricas
            processing_time_ms = int((time.time() - start_time) * 1000)
            tokens_used = response.usage.total_tokens
            cost_usd = self._calculate_cost(tokens_used)
            
            logger.info("ai_response_received", extra={
                "rfx_id": rfx_id,
                "confidence": result["confidence"],
                "changes_count": len(result["changes"]),
                "requires_confirmation": result["requires_confirmation"],
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "processing_time_ms": processing_time_ms,
                "correlation_id": correlation_id
            })
            
            # 5. Validar cambios
            validated_changes = self._validate_changes(result["changes"], context)
            
            # 6. Construir respuesta
            return ChatResponse(
                message=result["message"],
                confidence=result["confidence"],
                changes=[RFXChange(**change) for change in validated_changes],
                requires_confirmation=result["requires_confirmation"],
                options=[ConfirmationOption(**opt) for opt in result.get("options", [])],
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                processing_time_ms=processing_time_ms,
                model_used=self.model
            )
            
        except Exception as e:
            logger.error("ai_processing_error", extra={
                "rfx_id": rfx_id,
                "error": str(e),
                "correlation_id": correlation_id
            })
            
            # Retornar respuesta de error amigable
            return ChatResponse(
                message="Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?",
                confidence=0.0,
                changes=[],
                requires_confirmation=False,
                options=[],
                tokens_used=0,
                cost_usd=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_used=self.model
            )
    
    def _build_user_prompt(
        self,
        message: str,
        context: dict,
        files: List[dict]
    ) -> str:
        """
        Construye el prompt del usuario con contexto completo.
        """
        prompt = f"""# SOLICITUD DEL USUARIO

{message}

# CONTEXTO ACTUAL DEL RFX

## Productos Actuales:
"""
        
        for i, product in enumerate(context.get("current_products", []), 1):
            prompt += f"""
{i}. {product['nombre']}
   - ID: {product['id']}
   - Cantidad: {product['cantidad']} {product.get('unidad', 'unidades')}
   - Precio: ${product['precio']:.2f}
"""
        
        prompt += f"""
## Información del RFX:
- Total actual: ${context.get('current_total', 0):.2f}
- Fecha de entrega: {context.get('delivery_date', 'No especificada')}
- Lugar de entrega: {context.get('delivery_location', 'No especificado')}
- Cliente: {context.get('client_name', 'No especificado')}
- Email: {context.get('client_email', 'No especificado')}
"""
        
        if files:
            prompt += "\n## Archivos Adjuntos:\n"
            for file in files:
                prompt += f"- {file['name']} ({file['type']})\n"
        
        return prompt
    
    def _validate_changes(
        self,
        changes: List[dict],
        context: dict
    ) -> List[dict]:
        """
        Valida que los cambios generados sean válidos.
        """
        validated = []
        
        for change in changes:
            # Validar que el tipo sea válido
            if change["type"] not in ["add_product", "update_product", "delete_product", "update_field"]:
                logger.warning("invalid_change_type", extra={"change": change})
                continue
            
            # Validar que tenga los campos requeridos
            if not all(k in change for k in ["type", "target", "data", "description"]):
                logger.warning("missing_change_fields", extra={"change": change})
                continue
            
            # Validaciones específicas por tipo
            if change["type"] == "update_product":
                # Validar que el producto existe
                product_exists = any(
                    p["id"] == change["target"] 
                    for p in context.get("current_products", [])
                )
                if not product_exists:
                    logger.warning("product_not_found", extra={"change": change})
                    continue
            
            validated.append(change)
        
        return validated
    
    def _calculate_cost(self, tokens: int) -> float:
        """
        Calcula el costo de la llamada a la IA.
        """
        # Precios de gpt-4o-mini (ejemplo)
        # Input: $0.15 / 1M tokens
        # Output: $0.60 / 1M tokens
        # Asumimos 50/50 input/output
        cost_per_1m = (0.15 + 0.60) / 2
        return (tokens / 1_000_000) * cost_per_1m
    
    async def process_confirmation(
        self,
        rfx_id: str,
        option_value: str,
        context: dict,
        correlation_id: str = ""
    ) -> ChatResponse:
        """
        Procesa la confirmación de una opción seleccionada.
        """
        # Ejecutar la acción según la opción seleccionada
        if option_value == "increase_quantity":
            product_id = context["product_id"]
            new_quantity = context["new_quantity"]
            
            return ChatResponse(
                message=f"✅ Perfecto! He actualizado la cantidad.",
                confidence=1.0,
                changes=[
                    RFXChange(
                        type="update_product",
                        target=product_id,
                        data={"cantidad": new_quantity},
                        description=f"Cantidad actualizada a {new_quantity}"
                    )
                ],
                requires_confirmation=False,
                options=[],
                tokens_used=0,
                cost_usd=0.0,
                processing_time_ms=0,
                model_used=self.model
            )
        
        elif option_value == "add_new":
            new_product = context["new_product"]
            
            return ChatResponse(
                message=f"✅ He agregado el producto como nuevo.",
                confidence=1.0,
                changes=[
                    RFXChange(
                        type="add_product",
                        target="new",
                        data=new_product,
                        description=f"Agregado: {new_product['nombre']}"
                    )
                ],
                requires_confirmation=False,
                options=[],
                tokens_used=0,
                cost_usd=0.0,
                processing_time_ms=0,
                model_used=self.model
            )
        
        elif option_value == "cancel":
            return ChatResponse(
                message="Operación cancelada.",
                confidence=1.0,
                changes=[],
                requires_confirmation=False,
                options=[],
                tokens_used=0,
                cost_usd=0.0,
                processing_time_ms=0,
                model_used=self.model
            )
        
        else:
            raise ValueError(f"Opción no válida: {option_value}")
```

---

## 🎯 FILOSOFÍA: TODO LO DECIDE LA IA

### Principio Central

```
┌─────────────────────────────────────────────────────────────┐
│  BACKEND = EJECUTOR SIMPLE                                  │
│  IA = CEREBRO INTELIGENTE                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Backend NO tiene lógica de:                                │
│  ❌ Detección de duplicados                                 │
│  ❌ Validación de cantidades                                │
│  ❌ Cálculo de precios                                      │
│  ❌ Decisión de confirmaciones                              │
│  ❌ Parsing de intenciones                                  │
│                                                             │
│  Backend SOLO:                                              │
│  ✅ Recibe mensaje + contexto                               │
│  ✅ Llama a la IA                                           │
│  ✅ Valida formato JSON (no contenido)                      │
│  ✅ Retorna respuesta                                       │
│                                                             │
│  LA IA DECIDE:                                              │
│  🧠 Si hay duplicados → pide confirmación                   │
│  🧠 Si cantidad es rara → pide confirmación                 │
│  🧠 Si falta info → pide clarificación                      │
│  🧠 Qué precio asignar                                      │
│  🧠 Qué cambios generar                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Ventajas de Este Enfoque

1. **✅ Código Mínimo:** Backend es ~200 líneas, no 2000
2. **✅ Flexibilidad Total:** Agregar casos nuevos = actualizar prompt, no código
3. **✅ Mejora Continua:** Refinar IA es más fácil que refactorizar código
4. **✅ Mantenibilidad:** Un archivo de prompt vs múltiples servicios
5. **✅ Testing Simple:** Testear prompt con ejemplos vs testear lógica compleja

### Comparación: Enfoque Tradicional vs AI-First

**❌ Enfoque Tradicional (NO hacer):**
```python
# backend/services/rfx_updater.py (500+ líneas)

class RFXUpdater:
    def process_message(self, message, context):
        # Detectar intención manualmente
        if "agregar" in message.lower():
            return self._handle_add(message, context)
        elif "eliminar" in message.lower():
            return self._handle_delete(message, context)
        # ... 50 más if/elif
    
    def _handle_add(self, message, context):
        # Parsear producto manualmente
        product_name = self._extract_product_name(message)
        quantity = self._extract_quantity(message)
        
        # Detectar duplicados manualmente
        for existing in context['products']:
            similarity = self._calculate_similarity(product_name, existing['name'])
            if similarity > 0.8:
                return self._ask_confirmation(...)
        
        # ... 100 líneas más de lógica
    
    def _extract_product_name(self, message):
        # Regex complejo, NLP manual, etc.
        # ... 50 líneas
    
    # ... 10 métodos más
```

**✅ Enfoque AI-First (HACER):**
```python
# backend/services/chat_agent.py (100 líneas)

class ChatAgent:
    async def process_message(self, message, context):
        # 1. Construir prompt con contexto
        prompt = self._build_prompt(message, context)
        
        # 2. Llamar a IA (ella decide TODO)
        response = await openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMA}
        )
        
        # 3. Parsear y retornar (IA ya decidió todo)
        return json.loads(response.choices[0].message.content)
    
    def _build_prompt(self, message, context):
        # Simple: solo formatear contexto
        return f"Usuario: {message}\n\nContexto: {json.dumps(context)}"
```

**Diferencia:** 500 líneas de lógica compleja → 100 líneas simples

---

## 📝 SYSTEM PROMPT DESIGN

### Principios del System Prompt

1. **Exhaustivo:** Cubre TODOS los 20+ casos de uso documentados
2. **Con ejemplos:** Muestra casos reales con frecuencias
3. **Formato estructurado:** JSON schema estricto
4. **Manejo de ambigüedades:** Instrucciones claras sobre cuándo pedir confirmación
5. **Detección inteligente:** La IA detecta duplicados, errores, cantidades raras

### System Prompt Completo

```python
# prompts/chat_system_prompt.py

CHAT_SYSTEM_PROMPT = """Eres un asistente experto en actualización de RFX (Request for X) para servicios de catering.

# TU ROL

Ayudas a usuarios a actualizar RFX mediante lenguaje natural. Analizas sus solicitudes y generas cambios estructurados que el sistema puede aplicar automáticamente.

TÚ DECIDES TODO: detección de duplicados, validaciones, confirmaciones, precios, cantidades. El backend solo ejecuta lo que tú decides.

# CAPACIDADES COMPLETAS

Puedes realizar TODAS las siguientes acciones:

## 1. AGREGAR PRODUCTOS

### 1.1 Agregar Producto Simple (40% de casos)
- **Entrada:** "Agregar 20 refrescos", "Necesito 50 servilletas"
- **Acción:** Generar add_product con precio estimado
- **Importante:** Estimar precio razonable basado en productos similares

### 1.2 Agregar Múltiples Productos (15% de casos)
- **Entrada:** "Agregar: 20 refrescos, 30 jugos, 50 servilletas"
- **Acción:** Generar múltiples add_product en un solo response
- **Importante:** Procesar todos en una sola respuesta

### 1.3 Agregar desde Archivo SIN Duplicados (15% de casos)
- **Entrada:** Usuario adjunta PDF/imagen con productos nuevos
- **Acción:** Extraer productos y agregarlos todos
- **Importante:** Verificar que NO existan en el RFX actual

### 1.4 Agregar desde Archivo CON Duplicados (30% de casos) 🔥 CRÍTICO
- **Entrada:** Archivo con productos que YA existen + productos nuevos
- **Acción:** 
  1. Detectar productos duplicados (similitud >80%)
  2. Separar: duplicados vs nuevos
  3. Pedir confirmación mostrando ambas listas
  4. Ofrecer opciones claras
- **Ejemplo:**
  ```
  Archivo tiene: "Pasos salados (50)", "Café (20)", "Jugos (15)"
  RFX tiene: "Pasos salados variados (50)", "Café y té (20)"
  
  Respuesta:
  {
    "message": "⚠️ Encontré productos duplicados:\n\nDel archivo:\n• Pasos salados (50)\n• Café (20)\n\nYa existen:\n• Pasos salados variados (50)\n• Café y té (20)\n\nProductos nuevos:\n• Jugos (15)\n\n¿Qué hacer?",
    "requires_confirmation": true,
    "options": [
      {"value": "add_only_new", "label": "Solo agregar nuevos (Jugos)", "emoji": "1️⃣"},
      {"value": "add_all", "label": "Agregar todo como independientes", "emoji": "2️⃣"},
      {"value": "replace_existing", "label": "Reemplazar existentes con archivo", "emoji": "3️⃣"}
    ]
  }
  ```

### 1.5 Agregar con Especificaciones Detalladas (5% de casos)
- **Entrada:** "Agregar 50 pasos gourmet premium, $8.00 c/u"
- **Acción:** Respetar precio y descripción especificados por usuario

## 2. MODIFICAR PRODUCTOS/INFORMACIÓN

### 2.1 Modificar Cantidad - Aumentar (15% de casos)
- **Entrada:** "Aumentar pasos a 80", "Cambiar café a 30"
- **Acción:** update_product con nueva cantidad, recalcular precio total

### 2.2 Modificar Cantidad - Disminuir (5% de casos)
- **Entrada:** "Reducir café a 10"
- **Acción:** update_product con cantidad menor

### 2.3 Modificar Precio Unitario (10% de casos)
- **Entrada:** "Precio de pasos es $6.00 cada uno"
- **Acción:** update_product con nuevo precio, recalcular total

### 2.4 Modificar Nombre/Descripción (5% de casos)
- **Entrada:** "Cambiar 'Pasos salados' a 'Bocadillos gourmet'"
- **Acción:** update_product solo el nombre, mantener cantidad/precio

### 2.5 Modificar Información del Evento (15% de casos)
- **Entrada:** "Cambiar fecha al 15 dic", "Lugar: Salón Gardenia", "Cliente: María"
- **Acción:** update_field para delivery_date, delivery_location, client_name, etc.

## 3. ELIMINAR PRODUCTOS

### 3.1 Eliminar Producto Específico (10% de casos)
- **Entrada:** "Eliminar los refrescos", "Quitar café"
- **Acción:** delete_product
- **Confirmación:** Solo si >$100 o múltiples productos

### 3.2 Eliminar Múltiples (5% de casos)
- **Entrada:** "Eliminar café, refrescos y servilletas"
- **Acción:** Múltiples delete_product
- **Confirmación:** SIEMPRE pedir confirmación, mostrar total a restar

## 4. REEMPLAZAR

### 4.1 Reemplazar TODO el RFX (5% de casos)
- **Entrada:** "Cliente cambió todo, adjunto nueva solicitud"
- **Detección:** >70% productos diferentes + keywords ("reemplazar", "cambió todo")
- **Acción:** Pedir confirmación, luego delete_product de todos + add_product de nuevos

### 4.2 Reemplazar Producto Individual (5% de casos)
- **Entrada:** "Cambiar pasos por bocadillos gourmet"
- **Acción:** delete_product antiguo + add_product nuevo

## 5. CORREGIR ERRORES

### 5.1 Corregir Cantidad (8% de casos)
- **Entrada:** "Son 50 pasos, no 80", "Corregir café: 20 no 30"
- **Acción:** update_product, explicar corrección

### 5.2 Corregir Precio (8% de casos)
- **Entrada:** "Precio correcto es $5.00, no $6.00"
- **Acción:** update_product precio, recalcular

### 5.3 Corregir Nombre (3% de casos)
- **Entrada:** "Es 'Pasos salados', no 'Bocadillos'"
- **Acción:** update_product solo nombre

### 5.4 Corregir Info Evento (7% de casos)
- **Entrada:** "Fecha correcta es 12 dic, no 15"
- **Acción:** update_field

## 6. CONSULTAR (Sin Modificar)

### 6.1 Consultar Lista (5% de casos)
- **Entrada:** "¿Qué productos tiene?", "Muéstrame la lista"
- **Acción:** NO generar changes, solo responder con información

### 6.2 Consultar Info Específica (4% de casos)
- **Entrada:** "¿Cuál es el total?", "¿Cuándo es el evento?"
- **Acción:** Responder sin modificar nada

### 6.3 Consultar Precios (2% de casos)
- **Entrada:** "¿Cuánto cuesta cada paso?"
- **Acción:** Responder con precios actuales

## 7. CASOS ESPECIALES (Edge Cases)

### 7.1 Solicitud Ambigua
- **Entrada:** "Agregar más pasos" (sin cantidad)
- **Acción:** confidence < 0.7, pedir clarificación, NO generar cambios

### 7.2 Producto No en Catálogo
- **Entrada:** "Agregar canapés de salmón" (sin precio)
- **Acción:** Pedir precio o agregar sin precio

### 7.3 Cantidad Inusual
- **Entrada:** "Agregar 10,000 pasos"
- **Acción:** requires_confirmation = true, confirmar cantidad

### 7.4 Múltiples Operaciones en Un Mensaje
- **Entrada:** "Agregar refrescos, aumentar pasos a 80, eliminar café, cambiar fecha"
- **Acción:** Procesar TODAS en orden, generar múltiples changes

### 7.5 Instrucciones Contradictorias
- **Entrada:** "Agregar refrescos pero no los agregues"
- **Acción:** Detectar contradicción, pedir clarificación

# FORMATO DE RESPUESTA

SIEMPRE debes responder en formato JSON con esta estructura:

{
  "message": "Respuesta amigable en español para el usuario",
  "confidence": 0.95,  // 0.0 a 1.0
  "changes": [
    {
      "type": "add_product | update_product | delete_product | update_field",
      "target": "ID del producto o nombre del campo",
      "data": { /* datos específicos del cambio */ },
      "description": "Descripción legible del cambio"
    }
  ],
  "requires_confirmation": false,
  "options": []  // Solo si requires_confirmation es true
}

# REGLAS IMPORTANTES

## 1. Detección de Productos Similares

Si el usuario pide agregar un producto que ya existe o es muy similar:
- Establece `requires_confirmation: true`
- Ofrece opciones claras al usuario
- NO agregues el producto automáticamente

Ejemplo:
Usuario: "Agregar pasos salados"
Contexto: Ya existe "Pasos salados variados (50 unidades)"

Respuesta:
{
  "message": "⚠️ Encontré un producto similar:\n\nYa existe:\n• Pasos salados variados (50 unidades)\n\n¿Qué deseas hacer?",
  "confidence": 0.75,
  "changes": [],
  "requires_confirmation": true,
  "options": [
    {
      "value": "increase_quantity",
      "label": "Aumentar cantidad a 100",
      "emoji": "1️⃣",
      "context": { "product_id": "prod_1", "new_quantity": 100 }
    },
    {
      "value": "add_new",
      "label": "Agregar como producto nuevo",
      "emoji": "2️⃣",
      "context": { "new_product": { "nombre": "Pasos salados", "cantidad": 50, "precio": 5.0 } }
    },
    {
      "value": "cancel",
      "label": "Cancelar",
      "emoji": "3️⃣",
      "context": null
    }
  ]
}

## 2. Cálculo de Precios

Cuando agregues productos nuevos:
- Estima un precio razonable basado en productos similares
- Si no hay referencia, usa precios estándar de catering
- Indica en el mensaje que es un precio estimado

## 3. Unidades

Siempre especifica la unidad correcta:
- "unidades" para items contables (pasos, empanadas, refrescos)
- "servicios" para servicios (café, té)
- "kg" para peso
- "personas" para servicios por persona

## 4. Cambios Masivos

Si el cambio afecta a múltiples productos (>3):
- Establece `requires_confirmation: true`
- Lista todos los productos afectados
- Pide confirmación explícita

## 5. Solicitudes Ambiguas

Si la solicitud no es clara:
- Establece `confidence` < 0.7
- Pide clarificación en el mensaje
- NO generes cambios

Ejemplo:
Usuario: "Agregar más comida"

Respuesta:
{
  "message": "¿Podrías ser más específico? ¿Qué tipo de comida deseas agregar y en qué cantidad?",
  "confidence": 0.3,
  "changes": [],
  "requires_confirmation": false,
  "options": []
}

## 6. Fechas Relativas

Interpreta fechas relativas correctamente:
- "mañana" = fecha actual + 1 día
- "pasado mañana" = fecha actual + 2 días
- "próxima semana" = fecha actual + 7 días
- "hoy" = fecha actual

## 7. Tono de Respuesta

- Usa emojis apropiados: ✅ 📦 💰 ⚠️ ❌
- Sé conciso pero amigable
- Confirma siempre lo que hiciste
- Ofrece ayuda adicional al final

# EJEMPLOS DE CASOS DE USO

## Caso 1: Agregar Producto Simple

Usuario: "Agregar 20 refrescos"
Contexto: No hay refrescos en la lista

Respuesta:
{
  "message": "✅ ¡Listo! He agregado:\n\n📦 Refrescos variados\n   20 unidades\n   $2.50 c/u\n\n💰 Total actualizado: $290 → $340\n\n¿Necesitas algo más?",
  "confidence": 0.95,
  "changes": [
    {
      "type": "add_product",
      "target": "new",
      "data": {
        "nombre": "Refrescos variados",
        "cantidad": 20,
        "precio": 2.50,
        "unidad": "unidades",
        "costo_unitario": 1.50
      },
      "description": "Agregado: Refrescos variados (20 unidades)"
    }
  ],
  "requires_confirmation": false,
  "options": []
}

## Caso 2: Modificar Cantidad

Usuario: "Cambiar pasos salados a 100"
Contexto: Existe "Pasos salados variados" con ID "prod_1", cantidad actual 50

Respuesta:
{
  "message": "✅ Actualizado!\n\n📦 Pasos salados variados\n   50 → 100 unidades\n\n💰 Total: $290 → $540",
  "confidence": 0.98,
  "changes": [
    {
      "type": "update_product",
      "target": "prod_1",
      "data": {
        "cantidad": 100
      },
      "description": "Actualizado: Pasos salados variados - cantidad 50 → 100"
    }
  ],
  "requires_confirmation": false,
  "options": []
}

## Caso 3: Cambiar Fecha

Usuario: "Cambiar la fecha a mañana"
Contexto: Fecha actual es 2025-12-05

Respuesta:
{
  "message": "✅ Fecha actualizada!\n\n📅 Nueva fecha de entrega: 6 de diciembre de 2025",
  "confidence": 0.99,
  "changes": [
    {
      "type": "update_field",
      "target": "delivery_date",
      "data": {
        "oldValue": "2025-12-05",
        "newValue": "2025-12-06"
      },
      "description": "Fecha de entrega actualizada: 5 dic → 6 dic"
    }
  ],
  "requires_confirmation": false,
  "options": []
}

## Caso 4: Eliminar Producto

Usuario: "Eliminar el café"
Contexto: Existe "Café y té" con ID "prod_2"

Respuesta:
{
  "message": "✅ Producto eliminado!\n\n❌ Café y té (20 servicios)\n\n💰 Total: $290 → $250",
  "confidence": 0.95,
  "changes": [
    {
      "type": "delete_product",
      "target": "prod_2",
      "data": {},
      "description": "Eliminado: Café y té (20 servicios)"
    }
  ],
  "requires_confirmation": false,
  "options": []
}

## Caso 5: Agregar Múltiples Productos (15% de casos)

Usuario: "Agregar 20 refrescos, 30 jugos naturales y 50 servilletas"
Contexto: No existen estos productos

Respuesta:
{
  "message": "✅ ¡Perfecto! He agregado 3 productos:\n\n📦 Refrescos (20) - $50.00\n📦 Jugos naturales (30) - $90.00\n📦 Servilletas (50) - $25.00\n\n💰 Total actualizado: $290 → $455\n\n¿Algo más?",
  "confidence": 0.92,
  "changes": [
    {
      "type": "add_product",
      "target": "new",
      "data": {"nombre": "Refrescos", "cantidad": 20, "precio": 2.50, "unidad": "unidades"},
      "description": "Agregado: Refrescos (20 unidades)"
    },
    {
      "type": "add_product",
      "target": "new",
      "data": {"nombre": "Jugos naturales", "cantidad": 30, "precio": 3.00, "unidad": "unidades"},
      "description": "Agregado: Jugos naturales (30 unidades)"
    },
    {
      "type": "add_product",
      "target": "new",
      "data": {"nombre": "Servilletas", "cantidad": 50, "precio": 0.50, "unidad": "unidades"},
      "description": "Agregado: Servilletas (50 unidades)"
    }
  ],
  "requires_confirmation": false,
  "options": []
}

## Caso 6: Archivo CON Duplicados 🔥 CRÍTICO (30% de casos)

Usuario adjunta PDF con: "Pasos salados (50)", "Café (20)", "Jugos (15)"
Contexto: Ya existe "Pasos salados variados (50)", "Café y té (20)"

Respuesta:
{
  "message": "⚠️ Encontré productos duplicados en el archivo:\n\n**Del archivo:**\n• Pasos salados (50)\n• Café (20)\n\n**Ya existen en el RFX:**\n• Pasos salados variados (50)\n• Café y té (20)\n\n**Productos nuevos detectados:**\n• Jugos (15)\n\n¿Qué deseas hacer?",
  "confidence": 0.85,
  "changes": [],
  "requires_confirmation": true,
  "options": [
    {
      "value": "add_only_new",
      "label": "Solo agregar productos nuevos (Jugos)",
      "emoji": "1️⃣",
      "context": {
        "new_products": [
          {"nombre": "Jugos", "cantidad": 15, "precio": 3.00}
        ]
      }
    },
    {
      "value": "add_all_independent",
      "label": "Agregar todo como productos independientes",
      "emoji": "2️⃣",
      "context": {
        "all_products": [
          {"nombre": "Pasos salados", "cantidad": 50, "precio": 5.00},
          {"nombre": "Café", "cantidad": 20, "precio": 2.00},
          {"nombre": "Jugos", "cantidad": 15, "precio": 3.00}
        ]
      }
    },
    {
      "value": "replace_existing",
      "label": "Reemplazar productos existentes con versión del archivo",
      "emoji": "3️⃣",
      "context": {
        "to_delete": ["prod_1", "prod_2"],
        "to_add": [
          {"nombre": "Pasos salados", "cantidad": 50, "precio": 5.00},
          {"nombre": "Café", "cantidad": 20, "precio": 2.00},
          {"nombre": "Jugos", "cantidad": 15, "precio": 3.00}
        ]
      }
    },
    {
      "value": "cancel",
      "label": "Cancelar",
      "emoji": "❌",
      "context": null
    }
  ]
}

## Caso 7: Múltiples Operaciones en Un Mensaje

Usuario: "Agregar 20 refrescos, aumentar pasos a 80, eliminar café y cambiar la fecha al 15 de diciembre"
Contexto: Tiene "Pasos salados (50)", "Café y té (20)", fecha actual "2025-12-05"

Respuesta:
{
  "message": "✅ He aplicado 4 cambios:\n\n1. ➕ Agregado: Refrescos (20) - $50.00\n2. ✏️ Modificado: Pasos salados 50 → 80 unidades\n3. ➖ Eliminado: Café y té (20 servicios)\n4. 📅 Fecha actualizada: 5 dic → 15 dic 2025\n\n💰 Nuevo total: $450.00\n\n¿Necesitas algo más?",
  "confidence": 0.96,
  "changes": [
    {
      "type": "add_product",
      "target": "new",
      "data": {"nombre": "Refrescos", "cantidad": 20, "precio": 2.50, "unidad": "unidades"},
      "description": "Agregado: Refrescos (20 unidades)"
    },
    {
      "type": "update_product",
      "target": "prod_1",
      "data": {"cantidad": 80},
      "description": "Actualizado: Pasos salados - cantidad 50 → 80"
    },
    {
      "type": "delete_product",
      "target": "prod_2",
      "data": {},
      "description": "Eliminado: Café y té (20 servicios)"
    },
    {
      "type": "update_field",
      "target": "delivery_date",
      "data": {"oldValue": "2025-12-05", "newValue": "2025-12-15"},
      "description": "Fecha actualizada: 5 dic → 15 dic"
    }
  ],
  "requires_confirmation": false,
  "options": []
}

## Caso 8: Solicitud Ambigua

Usuario: "Agregar más pasos"
Contexto: Tiene "Pasos salados (50)"

Respuesta:
{
  "message": "❓ ¿Cuántos pasos salados deseas agregar?\n\nActualmente tienes: 50 unidades\n\nPor favor especifica:\n• Cantidad adicional (ej: '+20' = total 70)\n• Cantidad nueva total (ej: '70' = total 70)",
  "confidence": 0.4,
  "changes": [],
  "requires_confirmation": false,
  "options": []
}

## Caso 9: Reemplazar TODO el RFX

Usuario: "Cliente cambió todo, adjunto nueva solicitud"
Usuario adjunta PDF con productos completamente diferentes (>70% cambio)

Respuesta:
{
  "message": "⚠️ REEMPLAZO COMPLETO DETECTADO\n\nEl archivo tiene productos muy diferentes al RFX actual.\n\n**RFX actual:**\n• 3 productos\n• Total: $340.00\n\n**Nueva solicitud:**\n• 5 productos\n• Total estimado: $580.00\n\n¿Confirmas reemplazar completamente el RFX?",
  "confidence": 0.88,
  "changes": [],
  "requires_confirmation": true,
  "options": [
    {
      "value": "replace_all",
      "label": "Sí, reemplazar todo el RFX",
      "emoji": "⚠️",
      "context": {
        "delete_all": true,
        "new_products": [
          {"nombre": "Producto1", "cantidad": 10, "precio": 50.00},
          {"nombre": "Producto2", "cantidad": 20, "precio": 30.00}
        ]
      }
    },
    {
      "value": "add_to_existing",
      "label": "No, solo agregar productos nuevos",
      "emoji": "➕",
      "context": {"add_only": true}
    },
    {
      "value": "cancel",
      "label": "Cancelar",
      "emoji": "❌",
      "context": null
    }
  ]
}

# REGLAS CRÍTICAS DE DECISIÓN

## Cuándo Pedir Confirmación (requires_confirmation = true)

1. **Duplicados detectados** (similitud >80%)
2. **Eliminar múltiples productos** (>1 producto)
3. **Eliminar producto caro** (>$100)
4. **Cantidad inusual** (>1000 unidades o <1)
5. **Reemplazo completo** (>70% productos diferentes)
6. **Cambios masivos** (>5 productos afectados)

## Cuándo Pedir Clarificación (confidence < 0.7, no generar changes)

1. **Solicitud ambigua** (falta cantidad, producto, etc.)
2. **Instrucciones contradictorias**
3. **Producto no identificable**
4. **Información insuficiente**

## Cálculo de Precios

1. **Si hay productos similares:** Usar precio promedio de similares
2. **Si no hay referencia:** Usar precios estándar de catering:
   - Pasos/bocadillos: $4-6 c/u
   - Bebidas: $2-3 c/u
   - Servicios (café/té): $2-3 por servicio
   - Servilletas/decoración: $0.50-1 c/u
3. **Si usuario especifica precio:** SIEMPRE respetar el precio del usuario

## Detección de Similitud de Productos

Considera productos similares si:
- Nombres tienen >80% similitud (ej: "Pasos salados" vs "Pasos salados variados")
- Mismo tipo de producto con diferente descripción
- Mismo producto en singular/plural

# IMPORTANTE

- SIEMPRE responde en formato JSON válido
- NUNCA inventes IDs de productos, usa los del contexto
- SIEMPRE valida que los productos existan antes de modificarlos
- SIEMPRE calcula el nuevo total correctamente
- SIEMPRE usa emojis para mejor UX (✅ ➕ ✏️ ➖ 📅 💰 ⚠️ ❌ 📦)
- SIEMPRE sé específico en las descripciones de cambios
- SIEMPRE muestra antes → después en modificaciones
- SIEMPRE resume el impacto en el total
- TÚ DECIDES TODO: duplicados, validaciones, confirmaciones, precios
"""
```

---

## 💾 PERSISTENCIA DE DATOS

### Schema de Base de Datos

```sql
-- Tabla para historial de chat
CREATE TABLE rfx_chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Mensaje del usuario
    user_message TEXT NOT NULL,
    user_files JSONB DEFAULT '[]',  -- Array de archivos adjuntos
    
    -- Respuesta del asistente
    assistant_message TEXT NOT NULL,
    confidence DECIMAL(3,2),
    
    -- Cambios aplicados
    changes_applied JSONB DEFAULT '[]',  -- Array de RFXChange
    
    -- Metadata
    requires_confirmation BOOLEAN DEFAULT FALSE,
    tokens_used INTEGER,
    cost_usd DECIMAL(10,6),
    processing_time_ms INTEGER,
    model_used VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_rfx_chat_rfx_id (rfx_id),
    INDEX idx_rfx_chat_created_at (created_at DESC)
);

-- Tabla para cambios pendientes de confirmación
CREATE TABLE rfx_pending_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx(id) ON DELETE CASCADE,
    chat_message_id UUID NOT NULL REFERENCES rfx_chat_history(id),
    
    options JSONB NOT NULL,  -- Array de opciones
    
    confirmed_at TIMESTAMP WITH TIME ZONE,
    confirmed_option VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 hour',
    
    INDEX idx_pending_rfx_id (rfx_id),
    INDEX idx_pending_expires (expires_at)
);
```

### Servicio de Persistencia

```python
# services/rfx_service.py

from supabase import create_client, Client
from typing import List, Dict, Optional
from datetime import datetime
import os

class RFXService:
    """
    Servicio para interactuar con la base de datos de RFX.
    """
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    async def get_rfx(self, rfx_id: str) -> Optional[Dict]:
        """
        Obtiene un RFX por ID.
        """
        response = self.supabase.table("rfx").select("*").eq("id", rfx_id).single().execute()
        return response.data if response.data else None
    
    async def save_chat_message(
        self,
        rfx_id: str,
        user_message: str,
        assistant_message: str,
        changes: List[Dict],
        files: List[Dict] = [],
        confidence: float = 0.0,
        requires_confirmation: bool = False,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        processing_time_ms: int = 0,
        model_used: str = ""
    ) -> str:
        """
        Guarda un mensaje del chat en el historial.
        """
        data = {
            "rfx_id": rfx_id,
            "user_id": self._get_current_user_id(),  # Obtener del contexto de auth
            "user_message": user_message,
            "user_files": files,
            "assistant_message": assistant_message,
            "confidence": confidence,
            "changes_applied": changes,
            "requires_confirmation": requires_confirmation,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "processing_time_ms": processing_time_ms,
            "model_used": model_used
        }
        
        response = self.supabase.table("rfx_chat_history").insert(data).execute()
        return response.data[0]["id"]
    
    async def get_chat_history(
        self,
        rfx_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Obtiene el historial de chat de un RFX.
        """
        response = (
            self.supabase.table("rfx_chat_history")
            .select("*")
            .eq("rfx_id", rfx_id)
            .order("created_at", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )
        
        # Transformar a formato esperado por el frontend
        messages = []
        for row in response.data:
            # Mensaje del usuario
            messages.append({
                "id": f"{row['id']}_user",
                "role": "user",
                "content": row["user_message"],
                "timestamp": row["created_at"],
                "files": row.get("user_files", [])
            })
            
            # Mensaje del asistente
            messages.append({
                "id": f"{row['id']}_assistant",
                "role": "assistant",
                "content": row["assistant_message"],
                "timestamp": row["created_at"],
                "metadata": {
                    "confidence": float(row.get("confidence", 0)),
                    "changes": row.get("changes_applied", []),
                    "tokens_used": row.get("tokens_used", 0)
                }
            })
        
        return messages
    
    async def apply_changes(
        self,
        rfx_id: str,
        changes: List[Dict]
    ) -> bool:
        """
        Aplica cambios al RFX en la base de datos.
        """
        try:
            for change in changes:
                if change["type"] == "add_product":
                    await self._add_product(rfx_id, change["data"])
                
                elif change["type"] == "update_product":
                    await self._update_product(change["target"], change["data"])
                
                elif change["type"] == "delete_product":
                    await self._delete_product(change["target"])
                
                elif change["type"] == "update_field":
                    await self._update_rfx_field(rfx_id, change["target"], change["data"]["newValue"])
            
            return True
            
        except Exception as e:
            logger.error("apply_changes_error", extra={
                "rfx_id": rfx_id,
                "error": str(e)
            })
            return False
    
    async def _add_product(self, rfx_id: str, product_data: Dict):
        """Agrega un producto al RFX."""
        data = {
            "rfx_id": rfx_id,
            **product_data
        }
        self.supabase.table("rfx_products").insert(data).execute()
    
    async def _update_product(self, product_id: str, updates: Dict):
        """Actualiza un producto existente."""
        self.supabase.table("rfx_products").update(updates).eq("id", product_id).execute()
    
    async def _delete_product(self, product_id: str):
        """Elimina un producto."""
        self.supabase.table("rfx_products").delete().eq("id", product_id).execute()
    
    async def _update_rfx_field(self, rfx_id: str, field: str, value: any):
        """Actualiza un campo del RFX."""
        self.supabase.table("rfx").update({field: value}).eq("id", rfx_id).execute()
    
    def _get_current_user_id(self) -> str:
        """Obtiene el ID del usuario actual del contexto de autenticación."""
        # Implementar según tu sistema de auth
        # Por ejemplo, desde JWT token
        return "user_id_from_jwt"
```

---

## 💡 RECOMENDACIONES DE IMPLEMENTACIÓN KISS

### Principio: Menos Código, Más Inteligencia

```
┌─────────────────────────────────────────────────────────────┐
│  IMPLEMENTACIÓN MINIMALISTA                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  3 archivos principales:                                    │
│                                                             │
│  1. routes/rfx_chat.py           (~150 líneas)             │
│     - 3 endpoints simples                                   │
│     - Solo validación de entrada                            │
│     - Delega todo al agente                                 │
│                                                             │
│  2. services/chat_agent.py       (~200 líneas)             │
│     - Una función: process_message()                        │
│     - Construye prompt                                      │
│     - Llama a OpenAI                                        │
│     - Retorna respuesta                                     │
│                                                             │
│  3. prompts/chat_system_prompt.py (~500 líneas)            │
│     - TODO el conocimiento está aquí                        │
│     - Todos los casos de uso                                │
│     - Todas las reglas                                      │
│     - Todos los ejemplos                                    │
│                                                             │
│  Total: ~850 líneas vs 2000+ en enfoque tradicional        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ❌ NO Implementar (Evitar Complejidad)

1. **NO crear clases separadas por tipo de operación:**
   ```python
   # ❌ NO hacer esto
   class ProductAdder:
       def add_product(self, ...): ...
   
   class ProductUpdater:
       def update_product(self, ...): ...
   
   class ProductDeleter:
       def delete_product(self, ...): ...
   ```

2. **NO crear lógica de detección de duplicados:**
   ```python
   # ❌ NO hacer esto
   def detect_duplicates(new_product, existing_products):
       for existing in existing_products:
           similarity = calculate_similarity(...)
           if similarity > 0.8:
               return True
       return False
   ```

3. **NO crear parsers manuales:**
   ```python
   # ❌ NO hacer esto
   def extract_product_name(message):
       # Regex complejo
       pattern = r"agregar\s+(\d+)\s+(.+)"
       match = re.search(pattern, message)
       ...
   ```

4. **NO crear validadores complejos:**
   ```python
   # ❌ NO hacer esto
   def validate_quantity(quantity):
       if quantity < 1:
           raise ValueError("Cantidad debe ser > 0")
       if quantity > 10000:
           return ask_confirmation(...)
   ```

### ✅ SÍ Implementar (Simplicidad)

1. **Una sola función que llama a la IA:**
   ```python
   # ✅ Hacer esto
   async def process_message(message, context):
       prompt = build_prompt(message, context)
       response = await openai.create(prompt)
       return response
   ```

2. **Validación mínima (solo formato):**
   ```python
   # ✅ Hacer esto
   def validate_response(response):
       # Solo verificar que tenga los campos requeridos
       required = ["message", "confidence", "changes"]
       return all(field in response for field in required)
   ```

3. **Delegar decisiones a la IA:**
   ```python
   # ✅ La IA decide si hay duplicados
   # ✅ La IA decide si pedir confirmación
   # ✅ La IA decide qué precio asignar
   # Backend solo ejecuta lo que la IA decide
   ```

### Estructura de Archivos Recomendada

```
backend/
├── routes/
│   └── rfx_chat.py                    # 150 líneas - 3 endpoints
│
├── services/
│   ├── chat_agent.py                  # 200 líneas - Agente de IA
│   └── rfx_service.py                 # 300 líneas - Persistencia (ya existe)
│
├── prompts/
│   └── chat_system_prompt.py          # 500 líneas - TODO el conocimiento
│
└── models/
    └── chat_models.py                 # 100 líneas - Pydantic models

Total: ~1250 líneas (vs 3000+ en enfoque tradicional)
```

### Flujo de Implementación Recomendado

**Semana 1: MVP Básico (Top 3 casos - 70% de uso)**
```
Día 1-2: Setup + System Prompt
- [ ] Crear archivos base
- [ ] Escribir system prompt con casos básicos
- [ ] Testing manual del prompt en ChatGPT

Día 3-4: Agente + Endpoint
- [ ] Implementar ChatAgent.process_message()
- [ ] Implementar POST /api/rfx/{id}/chat
- [ ] Testing con Postman

Día 5: Integración
- [ ] Conectar con frontend
- [ ] Testing E2E de casos básicos
- [ ] Ajustar prompt según resultados
```

**Semana 2: Casos Avanzados (30% restante)**
```
Día 1-2: Archivos + Duplicados
- [ ] Agregar procesamiento de archivos
- [ ] Mejorar prompt para detección de duplicados
- [ ] Testing con PDFs reales

Día 3-4: Confirmaciones + Historial
- [ ] Implementar endpoint de confirmación
- [ ] Implementar endpoint de historial
- [ ] Testing de flujo completo

Día 5: Refinamiento
- [ ] Ajustar prompt con casos edge
- [ ] Optimizar respuestas
- [ ] Testing de todos los casos
```

### Métricas de Éxito

**Código:**
- ✅ Backend < 1500 líneas totales
- ✅ Función principal < 50 líneas
- ✅ Sin if/else por tipo de operación
- ✅ Sin lógica de parsing manual

**Funcionalidad:**
- ✅ Cubre 20+ casos de uso
- ✅ Detección de duplicados funciona
- ✅ Confirmaciones apropiadas
- ✅ Precios razonables

**Performance:**
- ✅ Respuesta < 3 segundos (95th percentile)
- ✅ Costo < $0.02 por mensaje
- ✅ Accuracy > 90% en casos comunes

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Setup Básico (1 día)
- [ ] Crear estructura de carpetas
- [ ] Instalar dependencias: `openai`, `pydantic`, `fastapi`
- [ ] Configurar `OPENAI_API_KEY` en `.env`
- [ ] Crear schema de BD (rfx_chat_history)

### Fase 2: System Prompt (1 día)
- [ ] Copiar system prompt completo de esta documentación
- [ ] Crear archivo `prompts/chat_system_prompt.py`
- [ ] Testing manual en ChatGPT con ejemplos
- [ ] Ajustar según resultados

### Fase 3: Agente de IA (1 día)
- [ ] Implementar `ChatAgent` class (~200 líneas)
- [ ] Implementar `process_message()` con structured outputs
- [ ] Implementar `_build_prompt()` para formatear contexto
- [ ] Testing unitario con casos básicos

### Fase 4: Endpoint Principal (1 día)
- [ ] Implementar POST `/api/rfx/{id}/chat`
- [ ] Validación de request (Pydantic)
- [ ] Llamar a ChatAgent
- [ ] Guardar en historial
- [ ] Testing con Postman

### Fase 5: Endpoints Secundarios (1 día)
- [ ] Implementar POST `/api/rfx/{id}/chat/confirm`
- [ ] Implementar GET `/api/rfx/{id}/chat/history`
- [ ] Testing de flujo completo

### Fase 6: Procesamiento de Archivos (2 días)
- [ ] Integrar con extractor de PDFs existente
- [ ] Pasar contenido extraído a la IA
- [ ] Testing con archivos reales

### Fase 7: Refinamiento (2 días)
- [ ] Testing de todos los 20+ casos de uso
- [ ] Ajustar prompt según errores
- [ ] Optimizar costos (usar gpt-4o-mini)
- [ ] Logging y métricas

### Fase 8: Integración Frontend (1 día)
- [ ] Testing E2E con frontend
- [ ] Ajustes finales de UX
- [ ] Deploy a staging

**Total estimado: 10 días de desarrollo**

---

## 🚀 PRÓXIMOS PASOS

### Inmediato (Hoy)
1. ✅ Revisar esta documentación completa
2. ✅ Validar que cubre todos los casos de uso
3. ✅ Confirmar enfoque AI-First

### Corto Plazo (Esta Semana)
1. Crear estructura de archivos
2. Implementar system prompt
3. Implementar agente básico
4. Testing de casos top 3

### Mediano Plazo (Próximas 2 Semanas)
1. Implementar todos los endpoints
2. Procesamiento de archivos
3. Testing exhaustivo
4. Integración con frontend

### Largo Plazo (Mes 1)
1. Monitoreo en producción
2. Refinamiento del prompt basado en uso real
3. Optimización de costos
4. Mejoras de UX

---

## 📊 RESUMEN EJECUTIVO

### Lo Que Hace Esta Implementación Diferente

**Enfoque Tradicional:**
- 2000+ líneas de código
- 10+ clases y servicios
- Lógica compleja de parsing
- Difícil de mantener y extender
- Testing complejo

**Nuestro Enfoque AI-First:**
- ~1250 líneas de código (-40%)
- 3 archivos principales
- IA decide TODO
- Fácil de mantener (solo actualizar prompt)
- Testing simple (ejemplos en prompt)

### Cobertura de Casos de Uso

✅ **20+ casos documentados cubiertos al 100%**
- Agregar productos (simple, múltiples, con archivos)
- Modificar (cantidad, precio, nombre, info evento)
- Eliminar (simple, múltiples)
- Reemplazar (individual, completo)
- Corregir errores
- Consultar información
- Edge cases (ambigüedades, duplicados, etc.)

### Ventajas Clave

1. **🚀 Rápido de Implementar:** 10 días vs 30+ días
2. **💰 Bajo Costo de Mantenimiento:** Actualizar prompt vs refactorizar código
3. **🧠 Inteligente:** IA maneja casos no previstos
4. **📈 Escalable:** Agregar casos = agregar al prompt
5. **🔍 Observable:** Logs estructurados + métricas de IA

---

**¿Listo para comenzar la implementación?** 🎯

**Siguiente paso:** Crear estructura de archivos y copiar system prompt
