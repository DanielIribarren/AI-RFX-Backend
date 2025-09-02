# 🚀 **GUÍA COMPLETA DE INTEGRACIÓN FRONTEND - V2.2**

## 📋 **RESUMEN EJECUTIVO**

**Sistema:** RFX Automation Platform V2.2  
**Backend:** Flask con arquitectura modular  
**Base de Datos:** Supabase (PostgreSQL) con sistema de pricing normalizado  
**Nuevas Funcionalidades:** Configuración independiente de coordinación y costo por persona

---

## 🏗️ **ARQUITECTURA DEL SISTEMA**

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                      │
├─────────────────────────────────────────────────────────────┤
│                     API GATEWAY                            │
│                 (Flask + CORS)                             │
├─────────────────────────────────────────────────────────────┤
│              BACKEND SERVICES V2.2                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │   RFX   │ │Proposal │ │Download │ │  PRICING V2.2   │   │
│  │Service  │ │Service  │ │Service  │ │   (NUEVO)       │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│              BASE DE DATOS V2.2                            │
│  ┌─────────┐ ┌─────────────────────────────────────────┐   │
│  │RFX Core │ │         PRICING TABLES                  │   │
│  │ Tables  │ │ • rfx_pricing_configurations           │   │
│  │         │ │ • coordination_configurations          │   │
│  │         │ │ • cost_per_person_configurations       │   │
│  │         │ │ • tax_configurations                   │   │
│  └─────────┘ └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌐 **ENDPOINTS COMPLETOS POR CATEGORÍA**

### **🏥 HEALTH & STATUS**

```typescript
// Verificación básica del sistema
GET /health
Response: { status: "ok", timestamp: "2024-..." }

// Verificación detallada con dependencias
GET /health/detailed
Response: {
  status: "ok",
  database: "connected",
  services: {...}
}
```

---

### **💰 PRICING ENDPOINTS (NUEVOS V2.2)**

#### **📋 Obtener Configuración de Pricing**

```typescript
GET /api/pricing/config/{rfx_id}

Response: {
  status: "success",
  data: {
    rfx_id: string,
    coordination_enabled: boolean,
    coordination_rate: number,
    cost_per_person_enabled: boolean,
    headcount: number | null,
    taxes_enabled: boolean,
    tax_rate: number | null,
    tax_type: string | null,
    has_configuration: boolean,
    last_updated: string | null,
    enabled_configs: string[]
  }
}
```

#### **⚙️ Actualizar Configuración de Pricing**

```typescript
PUT /api/pricing/config/{rfx_id}

Body: {
  coordination: {
    enabled: boolean,
    rate: number,        // 0.18 = 18%
    type: "basic" | "standard" | "premium" | "custom",
    description?: string
  },
  cost_per_person: {
    enabled: boolean,
    headcount: number,
    calculation_base: "subtotal" | "subtotal_with_coordination" | "final_total"
  },
  taxes: {
    enabled: boolean,
    rate: number,        // 0.16 = 16%
    name: string        // "IVA"
  }
}

Response: {
  status: "success",
  message: "Configuration updated successfully",
  data: { configuration_id: string }
}
```

#### **🧮 Calcular Pricing Dinámico**

```typescript
POST /api/pricing/calculate/{rfx_id}

Body: {
  subtotal: number
}

Response: {
  status: "success",
  data: {
    subtotal: number,
    coordination_enabled: boolean,
    coordination_amount: number,
    cost_per_person_enabled: boolean,
    headcount: number,
    cost_per_person: number,
    taxes_enabled: boolean,
    tax_amount: number,
    total_before_tax: number,
    final_total: number
  }
}
```

#### **📊 Resumen de Pricing**

```typescript
GET /api/pricing/summary/{rfx_id}

Response: {
  status: "success",
  data: {
    configuration_name: string,
    coordination: { enabled: boolean, rate: number, amount: number },
    cost_per_person: { enabled: boolean, headcount: number, cost: number },
    taxes: { enabled: boolean, rate: number, amount: number },
    totals: {
      subtotal: number,
      total_before_tax: number,
      final_total: number
    }
  }
}
```

#### **⚡ Configuración Rápida**

```typescript
POST /api/pricing/quick-config/{rfx_id}

Body: {
  preset_type: "catering_basic" | "catering_premium" | "eventos_corporativos" | "custom",
  headcount?: number
}

Response: {
  status: "success",
  message: "Quick configuration applied",
  data: { applied_preset: string }
}
```

#### **🎯 Presets Disponibles**

