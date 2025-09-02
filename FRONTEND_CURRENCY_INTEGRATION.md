# 💰 **GUÍA DE INTEGRACIÓN FRONTEND - MONEDAS**

## 📋 **INTRODUCCIÓN**

Esta guía te ayudará a integrar los nuevos endpoints de moneda en tus componentes React/Vue/Angular para **mostrar y actualizar monedas** en el sistema RFX.

### **🎯 OBJETIVOS**

- Mostrar la moneda correcta en todos los importes
- Permitir cambio de moneda cuando sea seguro
- Proporcionar feedback claro al usuario
- Mantener consistencia en toda la aplicación

---

## 🔗 **ENDPOINTS DISPONIBLES**

### **📍 Endpoints que incluyen moneda:**

- `GET /api/rfx/{rfxId}` → Campo `currency` en respuesta
- `GET /api/rfx/{rfxId}/products` → Campo `currency` en `data`
- `GET /api/pricing/config/{rfxId}` → Campo `currency` en `data`
- `POST /api/pricing/calculate/{rfxId}` → Campo `currency` en `data`

### **📍 Endpoint de actualización:**

- `PUT /api/rfx/{rfxId}/currency` → Cambiar moneda del RFX

---

## 📱 **COMPONENTES FRONTEND NECESARIOS**

### **1. 💰 Currency Display Component**

**Purpose:** Mostrar importes con su moneda de forma consistente

```jsx
// CurrencyDisplay.jsx
import React from "react";

const CurrencyDisplay = ({
  amount,
  currency = "USD", // Predeterminado por AI
  showSymbol = true,
  precision = 2,
  className = "",
}) => {
  const formatCurrency = (amount, currency, precision) => {
    if (amount === null || amount === undefined) return "N/A";

    const numberFormatter = new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });

    return numberFormatter.format(amount);
  };

  const currencySymbols = {
    MXN: "$",
    USD: "$",
    EUR: "€",
    GBP: "£",
    CAD: "C$",
  };

  return (
    <span className={`currency-display ${className}`}>
      {showSymbol && (
        <span className="currency-symbol">
          {currencySymbols[currency] || currency}
        </span>
      )}
      <span className="amount">
        {formatCurrency(amount, currency, precision)}
      </span>
    </span>
  );
};

export default CurrencyDisplay;
```

**Usage:**

```jsx
// En cualquier componente
<CurrencyDisplay amount={2500.50} currency="USD" />
// Resultado: $2,500.50

<CurrencyDisplay amount={100.00} currency="EUR" showSymbol={false} />
// Resultado: €100.00
```

### **2. 🔄 Currency Selector Component**

**Purpose:** Permitir selección y cambio de moneda

```jsx
// CurrencySelector.jsx
import React, { useState } from "react";

const CurrencySelector = ({
  currentCurrency,
  onCurrencyChange,
  disabled = false,
  rfxId,
  hasProducts = false,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const availableCurrencies = [
    { code: "USD", name: "Dólar Americano", symbol: "$" }, // Predeterminado por AI
    { code: "MXN", name: "Peso Mexicano", symbol: "$" },
    { code: "EUR", name: "Euro", symbol: "€" },
    { code: "CAD", name: "Dólar Canadiense", symbol: "C$" },
  ];

  const handleCurrencyChange = async (newCurrency) => {
    if (newCurrency === currentCurrency) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/rfx/${rfxId}/currency`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ currency: newCurrency }),
      });

      const result = await response.json();

      if (response.ok) {
        // MVP: Manejar warnings de productos no convertidos
        if (result.data?.warnings?.includes("prices_not_converted")) {
          alert(
            `⚠️ Moneda cambiada a ${newCurrency}. ${result.data.priced_products_count} productos requieren ajuste manual de precios.`
          );
        }
        onCurrencyChange(newCurrency, result);
      } else {
        throw new Error(result.message || "Error updating currency");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const isDisabled = disabled || isLoading; // MVP: No bloquear por productos

  return (
    <div className="currency-selector">
      <label className="currency-label">Moneda:</label>

      <select
        value={currentCurrency}
        onChange={(e) => handleCurrencyChange(e.target.value)}
        disabled={isDisabled}
        className={`currency-select ${isDisabled ? "disabled" : ""}`}
      >
        {availableCurrencies.map((currency) => (
          <option key={currency.code} value={currency.code}>
            {currency.symbol} {currency.code} - {currency.name}
          </option>
        ))}
      </select>

      {isLoading && <span className="loading">Actualizando...</span>}

      {/* MVP: Mostrar warning después del cambio, no bloquear */}

      {error && <div className="error">❌ Error: {error}</div>}
    </div>
  );
};