```typescript
GET /api/pricing/presets

Response: {
  status: "success",
  data: [
    {
      id: "catering_basic",
      name: "Catering Básico",
      coordination_rate: 0.15,
      includes_coordination: true,
      includes_cost_per_person: true,
      description: "Configuración estándar para catering básico"
    },
    // ... más presets
  ]
}
```

#### **✅ Validar Configuración**

```typescript
POST /api/pricing/validate-config

Body: {
  coordination_rate: number,
  headcount: number,
  tax_rate: number
}

Response: {
  status: "success",
  valid: boolean,
  errors: string[] | null
}
```

#### **🔢 Calcular desde RFX Existente**

```typescript
GET /api/pricing/calculate-from-rfx/{rfx_id}

Response: {
  status: "success",
  data: {
    // Mismo formato que POST /calculate pero usando datos del RFX
    subtotal: number,
    coordination_amount: number,
    final_total: number,
    cost_per_person: number
  }
}
```

---

### **📋 RFX MANAGEMENT**

#### **📄 Procesar RFX**

```typescript
POST /api/rfx/process

Body: FormData {
  files?: File[],                    // Archivos PDF/texto
  contenido_extraido?: string,       // Texto directo
  tipo_rfx?: "catering" | "logistica" | "tecnologia",
  email?: string,
  telefono?: string,
  empresa?: string,
  nombre_contacto?: string
}

Response: {
  status: "success",
  data: {
    rfx_id: string,
    processed_content: string,
    extracted_info: {
      productos: Array<{
        producto: string,
        cantidad: number,
        precio_unitario_estimado: number,
        descripcion: string
      }>,
      evento_info: {
        fecha: string,
        ubicacion: string,
        personas: number
      },
      empresa_info: {
        nombre: string,
        contacto: string,
        email: string
      }
    },
    pricing_suggestion: {
      coordination_recommended: boolean,
      cost_per_person_recommended: boolean,
      estimated_headcount: number
    }
  }
}
```

#### **📚 Historial de RFX**

```typescript
GET /api/rfx/history?page=1&limit=10&status=all

Response: {
  status: "success",
  data: {
    rfx_items: Array<{
      id: string,
      title: string,
      status: "in_progress" | "completed" | "cancelled",
      created_at: string,
      company_name: string,
      total_cost: number,
      has_pricing_config: boolean
    }>,
    pagination: {
      page: number,
      limit: number,
      total: number,
      pages: number
    }
  }
}
```

#### **🔍 Obtener RFX Específico**

```typescript
GET /api/rfx/{rfx_id}

Response: {
  status: "success",
  data: {
    id: string,
    title: string,
    description: string,
    status: string,
    company_info: {
      name: string,
      email: string,
      phone: string
    },
    productos: Array<{
      id: string,
      producto: string,
      cantidad: number,
      precio_unitario_estimado: number,
      total_estimado: number
    }>,
    evento_info: {
      fecha: string,
      ubicacion: string,
      personas: number
    },
    pricing_config: {
      has_config: boolean,
      coordination_enabled: boolean,
      cost_per_person_enabled: boolean
    },
    created_at: string,
    updated_at: string
  }
}
```

#### **✅ Finalizar RFX**

```typescript
POST /api/rfx/{rfx_id}/finalize

Body: {
  final_notes?: string,
  approved_by?: string
}

Response: {
  status: "success",
  message: "RFX finalized successfully"
}
```

#### **📝 Actualizar Datos de RFX**

```typescript
PUT /api/rfx/{rfx_id}/data

Body: {
  title?: string,
  description?: string,
  company_info?: {
    name: string,
    email: string,
    phone: string
  },
  evento_info?: {
    fecha: string,
    ubicacion: string,
    personas: number
  }
}

Response: {
  status: "success",
  message: "RFX updated successfully"
}
```

#### **💰 Actualizar Costos de Productos**

```typescript
PUT /api/rfx/{rfx_id}/products/costs

Body: {
  productos: Array<{
    id: string,
    precio_unitario_estimado: number
  }>
}

Response: {
  status: "success",
  message: "Product costs updated successfully",
  data: {
    updated_count: number,
    total_estimated_cost: number
  }
}
```

#### **📦 Actualizar Producto Específico**

```typescript
PUT /api/rfx/{rfx_id}/products/{product_id}

Body: {
  producto?: string,
  cantidad?: number,
  precio_unitario_estimado?: number,
  descripcion?: string
}

Response: {
  status: "success",
  message: "Product updated successfully"
}
```

#### **🔥 RFX Recientes**

```typescript
GET /api/rfx/recent?limit=5

Response: {
  status: "success",
  data: Array<{
    id: string,
    title: string,
    created_at: string,
    status: string,
    total_cost: number
  }>
}
```

---

### **📄 PROPOSALS**

#### **🎯 Generar Propuesta**

```typescript
POST /api/proposals/generate

Body: {
  rfx_id: string,
  proposal_type?: "standard" | "premium",
  custom_template?: string,
  include_pricing_breakdown?: boolean
}

Response: {
  status: "success",
  data: {
    proposal_id: string,
    html_content: string,
    total_cost: number,
    pricing_breakdown: {
      subtotal: number,
      coordination_amount: number,
      tax_amount: number,
      final_total: number,
      cost_per_person?: number
    },
    generated_at: string
  }
}
```

#### **📄 Obtener Propuesta**

```typescript
GET /api/proposals/{proposal_id}

Response: {
  status: "success",
  data: {
    id: string,
    rfx_id: string,
    html_content: string,
    total_cost: number,
    status: string,
    generated_at: string,
    updated_at: string
  }
}
```

#### **📋 Propuestas por RFX**

```typescript
GET /api/proposals/rfx/{rfx_id}/proposals

Response: {
  status: "success",
  data: Array<{
    id: string,
    title: string,
    total_cost: number,
    status: string,
    generated_at: string
  }>
}
```

---

### **📥 DOWNLOADS**

#### **📄 Descargar Documento**

```typescript
GET /api/download/{document_id}

Response: Binary file (PDF/HTML)
Headers: {
  "Content-Type": "application/pdf" | "text/html",
  "Content-Disposition": "attachment; filename=documento.pdf"
}
```

#### **🔄 HTML a PDF**

```typescript
POST /api/download/html-to-pdf

Body: {
  html_content: string,
  filename?: string,
  options?: {
    format: "A4" | "Letter",
    orientation: "portrait" | "landscape",
    margin: { top: string, bottom: string, left: string, right: string }
  }
}

Response: Binary PDF file
```

#### **🧪 Test de Capacidades PDF**

```typescript
GET /api/download/test-pdf-capabilities

Response: {
  status: "success",
  data: {
    pdf_generation: boolean,
    html_parsing: boolean,
    file_conversion: boolean
  }
}
```

---

## 🔗 **INTEGRACIÓN FRONTEND**

### **📦 Configuración Base**

```typescript
// api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";

class RFXApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  // Configuración de headers por defecto
  private getHeaders(): HeadersInit {
    return {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
  }

  // Método genérico para hacer requests
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const response = await fetch(url, {
      headers: this.getHeaders(),
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} - ${response.statusText}`);
    }

    return response.json();
  }

  // Métodos específicos para cada endpoint...
}
```

### **💰 Cliente de Pricing**

```typescript
// pricing-client.ts
interface PricingConfig {
  coordination: {
    enabled: boolean;
    rate: number;
    type: "basic" | "standard" | "premium" | "custom";
    description?: string;
  };
  cost_per_person: {
    enabled: boolean;
    headcount: number;
    calculation_base: "subtotal" | "subtotal_with_coordination" | "final_total";
  };
  taxes: {
    enabled: boolean;
    rate: number;
    name: string;
  };
}

class PricingApiClient extends RFXApiClient {
  // Obtener configuración
  async getPricingConfig(rfxId: string) {
    return this.request<{ status: string; data: any }>(
      `/api/pricing/config/${rfxId}`
    );
  }

  // Actualizar configuración
  async updatePricingConfig(rfxId: string, config: PricingConfig) {
    return this.request(`/api/pricing/config/${rfxId}`, {
      method: "PUT",
      body: JSON.stringify(config),
    });
  }

  // Calcular pricing
  async calculatePricing(rfxId: string, subtotal: number) {
    return this.request(`/api/pricing/calculate/${rfxId}`, {
      method: "POST",
      body: JSON.stringify({ subtotal }),
    });
  }

  // Configuración rápida
  async quickConfig(rfxId: string, presetType: string, headcount?: number) {
    return this.request(`/api/pricing/quick-config/${rfxId}`, {
      method: "POST",
      body: JSON.stringify({ preset_type: presetType, headcount }),
    });
  }
}
```

### **🎯 Hooks de React**

```typescript
// hooks/use-pricing.ts
import { useState, useEffect } from "react";
import { PricingApiClient } from "@/lib/pricing-client";