export default CurrencySelector;
```

### **3. 📊 Product List with Currency**

**Purpose:** Mostrar productos con precios en la moneda correcta

```jsx
// ProductList.jsx
import React, { useState, useEffect } from "react";
import CurrencyDisplay from "./CurrencyDisplay";

const ProductList = ({ rfxId }) => {
  const [products, setProducts] = useState([]);
  const [currency, setCurrency] = useState("USD"); // Predeterminado por AI
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProducts();
  }, [rfxId]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/rfx/${rfxId}/products`);
      const result = await response.json();

      if (response.ok) {
        setProducts(result.data.products);
        setCurrency(result.data.currency);
      } else {
        throw new Error(result.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Cargando productos...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="product-list">
      <h3>Productos ({currency})</h3>

      <table className="products-table">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Cantidad</th>
            <th>Precio Unitario</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.id}>
              <td>{product.product_name}</td>
              <td>
                {product.quantity} {product.unit_of_measure}
              </td>
              <td>
                <CurrencyDisplay
                  amount={product.estimated_unit_price}
                  currency={currency}
                />
              </td>
              <td>
                <CurrencyDisplay
                  amount={product.total_estimated_cost}
                  currency={currency}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="subtotal">
        <strong>
          Subtotal:{" "}
          <CurrencyDisplay
            amount={products.reduce(
              (sum, p) => sum + (p.total_estimated_cost || 0),
              0
            )}
            currency={currency}
          />
        </strong>
      </div>
    </div>
  );
};

export default ProductList;
```

### **4. 💳 Pricing Calculator Component**

**Purpose:** Mostrar cálculos de pricing con moneda

```jsx
// PricingCalculator.jsx
import React, { useState, useEffect } from "react";
import CurrencyDisplay from "./CurrencyDisplay";

const PricingCalculator = ({ rfxId, subtotal }) => {
  const [pricingData, setPricingData] = useState(null);
  const [currency, setCurrency] = useState("USD"); // Predeterminado por AI
  const [loading, setLoading] = useState(false);

  const calculatePricing = async () => {
    if (!subtotal || subtotal <= 0) return;

    try {
      setLoading(true);
      const response = await fetch(`/api/pricing/calculate/${rfxId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ subtotal }),
      });

      const result = await response.json();

      if (response.ok) {
        setPricingData(result.data);
        setCurrency(result.data.currency);
      }
    } catch (err) {
      console.error("Error calculating pricing:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    calculatePricing();
  }, [rfxId, subtotal]);

  if (!pricingData) return null;

  const { summary } = pricingData;

  return (
    <div className="pricing-calculator">
      <h3>Cálculo de Pricing ({currency})</h3>

      <div className="pricing-breakdown">
        <div className="line-item">
          <span>Subtotal:</span>
          <CurrencyDisplay amount={summary.subtotal} currency={currency} />
        </div>

        {summary.coordination_amount > 0 && (
          <div className="line-item">
            <span>Coordinación:</span>
            <CurrencyDisplay
              amount={summary.coordination_amount}
              currency={currency}
            />
          </div>
        )}

        {summary.tax_amount > 0 && (
          <div className="line-item">
            <span>Impuestos:</span>
            <CurrencyDisplay amount={summary.tax_amount} currency={currency} />
          </div>
        )}

        <div className="line-item total">
          <strong>
            <span>Total:</span>
            <CurrencyDisplay amount={summary.total_cost} currency={currency} />
          </strong>
        </div>

        {summary.cost_per_person && (
          <div className="cost-per-person">
            <em>
              Costo por persona:{" "}
              <CurrencyDisplay
                amount={summary.cost_per_person}
                currency={currency}
              />
            </em>
          </div>
        )}
      </div>

      {loading && <div className="loading">Calculando...</div>}
    </div>
  );
};

export default PricingCalculator;
```

---

## 🎯 **FLUJOS DE INTEGRACIÓN**

### **🔄 Flujo 1: Pantalla Principal de RFX**

```jsx
// RFXDetailPage.jsx
import React, { useState, useEffect } from "react";
import CurrencySelector from "./CurrencySelector";
import ProductList from "./ProductList";
import PricingCalculator from "./PricingCalculator";

const RFXDetailPage = ({ rfxId }) => {
  const [rfxData, setRfxData] = useState(null);
  const [hasProducts, setHasProducts] = useState(false);

  useEffect(() => {
    fetchRFXData();
  }, [rfxId]);

  const fetchRFXData = async () => {
    try {
      // Obtener datos del RFX
      const response = await fetch(`/api/rfx/${rfxId}`);
      const result = await response.json();

      if (response.ok) {
        setRfxData(result.data);

        // Verificar si tiene productos
        const productsResponse = await fetch(`/api/rfx/${rfxId}/products`);
        const productsResult = await productsResponse.json();

        if (productsResponse.ok) {
          setHasProducts(productsResult.data.products.length > 0);
        }
      }
    } catch (err) {
      console.error("Error fetching RFX data:", err);
    }
  };

  const handleCurrencyChange = (newCurrency, result) => {
    // Actualizar estado local
    setRfxData((prev) => ({
      ...prev,
      currency: newCurrency,
    }));

    // Mostrar notificación de éxito
    alert(`Moneda actualizada a ${newCurrency}`);

    // Refresh de datos
    fetchRFXData();
  };

  if (!rfxData) return <div>Cargando...</div>;

  return (
    <div className="rfx-detail-page">
      <div className="rfx-header">
        <h1>{rfxData.title}</h1>

        <CurrencySelector
          currentCurrency={rfxData.currency}
          onCurrencyChange={handleCurrencyChange}
          rfxId={rfxId}
          hasProducts={hasProducts}
        />
      </div>

      <ProductList rfxId={rfxId} />

      <PricingCalculator rfxId={rfxId} subtotal={rfxData.actual_cost || 0} />
    </div>
  );
};

export default RFXDetailPage;
```

### **🔄 Flujo 2: Lista de RFX con Monedas**

```jsx
// RFXList.jsx
import React, { useState, useEffect } from "react";
import CurrencyDisplay from "./CurrencyDisplay";