export function usePricing(rfxId: string) {
  const [config, setConfig] = useState(null);
  const [calculation, setCalculation] = useState(null);
  const [loading, setLoading] = useState(false);

  const api = new PricingApiClient();

  const loadConfig = async () => {
    setLoading(true);
    try {
      const result = await api.getPricingConfig(rfxId);
      setConfig(result.data);
    } catch (error) {
      console.error("Error loading pricing config:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = async (newConfig: PricingConfig) => {
    setLoading(true);
    try {
      await api.updatePricingConfig(rfxId, newConfig);
      await loadConfig(); // Recargar configuración
    } catch (error) {
      console.error("Error updating config:", error);
    } finally {
      setLoading(false);
    }
  };

  const calculate = async (subtotal: number) => {
    try {
      const result = await api.calculatePricing(rfxId, subtotal);
      setCalculation(result.data);
      return result.data;
    } catch (error) {
      console.error("Error calculating pricing:", error);
    }
  };

  useEffect(() => {
    if (rfxId) {
      loadConfig();
    }
  }, [rfxId]);

  return {
    config,
    calculation,
    loading,
    updateConfig,
    calculate,
    refreshConfig: loadConfig,
  };
}
```

### **🎨 Componente de Configuración de Pricing**

```typescript
// components/pricing-config.tsx
import { usePricing } from "@/hooks/use-pricing";

interface PricingConfigProps {
  rfxId: string;
  onConfigUpdate?: (config: any) => void;
}

export function PricingConfig({ rfxId, onConfigUpdate }: PricingConfigProps) {
  const { config, loading, updateConfig, calculate } = usePricing(rfxId);
  const [localConfig, setLocalConfig] = useState(config);

  const handleSave = async () => {
    await updateConfig(localConfig);
    onConfigUpdate?.(localConfig);
  };

  const handleCalculate = async () => {
    const subtotal = 10000; // Obtener del contexto
    const result = await calculate(subtotal);
    console.log("Calculation result:", result);
  };

  if (loading) return <div>Cargando configuración...</div>;

  return (
    <div className="pricing-config">
      {/* Coordinación */}
      <div className="config-section">
        <h3>Coordinación y Logística</h3>
        <label>
          <input
            type="checkbox"
            checked={localConfig?.coordination_enabled}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                coordination_enabled: e.target.checked,
              })
            }
          />
          Incluir coordinación
        </label>

        {localConfig?.coordination_enabled && (
          <input
            type="number"
            placeholder="Tasa (%)"
            value={localConfig.coordination_rate * 100}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                coordination_rate: Number(e.target.value) / 100,
              })
            }
          />
        )}
      </div>

      {/* Costo por persona */}
      <div className="config-section">
        <h3>Costo por Persona</h3>
        <label>
          <input
            type="checkbox"
            checked={localConfig?.cost_per_person_enabled}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                cost_per_person_enabled: e.target.checked,
              })
            }
          />
          Mostrar costo por persona
        </label>

        {localConfig?.cost_per_person_enabled && (
          <input
            type="number"
            placeholder="Número de personas"
            value={localConfig.headcount}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                headcount: Number(e.target.value),
              })
            }
          />
        )}
      </div>

      <div className="actions">
        <button onClick={handleSave}>Guardar Configuración</button>
        <button onClick={handleCalculate}>Calcular Precio</button>
      </div>
    </div>
  );
}
```

---

## 🔄 **FLUJOS DE TRABAJO RECOMENDADOS**

### **📋 Flujo: Crear RFX con Pricing**

```typescript
async function createRFXWithPricing(files: File[], headcount: number) {
  // 1. Procesar RFX
  const rfxResult = await api.processRFX(files);
  const rfxId = rfxResult.data.rfx_id;

  // 2. Configurar pricing
  await api.updatePricingConfig(rfxId, {
    coordination: { enabled: true, rate: 0.18, type: "standard" },
    cost_per_person: {
      enabled: true,
      headcount,
      calculation_base: "final_total",
    },
    taxes: { enabled: true, rate: 0.16, name: "IVA" },
  });

  // 3. Calcular precios
  const subtotal = rfxResult.data.extracted_info.productos.reduce(
    (sum, p) => sum + p.cantidad * p.precio_unitario_estimado,
    0
  );

  const calculation = await api.calculatePricing(rfxId, subtotal);

  // 4. Generar propuesta
  const proposal = await api.generateProposal({
    rfx_id: rfxId,
    include_pricing_breakdown: true,
  });

  return { rfxId, calculation, proposal };
}
```

### **💰 Flujo: Actualización Dinámica de Precios**

```typescript
function PricingCalculator({ rfxId, products }) {
  const { calculate } = usePricing(rfxId);
  const [results, setResults] = useState(null);

  const updatePricing = useCallback(
    debounce(async (newProducts) => {
      const subtotal = newProducts.reduce(
        (sum, p) => sum + p.quantity * p.unit_price,
        0
      );

      const calculation = await calculate(subtotal);
      setResults(calculation);
    }, 500),
    [calculate]
  );

  useEffect(() => {
    updatePricing(products);
  }, [products, updatePricing]);

  return (
    <div>
      {results && (
        <div className="pricing-summary">
          <div>Subtotal: ${results.subtotal}</div>
          <div>Coordinación: ${results.coordination_amount}</div>
          <div>Impuestos: ${results.tax_amount}</div>
          <div>Total: ${results.final_total}</div>
          {results.cost_per_person_enabled && (
            <div>Por persona: ${results.cost_per_person}</div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 🎯 **CASOS DE USO ESPECÍFICOS**

### **🎪 Caso: Evento Corporativo**

```typescript
// Configuración típica para eventos corporativos
const corporateEventConfig = {
  coordination: { enabled: true, rate: 0.2, type: "premium" },
  cost_per_person: {
    enabled: true,
    headcount: 150,
    calculation_base: "final_total",
  },
  taxes: { enabled: true, rate: 0.16, name: "IVA" },
};
```

### **🍽️ Caso: Catering Básico**

```typescript
// Configuración para catering básico
const basicCateringConfig = {
  coordination: { enabled: true, rate: 0.15, type: "standard" },
  cost_per_person: {
    enabled: true,
    headcount: 50,
    calculation_base: "subtotal_with_coordination",
  },
  taxes: { enabled: true, rate: 0.16, name: "IVA" },
};
```

### **🏢 Caso: Solo Productos**

```typescript
// Sin coordinación ni costo por persona
const productsOnlyConfig = {
  coordination: { enabled: false, rate: 0, type: "basic" },
  cost_per_person: {
    enabled: false,
    headcount: 0,
    calculation_base: "final_total",
  },
  taxes: { enabled: true, rate: 0.16, name: "IVA" },
};
```

---

## ⚠️ **CONSIDERACIONES IMPORTANTES**

### **🔒 Seguridad**

- Todos los endpoints requieren validación en el frontend
- Implementar rate limiting para APIs de cálculo
- Validar datos de entrada antes de enviar

### **⚡ Performance**

- Usar debouncing para cálculos dinámicos
- Cachear configuraciones de pricing
- Implementar loading states apropiados

### **🐛 Manejo de Errores**

```typescript
try {
  const result = await api.updatePricingConfig(rfxId, config);
} catch (error) {
  if (error.status === 404) {
    // RFX no encontrado
  } else if (error.status === 400) {
    // Datos inválidos
  } else {
    // Error del servidor
  }
}
```

### **📱 Responsividad**

- Los componentes de pricing deben ser responsivos
- Usar breakpoints apropiados para tablas de cálculo
- Implementar UX optimizada para móviles

---

## 🎉 **NUEVAS FUNCIONALIDADES V2.2**

### **✨ Independencia Total**

- Coordinación y costo por persona son completamente independientes
- Se pueden configurar por separado
- Cálculos optimizados a nivel de base de datos

### **📊 Auditoría Completa**

- Historial de todos los cambios de configuración
- Tracking de quién y cuándo se modificaron precios
- Trazabilidad completa de decisiones de pricing

### **⚡ Performance Mejorado**

- Consultas SQL directas (sin parsing JSON)
- Stored procedures para cálculos complejos
- Índices optimizados para búsquedas rápidas

### **🎛️ Flexibilidad Extendida**

- Configuraciones por tipo de coordinación
- Bases de cálculo configurables
- Presets personalizables

---

## 🚀 **PRÓXIMOS PASOS PARA EL FRONTEND**

1. **Implementar hooks de pricing** (`usePricing`, `usePricingCalculation`)
2. **Crear componentes de configuración** (`PricingConfig`, `PricingCalculator`)
3. **Integrar en flujos existentes** (RFX creation, proposal generation)
4. **Añadir validaciones en tiempo real**
5. **Implementar presets de configuración**
6. **Crear dashboard de análisis de pricing**

---

**🎯 El sistema V2.2 está completamente funcional y listo para la integración frontend.** Todos los endpoints han sido probados y verificados. La base de datos está normalizada y optimizada para performance.

**¿Necesitas ayuda con algún endpoint específico o flujo de integración?** 🚀