const RFXList = () => {
  const [rfxList, setRfxList] = useState([]);

  useEffect(() => {
    fetchRFXList();
  }, []);

  const fetchRFXList = async () => {
    try {
      const response = await fetch("/api/rfx/recent");
      const result = await response.json();

      if (response.ok) {
        setRfxList(result.data);
      }
    } catch (err) {
      console.error("Error fetching RFX list:", err);
    }
  };

  return (
    <div className="rfx-list">
      <h2>RFX Recientes</h2>

      <table className="rfx-table">
        <thead>
          <tr>
            <th>Título</th>
            <th>Cliente</th>
            <th>Costo Total</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {rfxList.map((rfx) => (
            <tr key={rfx.id}>
              <td>{rfx.title}</td>
              <td>{rfx.client}</td>
              <td>
                <CurrencyDisplay
                  amount={rfx.costo_total}
                  currency={rfx.currency}
                />
              </td>
              <td>{rfx.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default RFXList;
```

---

## 🎨 **ESTILOS CSS RECOMENDADOS**

```css
/* currency-components.css */

.currency-display {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.currency-symbol {
  font-weight: bold;
  color: #666;
}

.amount {
  font-family: "Roboto Mono", monospace;
}

.currency-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 300px;
}

.currency-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.currency-select.disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.warning {
  color: #ff9500;
  font-size: 12px;
  padding: 0.25rem 0;
}

.error {
  color: #ff3333;
  font-size: 12px;
  padding: 0.25rem 0;
}

.loading {
  color: #007bff;
  font-size: 12px;
}

.pricing-breakdown {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 1rem;
  background-color: #fafafa;
}

.line-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.line-item.total {
  border-top: 2px solid #333;
  border-bottom: none;
  font-size: 1.1em;
}

.cost-per-person {
  text-align: center;
  margin-top: 1rem;
  color: #666;
}
```

---

## ⚠️ **MANEJO DE ERRORES Y EDGE CASES**

### **1. RFX sin moneda (datos legacy):**

```jsx
const safeCurrency = rfx.currency || "USD"; // AI extrae USD como predeterminado
```

### **2. Productos con precios existentes:**

```jsx
const hasProducts = products.some((p) => p.estimated_unit_price > 0);

if (hasProducts) {
  return (
    <div className="currency-locked">
      ⚠️ No se puede cambiar la moneda porque hay productos valorados
    </div>
  );
}
```

### **3. Error de red:**

```jsx
const handleCurrencyChange = async (newCurrency) => {
  try {
    // ... llamada a API
  } catch (error) {
    setError("Error de conexión. Intenta nuevamente.");
    // Revertir cambio en UI si es necesario
  }
};
```

### **4. Validación de entrada:**

```jsx
const isValidCurrency = (currency) => {
  return /^[A-Z]{3}$/.test(currency);
};
```

---

## 🚀 **MEJORES PRÁCTICAS**

### **1. Consistencia:**

- Usa siempre `CurrencyDisplay` para mostrar importes
- Mantén el mismo formato en toda la app

### **2. Performance:**

- Cache currency configuration por RFX
- Debounce currency selector changes

### **3. UX:**

- Muestra loading states durante cambios
- Proporciona feedback claro al usuario
- Deshabilita selector cuando no es seguro cambiar

### **4. Accesibilidad:**

- Labels claros en selectors
- Estados de error bien contrastados
- Soporte para lectores de pantalla

---

## ✅ **CHECKLIST DE IMPLEMENTACIÓN**

- [ ] **CurrencyDisplay component** implementado y probado
- [ ] **CurrencySelector component** con validaciones
- [ ] **ProductList** muestra precios con moneda correcta
- [ ] **PricingCalculator** incluye moneda en cálculos
- [ ] **Error handling** para casos edge
- [ ] **Loading states** en todos los cambios
- [ ] **Estilos CSS** aplicados consistentemente
- [ ] **Tests unitarios** para componentes críticos
- [ ] **Integration testing** de flujos completos

---

## 🤖 **SISTEMA DE DETECCIÓN AUTOMÁTICA DE MONEDA**

### **Cómo funciona la extracción por AI:**

1. **Análisis del documento**: El AI busca automáticamente indicadores de moneda en el texto del RFX
2. **Patrones detectados**:
   - Símbolos: `$`, `€`, `£`, `CAD$`, `USD$`
   - Menciones directas: "dólares", "euros", "pesos", "libras"
   - Códigos ISO: USD, EUR, MXN, CAD, GBP
3. **Fallback inteligente**: Si no encuentra moneda específica → USD como predeterminado
4. **Validación**: Solo acepta códigos ISO 4217 válidos de 3 letras

### **Ventajas del nuevo sistema:**

- ✅ **Automático**: No requiere input manual en la mayoría de casos
- ✅ **Inteligente**: Reconoce diferentes formatos y idiomas
- ✅ **Consistente**: Siempre tiene una moneda válida
- ✅ **Limpio**: Sin código redundante, fuente única de verdad
- ✅ **Extensible**: Fácil agregar nuevas monedas al análisis

### **Para desarrolladores:**

La moneda ya viene extraída desde el backend, solo necesitas:

```jsx
// ✅ Simplemente usa la moneda que viene en la respuesta
const currency = rfx.currency; // Ya validada por el AI

// ❌ NO necesitas manejar fallbacks complejos
// const currency = rfx.currency || "MXN" || detectCurrency(rfx.content)
```

---

## ⚠️ **MVP: CAMBIO SIN BLOQUEOS**

### **Comportamiento implementado:**

1. **Cambio permitido**: Los usuarios pueden cambiar moneda aunque haya productos con precios
2. **Sin conversión automática**: Los precios mantienen valores numéricos, solo cambia la moneda mostrada
3. **Warning obligatorio**: Alert automático advierte que los precios requieren ajuste manual
4. **Auditoría completa**: Cada cambio se registra en `rfx_history` con conteo de productos afectados

### **Respuesta del API:**

```json
{
  "status": "success",
  "message": "Currency updated successfully from EUR to USD. 9 product prices were NOT converted and require manual adjustment.",
  "data": {
    "changed": true,
    "new_currency": "USD",
    "old_currency": "EUR",
    "priced_products_count": 9,
    "warnings": ["prices_not_converted"]
  }
}
```

**¡Tu sistema estará listo para manejar múltiples monedas de forma profesional y user-friendly!** 🎉
