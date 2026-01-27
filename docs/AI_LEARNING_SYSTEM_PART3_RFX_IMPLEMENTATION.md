# 🎯 AI LEARNING SYSTEM - PARTE 3: IMPLEMENTACIÓN PARA RFX AUTOMATION

**Versión:** 1.0  
**Fecha:** 26 de Enero, 2026  
**Propósito:** Implementación específica del sistema de aprendizaje para RFX Automation

---

## 📋 CONTENIDO

1. [Casos de Uso RFX](#casos-de-uso-rfx)
2. [Aprendizaje de Productos y Precios](#aprendizaje-de-productos-y-precios)
3. [Aprendizaje de Patrones de Usuario](#aprendizaje-de-patrones-de-usuario)
4. [Aprendizaje de Configuraciones](#aprendizaje-de-configuraciones)
5. [Integración con Sistema Existente](#integración-con-sistema-existente)
6. [Plan de Implementación](#plan-de-implementación)

---

## 🎯 CASOS DE USO RFX

### Escenarios Principales

#### 1. **Aprendizaje de Precios Personalizados**

```
ESCENARIO:
Usuario A siempre aplica descuento del 18% para eventos de 300+ personas
Usuario B prefiere precios estándar pero ajusta por temporada

SISTEMA APRENDE:
- Patrón de descuentos por volumen de cada usuario
- Preferencias de pricing por tipo de evento
- Ajustes estacionales personalizados

RESULTADO:
Próxima vez que Usuario A cree RFX de 350 personas,
el sistema sugiere automáticamente descuento del 18%
```

#### 2. **Recomendación de Productos**

```
ESCENARIO:
Organización X siempre incluye:
- Tequeños + Empanadas (95% de los RFX)
- Canapés cuando hay > 200 personas (80%)
- Mini Pizzas para eventos corporativos (70%)

SISTEMA APRENDE:
- Productos frecuentemente usados juntos
- Patrones por tipo de evento
- Cantidades típicas por número de personas

RESULTADO:
Al crear nuevo RFX de evento corporativo (250 personas),
el sistema recomienda: Tequeños, Empanadas, Canapés, Mini Pizzas
con cantidades sugeridas basadas en historial
```

#### 3. **Optimización de Configuraciones**

```
ESCENARIO:
Usuario siempre activa:
- Coordinación: 18%
- Impuestos: 16%
- Costo por persona: desactivado

SISTEMA APRENDE:
- Configuración preferida de pricing
- Patrones de activación/desactivación
- Valores típicos por tipo de RFX

RESULTADO:
Al crear nuevo RFX, configuración se pre-llena automáticamente
con preferencias aprendidas del usuario
```

#### 4. **Corrección de Errores Comunes**

```
ESCENARIO:
Sistema extrae "Tequeños - 200 unidades - $0.80/u"
Usuario corrige a "$0.68/u" (descuento bulk)

SISTEMA APRENDE:
- Regla: Tequeños > 150 unidades → precio $0.68/u
- Contexto: Usuario específico, organización, tipo evento
- Patrón: Descuentos por volumen

RESULTADO:
Próxima extracción de Tequeños (200+ unidades),
el sistema aplica automáticamente $0.68/u
```

---

## 💰 APRENDIZAJE DE PRODUCTOS Y PRECIOS

### Knowledge Graph para Productos

```python
class ProductKnowledgeGraph:
    """
    Grafo de conocimiento temporal para productos y precios
    """
    
    def __init__(self, kg_service, vector_store):
        self.kg = kg_service
        self.vector_store = vector_store
    
    async def learn_product_correction(
        self,
        product_name: str,
        old_price: float,
        new_price: float,
        quantity: int,
        user_id: str,
        organization_id: str,
        context: dict
    ):
        """
        Aprende de una corrección de precio de producto
        """
        # 1. Crear/actualizar entidad de producto
        product_entity = await self.kg.upsert_entity(
            entity_type='product',
            entity_id=self._normalize_product_name(product_name),
            properties={
                'name': product_name,
                'category': await self._infer_category(product_name),
                'unit': 'unit'
            },
            organization_id=organization_id
        )
        
        # 2. Crear entidad de precio
        price_entity = await self.kg.upsert_entity(
            entity_type='price',
            entity_id=f"price_{new_price}_{datetime.now().isoformat()}",
            properties={
                'amount': new_price,
                'currency': 'USD',
                'quantity_threshold': quantity,
                'context': context
            },
            organization_id=organization_id
        )
        
        # 3. Crear relación temporal
        await self.kg.upsert_relation(
            source_entity_id=product_entity.id,
            target_entity_id=price_entity.id,
            relation_type='HAS_PRICE',
            properties={
                'quantity_min': quantity,
                'applied_by_user': user_id,
                'event_type': context.get('event_type'),
                'correction_from': old_price
            },
            confidence=self._calculate_confidence(old_price, new_price),
            organization_id=organization_id
        )
        
        # 4. Invalidar precio anterior si existe
        await self._invalidate_old_price(
            product_entity.id,
            old_price,
            organization_id
        )
        
        logger.info(
            f"✅ Learned price correction: {product_name} "
            f"${old_price} → ${new_price} (qty: {quantity})"
        )
    
    async def get_learned_price(
        self,
        product_name: str,
        quantity: int,
        organization_id: str,
        context: dict = None
    ) -> Optional[float]:
        """
        Obtiene precio aprendido para un producto
        """
        # Query Cypher para buscar precio más relevante
        query = """
        MATCH (p:Product {name: $product_name})-[r:HAS_PRICE]->(price:Price)
        WHERE r.organization_id = $org_id
          AND r.t_valid <= $now
          AND (r.t_invalid IS NULL OR r.t_invalid > $now)
          AND price.quantity_threshold <= $quantity
        ORDER BY r.confidence DESC, price.quantity_threshold DESC
        LIMIT 1
        RETURN price.amount as price, r.confidence as confidence
        """
        
        result = await self.kg.execute_query(
            query,
            params={
                'product_name': self._normalize_product_name(product_name),
                'org_id': organization_id,
                'quantity': quantity,
                'now': datetime.utcnow()
            }
        )
        
        if result:
            logger.info(
                f"📊 Found learned price for {product_name}: "
                f"${result['price']} (confidence: {result['confidence']})"
            )
            return result['price']
        
        return None
    
    async def learn_product_association(
        self,
        product_a: str,
        product_b: str,
        organization_id: str,
        rfx_id: str
    ):
        """
        Aprende que dos productos se usan juntos
        """
        # Crear/actualizar relación de co-ocurrencia
        await self.kg.upsert_relation(
            source_entity_id=await self._get_product_entity_id(product_a, organization_id),
            target_entity_id=await self._get_product_entity_id(product_b, organization_id),
            relation_type='CO_OCCURS_WITH',
            properties={
                'rfx_id': rfx_id,
                'count': 1  # Se incrementa si ya existe
            },
            organization_id=organization_id
        )
    
    async def get_recommended_products(
        self,
        current_products: List[str],
        organization_id: str,
        k: int = 5
    ) -> List[dict]:
        """
        Recomienda productos basados en productos actuales
        """
        # Query para productos que co-ocurren frecuentemente
        query = """
        MATCH (p1:Product)-[r:CO_OCCURS_WITH]->(p2:Product)
        WHERE p1.name IN $current_products
          AND r.organization_id = $org_id
          AND NOT p2.name IN $current_products
        WITH p2, SUM(r.count) as total_cooccurrence
        ORDER BY total_cooccurrence DESC
        LIMIT $k
        RETURN p2.name as product, total_cooccurrence as score
        """
        
        results = await self.kg.execute_query(
            query,
            params={
                'current_products': current_products,
                'org_id': organization_id,
                'k': k
            }
        )
        
        return [
            {
                'product': r['product'],
                'score': r['score'],
                'reason': f"Frequently used with {', '.join(current_products[:2])}"
            }
            for r in results
        ]
    
    def _calculate_confidence(self, old_price: float, new_price: float) -> float:
        """
        Calcula confianza de la corrección
        """
        # Mayor diferencia = mayor confianza (corrección intencional)
        price_diff_pct = abs(new_price - old_price) / old_price
        
        if price_diff_pct > 0.3:  # > 30% diferencia
            return 0.95
        elif price_diff_pct > 0.15:  # > 15% diferencia
            return 0.85
        elif price_diff_pct > 0.05:  # > 5% diferencia
            return 0.75
        else:  # Pequeña corrección
            return 0.60
    
    def _normalize_product_name(self, name: str) -> str:
        """Normaliza nombre de producto para consistencia"""
        return name.lower().strip().replace('  ', ' ')
```

### Few-Shot Learning para Pricing

```python
class PricingFewShotLearner:
    """
    Aprendizaje few-shot específico para pricing
    """
    
    def __init__(self, vector_store, embedding_model):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
    
    async def store_pricing_example(
        self,
        product_name: str,
        quantity: int,
        price: float,
        context: dict,
        organization_id: str,
        user_id: str
    ):
        """
        Almacena ejemplo de pricing
        """
        # Construir descripción del ejemplo
        example_text = self._build_example_description(
            product_name, quantity, price, context
        )
        
        # Generar embedding
        embedding = await self.embedding_model.encode(example_text)
        
        # Almacenar en vector store
        await self.vector_store.add(
            id=f"pricing_{organization_id}_{user_id}_{datetime.now().timestamp()}",
            embedding=embedding,
            metadata={
                'type': 'pricing_example',
                'product_name': product_name,
                'quantity': quantity,
                'price': price,
                'price_per_unit': price / quantity if quantity > 0 else price,
                'context': context,
                'organization_id': organization_id,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def retrieve_similar_pricing(
        self,
        product_name: str,
        quantity: int,
        context: dict,
        organization_id: str,
        k: int = 5
    ) -> List[dict]:
        """
        Recupera ejemplos similares de pricing
        """
        # Construir query
        query_text = self._build_example_description(
            product_name, quantity, None, context
        )
        
        # Generar embedding
        query_embedding = await self.embedding_model.encode(query_text)
        
        # Búsqueda semántica
        results = await self.vector_store.search(
            embedding=query_embedding,
            filters={
                'organization_id': organization_id,
                'type': 'pricing_example'
            },
            k=k * 2  # Recuperar más para filtrar
        )
        
        # Filtrar por relevancia de cantidad
        filtered_results = self._filter_by_quantity_relevance(
            results, quantity
        )
        
        return filtered_results[:k]
    
    async def predict_price(
        self,
        product_name: str,
        quantity: int,
        context: dict,
        organization_id: str
    ) -> dict:
        """
        Predice precio usando ejemplos similares
        """
        # Recuperar ejemplos
        examples = await self.retrieve_similar_pricing(
            product_name, quantity, context, organization_id
        )
        
        if not examples:
            return {
                'predicted_price': None,
                'confidence': 0,
                'reasoning': 'No historical examples found'
            }
        
        # Calcular precio ponderado por similitud
        total_weight = sum(ex['score'] for ex in examples)
        weighted_price = sum(
            ex['metadata']['price'] * ex['score']
            for ex in examples
        ) / total_weight
        
        # Calcular confianza
        confidence = self._calculate_prediction_confidence(examples)
        
        return {
            'predicted_price': weighted_price,
            'confidence': confidence,
            'reasoning': self._build_reasoning(examples),
            'examples_used': len(examples),
            'example_details': [
                {
                    'product': ex['metadata']['product_name'],
                    'quantity': ex['metadata']['quantity'],
                    'price': ex['metadata']['price'],
                    'similarity': ex['score']
                }
                for ex in examples[:3]
            ]
        }
    
    def _build_example_description(
        self,
        product_name: str,
        quantity: int,
        price: Optional[float],
        context: dict
    ) -> str:
        """
        Construye descripción textual del ejemplo
        """
        parts = [
            f"Product: {product_name}",
            f"Quantity: {quantity} units"
        ]
        
        if price is not None:
            parts.append(f"Price: ${price:.2f} (${price/quantity:.2f}/unit)")
        
        if context.get('event_type'):
            parts.append(f"Event type: {context['event_type']}")
        
        if context.get('attendees'):
            parts.append(f"Attendees: {context['attendees']}")
        
        if context.get('season'):
            parts.append(f"Season: {context['season']}")
        
        return " | ".join(parts)
    
    def _filter_by_quantity_relevance(
        self,
        results: List[dict],
        target_quantity: int
    ) -> List[dict]:
        """
        Filtra resultados por relevancia de cantidad
        """
        # Preferir ejemplos con cantidades similares
        for result in results:
            example_qty = result['metadata']['quantity']
            
            # Penalizar ejemplos con cantidades muy diferentes
            qty_ratio = min(example_qty, target_quantity) / max(example_qty, target_quantity)
            result['score'] *= qty_ratio
        
        # Re-ordenar por score ajustado
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _calculate_prediction_confidence(self, examples: List[dict]) -> float:
        """
        Calcula confianza de la predicción
        """
        if not examples:
            return 0.0
        
        # Factores de confianza
        num_examples = len(examples)
        avg_similarity = sum(ex['score'] for ex in examples) / num_examples
        price_variance = self._calculate_price_variance(examples)
        
        # Confianza base por número de ejemplos
        base_confidence = min(num_examples / 5, 1.0)  # Max con 5 ejemplos
        
        # Ajustar por similitud promedio
        similarity_factor = avg_similarity
        
        # Penalizar por alta varianza en precios
        variance_penalty = 1 - min(price_variance / 0.5, 1.0)
        
        confidence = base_confidence * similarity_factor * variance_penalty
        
        return round(confidence, 2)
    
    def _calculate_price_variance(self, examples: List[dict]) -> float:
        """
        Calcula varianza en precios de ejemplos
        """
        prices = [ex['metadata']['price_per_unit'] for ex in examples]
        
        if len(prices) < 2:
            return 0.0
        
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        
        # Normalizar por precio promedio
        return (variance ** 0.5) / mean_price if mean_price > 0 else 0
    
    def _build_reasoning(self, examples: List[dict]) -> str:
        """
        Construye explicación de la predicción
        """
        if not examples:
            return "No historical data available"
        
        top_example = examples[0]
        
        return (
            f"Based on {len(examples)} similar past transactions. "
            f"Most similar: {top_example['metadata']['product_name']} "
            f"({top_example['metadata']['quantity']} units at "
            f"${top_example['metadata']['price']:.2f})"
        )
```

---

## 👤 APRENDIZAJE DE PATRONES DE USUARIO

### User Preference Learning

```python
class UserPreferenceLearner:
    """
    Aprende preferencias y patrones de usuario
    """
    
    def __init__(self, db, analytics_service):
        self.db = db
        self.analytics = analytics_service
    
    async def learn_from_rfx_creation(
        self,
        user_id: str,
        organization_id: str,
        rfx_data: dict
    ):
        """
        Aprende de la creación de un RFX
        """
        # 1. Productos seleccionados
        await self._learn_product_preferences(
            user_id, organization_id, rfx_data.get('products', [])
        )
        
        # 2. Configuración de pricing
        await self._learn_pricing_config_preferences(
            user_id, organization_id, rfx_data.get('pricing_config', {})
        )
        
        # 3. Patrones de cantidades
        await self._learn_quantity_patterns(
            user_id, organization_id, rfx_data
        )
        
        # 4. Patrones temporales
        await self._learn_temporal_patterns(
            user_id, organization_id, rfx_data
        )
    
    async def _learn_product_preferences(
        self,
        user_id: str,
        organization_id: str,
        products: List[dict]
    ):
        """
        Aprende preferencias de productos
        """
        for product in products:
            # Incrementar contador de uso
            await self.db.execute(
                """
                INSERT INTO user_product_preferences 
                    (user_id, organization_id, product_name, usage_count, last_used)
                VALUES ($1, $2, $3, 1, NOW())
                ON CONFLICT (user_id, product_name) 
                DO UPDATE SET 
                    usage_count = user_product_preferences.usage_count + 1,
                    last_used = NOW()
                """,
                user_id, organization_id, product['name']
            )
    
    async def _learn_pricing_config_preferences(
        self,
        user_id: str,
        organization_id: str,
        pricing_config: dict
    ):
        """
        Aprende preferencias de configuración de pricing
        """
        config_snapshot = {
            'coordination_enabled': pricing_config.get('coordination_enabled', False),
            'coordination_rate': pricing_config.get('coordination_rate'),
            'taxes_enabled': pricing_config.get('taxes_enabled', False),
            'tax_rate': pricing_config.get('tax_rate'),
            'cost_per_person_enabled': pricing_config.get('cost_per_person_enabled', False),
            'headcount': pricing_config.get('headcount')
        }
        
        # Almacenar snapshot de configuración
        await self.db.execute(
            """
            INSERT INTO user_pricing_config_history
                (user_id, organization_id, config_snapshot, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id, organization_id, json.dumps(config_snapshot)
        )
    
    async def _learn_quantity_patterns(
        self,
        user_id: str,
        organization_id: str,
        rfx_data: dict
    ):
        """
        Aprende patrones de cantidades típicas
        """
        products = rfx_data.get('products', [])
        attendees = rfx_data.get('attendees', 0)
        
        for product in products:
            quantity = product.get('quantity', 0)
            
            if attendees > 0:
                # Calcular ratio cantidad/persona
                ratio = quantity / attendees
                
                await self.db.execute(
                    """
                    INSERT INTO user_quantity_patterns
                        (user_id, organization_id, product_name, 
                         quantity_per_person, sample_size)
                    VALUES ($1, $2, $3, $4, 1)
                    ON CONFLICT (user_id, product_name)
                    DO UPDATE SET
                        quantity_per_person = (
                            user_quantity_patterns.quantity_per_person * 
                            user_quantity_patterns.sample_size + $4
                        ) / (user_quantity_patterns.sample_size + 1),
                        sample_size = user_quantity_patterns.sample_size + 1
                    """,
                    user_id, organization_id, product['name'], ratio
                )
    
    async def get_user_preferences(
        self,
        user_id: str,
        organization_id: str
    ) -> dict:
        """
        Obtiene preferencias aprendidas del usuario
        """
        # 1. Productos más usados
        top_products = await self.db.fetch(
            """
            SELECT product_name, usage_count, last_used
            FROM user_product_preferences
            WHERE user_id = $1 AND organization_id = $2
            ORDER BY usage_count DESC, last_used DESC
            LIMIT 10
            """,
            user_id, organization_id
        )
        
        # 2. Configuración de pricing más común
        common_pricing_config = await self._get_most_common_pricing_config(
            user_id, organization_id
        )
        
        # 3. Patrones de cantidad
        quantity_patterns = await self.db.fetch(
            """
            SELECT product_name, quantity_per_person, sample_size
            FROM user_quantity_patterns
            WHERE user_id = $1 AND organization_id = $2
            ORDER BY sample_size DESC
            """,
            user_id, organization_id
        )
        
        return {
            'preferred_products': [
                {
                    'name': p['product_name'],
                    'usage_count': p['usage_count'],
                    'last_used': p['last_used']
                }
                for p in top_products
            ],
            'typical_pricing_config': common_pricing_config,
            'quantity_patterns': [
                {
                    'product': p['product_name'],
                    'qty_per_person': p['quantity_per_person'],
                    'confidence': min(p['sample_size'] / 10, 1.0)
                }
                for p in quantity_patterns
            ]
        }
    
    async def _get_most_common_pricing_config(
        self,
        user_id: str,
        organization_id: str
    ) -> dict:
        """
        Obtiene la configuración de pricing más común del usuario
        """
        # Obtener últimas 20 configuraciones
        configs = await self.db.fetch(
            """
            SELECT config_snapshot
            FROM user_pricing_config_history
            WHERE user_id = $1 AND organization_id = $2
            ORDER BY created_at DESC
            LIMIT 20
            """,
            user_id, organization_id
        )
        
        if not configs:
            return {}
        
        # Calcular valores más comunes para cada campo
        coordination_enabled_count = sum(
            1 for c in configs 
            if json.loads(c['config_snapshot']).get('coordination_enabled')
        )
        
        taxes_enabled_count = sum(
            1 for c in configs 
            if json.loads(c['config_snapshot']).get('taxes_enabled')
        )
        
        # Promediar valores numéricos
        coordination_rates = [
            json.loads(c['config_snapshot']).get('coordination_rate')
            for c in configs
            if json.loads(c['config_snapshot']).get('coordination_rate')
        ]
        
        tax_rates = [
            json.loads(c['config_snapshot']).get('tax_rate')
            for c in configs
            if json.loads(c['config_snapshot']).get('tax_rate')
        ]
        
        return {
            'coordination_enabled': coordination_enabled_count > len(configs) / 2,
            'coordination_rate': sum(coordination_rates) / len(coordination_rates) if coordination_rates else 0.18,
            'taxes_enabled': taxes_enabled_count > len(configs) / 2,
            'tax_rate': sum(tax_rates) / len(tax_rates) if tax_rates else 0.16,
            'confidence': len(configs) / 20  # Max confidence con 20 muestras
        }
```

### Contextual Bandit for Strategy Selection

```python
class RFXStrategyBandit:
    """
    Contextual Bandit para seleccionar estrategia de pricing óptima
    """
    
    def __init__(self, db):
        self.db = db
        self.arms = [
            'catalog_price',           # Precio de catálogo estándar
            'historical_average',      # Promedio histórico del usuario
            'few_shot_prediction',     # Predicción few-shot
            'kg_learned_price',        # Precio aprendido del KG
            'collaborative_filter'     # Recomendación colaborativa
        ]
    
    async def select_strategy(
        self,
        user_id: str,
        organization_id: str,
        context: dict
    ) -> str:
        """
        Selecciona estrategia óptima usando Thompson Sampling
        """
        # Obtener parámetros Beta de cada arm
        arm_params = await self._get_arm_parameters(organization_id)
        
        # Thompson Sampling: samplear de cada distribución Beta
        samples = {}
        for arm in self.arms:
            params = arm_params.get(arm, {'alpha': 1, 'beta': 1})
            sample = np.random.beta(params['alpha'], params['beta'])
            samples[arm] = sample
        
        # Seleccionar arm con sample más alto
        selected_arm = max(samples, key=samples.get)
        
        # Registrar pull
        await self._record_pull(
            organization_id, user_id, selected_arm, context
        )
        
        logger.info(
            f"🎰 Bandit selected strategy: {selected_arm} "
            f"(samples: {samples})"
        )
        
        return selected_arm
    
    async def update_reward(
        self,
        pull_id: str,
        reward: float
    ):
        """
        Actualiza recompensa de un pull
        """
        # Normalizar reward a [0, 1]
        normalized_reward = max(0, min(reward, 1))
        
        # Obtener información del pull
        pull = await self.db.fetchrow(
            "SELECT arm_name, organization_id FROM bandit_pulls WHERE id = $1",
            pull_id
        )
        
        if not pull:
            logger.error(f"Pull {pull_id} not found")
            return
        
        # Actualizar parámetros Beta
        if normalized_reward >= 0.5:  # Success
            await self.db.execute(
                """
                UPDATE bandit_arms
                SET alpha = alpha + 1,
                    total_pulls = total_pulls + 1,
                    total_rewards = total_rewards + $1,
                    avg_reward = total_rewards / total_pulls,
                    updated_at = NOW()
                WHERE organization_id = $2 AND arm_name = $3
                """,
                normalized_reward, pull['organization_id'], pull['arm_name']
            )
        else:  # Failure
            await self.db.execute(
                """
                UPDATE bandit_arms
                SET beta = beta + 1,
                    total_pulls = total_pulls + 1,
                    total_rewards = total_rewards + $1,
                    avg_reward = total_rewards / total_pulls,
                    updated_at = NOW()
                WHERE organization_id = $2 AND arm_name = $3
                """,
                normalized_reward, pull['organization_id'], pull['arm_name']
            )
        
        logger.info(
            f"✅ Updated reward for {pull['arm_name']}: {normalized_reward}"
        )
    
    async def _get_arm_parameters(
        self,
        organization_id: str
    ) -> dict:
        """
        Obtiene parámetros Beta de cada arm
        """
        arms = await self.db.fetch(
            """
            SELECT arm_name, alpha, beta
            FROM bandit_arms
            WHERE organization_id = $1
            """,
            organization_id
        )
        
        return {
            arm['arm_name']: {
                'alpha': arm['alpha'],
                'beta': arm['beta']
            }
            for arm in arms
        }
    
    async def _record_pull(
        self,
        organization_id: str,
        user_id: str,
        arm_name: str,
        context: dict
    ) -> str:
        """
        Registra un pull del bandit
        """
        pull_id = await self.db.fetchval(
            """
            INSERT INTO bandit_pulls
                (arm_id, user_id, context, timestamp)
            VALUES (
                (SELECT id FROM bandit_arms 
                 WHERE organization_id = $1 AND arm_name = $2),
                $3, $4, NOW()
            )
            RETURNING id
            """,
            organization_id, arm_name, user_id, json.dumps(context)
        )
        
        return pull_id
```

---

## ⚙️ APRENDIZAJE DE CONFIGURACIONES

### Configuration Pattern Learner

```python
class ConfigurationPatternLearner:
    """
    Aprende patrones de configuración por contexto
    """
    
    def __init__(self, db, ml_model):
        self.db = db
        self.ml_model = ml_model
    
    async def learn_configuration_pattern(
        self,
        user_id: str,
        organization_id: str,
        rfx_data: dict,
        final_config: dict
    ):
        """
        Aprende patrón de configuración
        """
        # Extraer features del contexto
        features = self._extract_context_features(rfx_data)
        
        # Almacenar patrón
        await self.db.execute(
            """
            INSERT INTO configuration_patterns
                (user_id, organization_id, context_features, 
                 configuration, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            user_id, organization_id,
            json.dumps(features), json.dumps(final_config)
        )
    
    async def predict_configuration(
        self,
        user_id: str,
        organization_id: str,
        rfx_data: dict
    ) -> dict:
        """
        Predice configuración óptima basada en contexto
        """
        # Extraer features del contexto actual
        current_features = self._extract_context_features(rfx_data)
        
        # Obtener patrones históricos similares
        similar_patterns = await self._find_similar_patterns(
            user_id, organization_id, current_features
        )
        
        if not similar_patterns:
            # Usar configuración por defecto del usuario
            return await self._get_default_user_config(user_id, organization_id)
        
        # Agregar configuraciones similares
        predicted_config = self._aggregate_configurations(similar_patterns)
        
        return predicted_config
    
    def _extract_context_features(self, rfx_data: dict) -> dict:
        """
        Extrae features relevantes del contexto
        """
        return {
            'event_type': rfx_data.get('event_type'),
            'attendees': rfx_data.get('attendees', 0),
            'attendees_bucket': self._bucket_attendees(rfx_data.get('attendees', 0)),
            'num_products': len(rfx_data.get('products', [])),
            'total_quantity': sum(p.get('quantity', 0) for p in rfx_data.get('products', [])),
            'has_catering': any('catering' in p.get('category', '').lower() 
                               for p in rfx_data.get('products', [])),
            'is_corporate': rfx_data.get('event_type') == 'corporate',
            'day_of_week': datetime.now().strftime('%A'),
            'month': datetime.now().month,
            'is_holiday_season': datetime.now().month in [11, 12]
        }
    
    def _bucket_attendees(self, attendees: int) -> str:
        """Agrupa número de asistentes en buckets"""
        if attendees < 50:
            return 'small'
        elif attendees < 150:
            return 'medium'
        elif attendees < 300:
            return 'large'
        else:
            return 'xlarge'
    
    async def _find_similar_patterns(
        self,
        user_id: str,
        organization_id: str,
        features: dict
    ) -> List[dict]:
        """
        Encuentra patrones similares en historial
        """
        # Obtener todos los patrones del usuario
        patterns = await self.db.fetch(
            """
            SELECT context_features, configuration, created_at
            FROM configuration_patterns
            WHERE user_id = $1 AND organization_id = $2
            ORDER BY created_at DESC
            LIMIT 50
            """,
            user_id, organization_id
        )
        
        # Calcular similitud de cada patrón
        scored_patterns = []
        for pattern in patterns:
            pattern_features = json.loads(pattern['context_features'])
            similarity = self._calculate_feature_similarity(
                features, pattern_features
            )
            
            if similarity > 0.6:  # Threshold de similitud
                scored_patterns.append({
                    'configuration': json.loads(pattern['configuration']),
                    'similarity': similarity,
                    'age_days': (datetime.now() - pattern['created_at']).days
                })
        
        # Ordenar por similitud y recencia
        scored_patterns.sort(
            key=lambda x: x['similarity'] * (0.95 ** x['age_days']),
            reverse=True
        )
        
        return scored_patterns[:5]
    
    def _calculate_feature_similarity(
        self,
        features_a: dict,
        features_b: dict
    ) -> float:
        """
        Calcula similitud entre dos conjuntos de features
        """
        score = 0
        total_weight = 0
        
        # Pesos de importancia por feature
        weights = {
            'event_type': 3.0,
            'attendees_bucket': 2.0,
            'is_corporate': 2.0,
            'has_catering': 1.5,
            'num_products': 1.0,
            'month': 0.5
        }
        
        for feature, weight in weights.items():
            if feature in features_a and feature in features_b:
                if features_a[feature] == features_b[feature]:
                    score += weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0
    
    def _aggregate_configurations(
        self,
        patterns: List[dict]
    ) -> dict:
        """
        Agrega múltiples configuraciones en una predicción
        """
        if not patterns:
            return {}
        
        # Ponderar por similitud
        total_weight = sum(p['similarity'] for p in patterns)
        
        # Campos booleanos: mayoría ponderada
        coordination_enabled_weight = sum(
            p['similarity'] for p in patterns
            if p['configuration'].get('coordination_enabled')
        )
        
        taxes_enabled_weight = sum(
            p['similarity'] for p in patterns
            if p['configuration'].get('taxes_enabled')
        )
        
        # Campos numéricos: promedio ponderado
        coordination_rates = [
            (p['configuration'].get('coordination_rate', 0), p['similarity'])
            for p in patterns
            if p['configuration'].get('coordination_rate')
        ]
        
        tax_rates = [
            (p['configuration'].get('tax_rate', 0), p['similarity'])
            for p in patterns
            if p['configuration'].get('tax_rate')
        ]
        
        return {
            'coordination_enabled': coordination_enabled_weight > total_weight / 2,
            'coordination_rate': (
                sum(rate * weight for rate, weight in coordination_rates) /
                sum(weight for _, weight in coordination_rates)
                if coordination_rates else 0.18
            ),
            'taxes_enabled': taxes_enabled_weight > total_weight / 2,
            'tax_rate': (
                sum(rate * weight for rate, weight in tax_rates) /
                sum(weight for _, weight in tax_rates)
                if tax_rates else 0.16
            ),
            'confidence': min(len(patterns) / 5, 1.0)
        }
```

---

## 🔗 INTEGRACIÓN CON SISTEMA EXISTENTE

### Integration Points

```python
# ============================================
# 1. RFX PROCESSING - Capturar Interacciones
# ============================================

# En: backend/services/rfx_processor_service.py

class RFXProcessorService:
    def __init__(self, ..., learning_service):
        # ... existing code ...
        self.learning = learning_service
    
    async def process_rfx_case(self, rfx_input, files, user_id):
        # ... existing extraction logic ...
        
        # 🧠 LEARNING: Capturar creación de RFX
        await self.learning.capture_rfx_creation(
            user_id=user_id,
            organization_id=rfx_input.get('organization_id'),
            rfx_data={
                'products': extracted_products,
                'pricing_config': rfx_input.get('pricing_config'),
                'attendees': rfx_input.get('attendees'),
                'event_type': rfx_input.get('event_type')
            }
        )
        
        return rfx_processed

# ============================================
# 2. PRICING CALCULATION - Aplicar Aprendizaje
# ============================================

# En: backend/services/pricing_service.py

class PricingService:
    def __init__(self, ..., learning_service):
        # ... existing code ...
        self.learning = learning_service
    
    async def calculate_pricing(self, rfx_id, user_id, organization_id):
        # ... existing logic ...
        
        # 🧠 LEARNING: Obtener precios aprendidos
        for product in products:
            learned_price = await self.learning.get_learned_price(
                product_name=product['name'],
                quantity=product['quantity'],
                organization_id=organization_id,
                context={'event_type': rfx_data.get('event_type')}
            )
            
            if learned_price and learned_price != product['price']:
                logger.info(
                    f"💡 Learned price suggestion: {product['name']} "
                    f"${product['price']} → ${learned_price}"
                )
                # Opcionalmente aplicar o sugerir
                product['suggested_price'] = learned_price
        
        return pricing_result

# ============================================
# 3. PROPOSAL GENERATION - Recomendaciones
# ============================================

# En: backend/services/proposal_generator.py

class ProposalGenerator:
    def __init__(self, ..., learning_service):
        # ... existing code ...
        self.learning = learning_service
    
    async def generate_proposal(self, rfx_id, user_id, organization_id):
        # ... existing logic ...
        
        # 🧠 LEARNING: Obtener recomendaciones de productos
        current_products = [p['name'] for p in rfx_data['products']]
        recommendations = await self.learning.get_product_recommendations(
            current_products=current_products,
            organization_id=organization_id,
            k=5
        )
        
        if recommendations:
            logger.info(
                f"💡 Product recommendations: "
                f"{[r['product'] for r in recommendations]}"
            )
            # Agregar a metadata de propuesta
            proposal_metadata['recommendations'] = recommendations
        
        return proposal

# ============================================
# 4. USER CORRECTIONS - Aprender de Feedback
# ============================================

# Nuevo endpoint en: backend/api/learning.py

@router.post("/api/learning/corrections")
@jwt_required
async def submit_correction(
    correction_data: dict,
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(get_current_organization_id)
):
    """
    Endpoint para capturar correcciones del usuario
    
    Body:
    {
        "rfx_id": "uuid",
        "correction_type": "price" | "quantity" | "product",
        "product_name": "Tequeños",
        "old_value": 0.80,
        "new_value": 0.68,
        "context": {...}
    }
    """
    await learning_service.learn_from_correction(
        user_id=user_id,
        organization_id=organization_id,
        correction_data=correction_data
    )
    
    return {
        "status": "success",
        "message": "Correction learned successfully"
    }

# ============================================
# 5. PRICING CONFIG - Pre-llenar con Preferencias
# ============================================

# En: backend/api/pricing.py

@router.get("/api/pricing/config/<rfx_id>")
@jwt_required
async def get_pricing_config(
    rfx_id: str,
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(get_current_organization_id)
):
    # ... existing logic ...
    
    # 🧠 LEARNING: Obtener configuración sugerida
    if not existing_config:
        suggested_config = await learning_service.predict_pricing_config(
            user_id=user_id,
            organization_id=organization_id,
            rfx_data=rfx_data
        )
        
        if suggested_config.get('confidence', 0) > 0.7:
            logger.info(
                f"💡 Using learned pricing config "
                f"(confidence: {suggested_config['confidence']})"
            )
            return suggested_config
    
    return existing_config or default_config
```

### Database Migrations

```sql
-- ============================================
-- MIGRATION: Add Learning Tables
-- ============================================

-- User product preferences
CREATE TABLE IF NOT EXISTS user_product_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    product_name VARCHAR(255) NOT NULL,
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, product_name),
    INDEX idx_user_org (user_id, organization_id),
    INDEX idx_usage (usage_count DESC, last_used DESC)
);

-- User pricing config history
CREATE TABLE IF NOT EXISTS user_pricing_config_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    config_snapshot JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_user_created (user_id, created_at DESC)
);

-- User quantity patterns
CREATE TABLE IF NOT EXISTS user_quantity_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    product_name VARCHAR(255) NOT NULL,
    quantity_per_person FLOAT NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, product_name),
    INDEX idx_user_product (user_id, product_name)
);

-- Configuration patterns
CREATE TABLE IF NOT EXISTS configuration_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    context_features JSONB NOT NULL,
    configuration JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_org_created (organization_id, created_at DESC)
);

-- Bandit arms (ya definido en Part 2)
-- Bandit pulls (ya definido en Part 2)

-- Few-shot examples metadata (complementa vector store)
CREATE TABLE IF NOT EXISTS few_shot_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    example_type VARCHAR(50) NOT NULL, -- 'pricing', 'product', 'config'
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    quality_score FLOAT NOT NULL DEFAULT 0.5,
    usage_count INTEGER NOT NULL DEFAULT 0,
    success_rate FLOAT,
    vector_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,
    
    INDEX idx_org_type (organization_id, example_type),
    INDEX idx_quality (quality_score DESC)
);
```

---

## 📅 PLAN DE IMPLEMENTACIÓN

### Fase 1: Fundamentos (Semanas 1-2)

```
✅ SEMANA 1: Infraestructura Base
├─ Configurar vector store (Pinecone/Qdrant)
├─ Crear tablas de base de datos
├─ Implementar InteractionCaptureService
├─ Implementar event bus (Redis Streams)
└─ Setup de logging y métricas básicas

✅ SEMANA 2: Knowledge Graph
├─ Implementar ProductKnowledgeGraph
├─ Crear queries Cypher básicas
├─ Implementar aprendizaje de precios
└─ Testing de almacenamiento temporal
```

### Fase 2: Few-Shot Learning (Semanas 3-4)

```
✅ SEMANA 3: Vector Store & Embeddings
├─ Implementar PricingFewShotLearner
├─ Integrar modelo de embeddings
├─ Crear pipeline de almacenamiento de ejemplos
└─ Testing de búsqueda semántica

✅ SEMANA 4: Predicción & Inferencia
├─ Implementar InferenceEngine
├─ Integrar predicción de precios
├─ Crear API endpoints de predicción
└─ Testing end-to-end
```

### Fase 3: User Preferences (Semanas 5-6)

```
✅ SEMANA 5: Aprendizaje de Patrones
├─ Implementar UserPreferenceLearner
├─ Capturar preferencias de productos
├─ Aprender configuraciones de pricing
└─ Testing de agregación de patrones

✅ SEMANA 6: Contextual Bandit
├─ Implementar RFXStrategyBandit
├─ Configurar Thompson Sampling
├─ Integrar selección de estrategias
└─ Testing de optimización
```

### Fase 4: Integración (Semanas 7-8)

```
✅ SEMANA 7: Integración con Sistema Existente
├─ Modificar RFXProcessorService
├─ Modificar PricingService
├─ Modificar ProposalGenerator
└─ Crear endpoints de learning API

✅ SEMANA 8: Testing & Refinamiento
├─ Testing de integración completo
├─ Optimización de performance
├─ Ajuste de parámetros
└─ Documentación de APIs
```

### Fase 5: Monitoring & Optimization (Semanas 9-10)

```
✅ SEMANA 9: Observabilidad
├─ Configurar dashboards de Grafana
├─ Implementar alertas críticas
├─ Setup de A/B testing framework
└─ Métricas de calidad de aprendizaje

✅ SEMANA 10: Optimización
├─ Análisis de performance
├─ Tuning de hiperparámetros
├─ Optimización de queries
└─ Preparación para producción
```

---

## 🎯 MÉTRICAS DE ÉXITO

### KPIs Principales

```python
class LearningSuccessMetrics:
    """
    Métricas para evaluar éxito del sistema de aprendizaje
    """
    
    # ============================================
    # ACCURACY METRICS
    # ============================================
    
    @staticmethod
    def price_prediction_accuracy():
        """
        % de predicciones de precio dentro de ±10% del precio final
        Target: > 80%
        """
        return """
        SELECT 
            COUNT(CASE WHEN ABS(predicted_price - final_price) / final_price < 0.1 
                  THEN 1 END) * 100.0 / COUNT(*) as accuracy_pct
        FROM price_predictions
        WHERE created_at > NOW() - INTERVAL '7 days'
        """
    
    @staticmethod
    def product_recommendation_acceptance():
        """
        % de productos recomendados que el usuario acepta
        Target: > 40%
        """
        return """
        SELECT 
            COUNT(CASE WHEN accepted = true THEN 1 END) * 100.0 / COUNT(*) 
            as acceptance_rate
        FROM product_recommendations
        WHERE created_at > NOW() - INTERVAL '7 days'
        """
    
    # ============================================
    # EFFICIENCY METRICS
    # ============================================
    
    @staticmethod
    def time_saved_per_rfx():
        """
        Tiempo ahorrado por RFX gracias a sugerencias
        Target: > 5 minutos
        """
        return """
        SELECT 
            AVG(baseline_time_seconds - actual_time_seconds) / 60 
            as minutes_saved
        FROM rfx_processing_times
        WHERE used_learning_suggestions = true
          AND created_at > NOW() - INTERVAL '7 days'
        """
    
    @staticmethod
    def correction_rate_reduction():
        """
        Reducción en tasa de correcciones vs baseline
        Target: -30% vs baseline
        """
        return """
        SELECT 
            (baseline_correction_rate - current_correction_rate) * 100.0 
            / baseline_correction_rate as reduction_pct
        FROM (
            SELECT 
                (SELECT COUNT(*) FROM corrections 
                 WHERE created_at < '2026-01-01') * 1.0 / 
                (SELECT COUNT(*) FROM rfx_v2 
                 WHERE created_at < '2026-01-01') as baseline_correction_rate,
                (SELECT COUNT(*) FROM corrections 
                 WHERE created_at > '2026-01-01') * 1.0 / 
                (SELECT COUNT(*) FROM rfx_v2 
                 WHERE created_at > '2026-01-01') as current_correction_rate
        ) rates
        """
    
    # ============================================
    # QUALITY METRICS
    # ============================================
    
    @staticmethod
    def user_satisfaction_score():
        """
        Score promedio de satisfacción del usuario
        Target: > 4.0 / 5.0
        """
        return """
        SELECT AVG(rating) as avg_satisfaction
        FROM user_feedback
        WHERE feedback_type = 'learning_suggestion'
          AND created_at > NOW() - INTERVAL '7 days'
        """
    
    @staticmethod
    def learning_confidence_trend():
        """
        Tendencia de confianza de predicciones (debe aumentar)
        Target: Pendiente positiva
        """
        return """
        SELECT 
            DATE_TRUNC('day', created_at) as date,
            AVG(confidence) as avg_confidence
        FROM predictions
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', created_at)
        ORDER BY date
        """
```

---

## 🚀 PRÓXIMOS PASOS

### Inmediatos (Post-Implementación)

1. **Recolección de Datos Históricos**
   - Migrar datos existentes de RFX a formato de aprendizaje
   - Generar ejemplos iniciales para Few-Shot Learning
   - Poblar Knowledge Graph con relaciones existentes

2. **Calibración Inicial**
   - Ajustar thresholds de confianza
   - Tuning de parámetros de bandit
   - Optimización de búsqueda semántica

3. **Rollout Gradual**
   - Beta con usuarios seleccionados
   - A/B testing vs sistema actual
   - Recolección de feedback

### Futuro (Mejoras Avanzadas)

1. **Active Learning**
   - Sistema solicita feedback en casos de baja confianza
   - Priorización de ejemplos más valiosos para aprender

2. **Transfer Learning Cross-Organization**
   - Aprender patrones generales de la industria
   - Mantener privacidad de datos específicos

3. **Reinforcement Learning**
   - Optimización end-to-end del proceso RFX
   - Aprendizaje de secuencias óptimas de acciones

4. **Explainability**
   - Visualización de por qué el sistema sugiere X
   - Trazabilidad de decisiones de aprendizaje

---

**FIN DE LA DOCUMENTACIÓN**

**Archivos Relacionados:**
- `AI_LEARNING_SYSTEM_PART1_THEORY.md` - Fundamentos teóricos
- `AI_LEARNING_SYSTEM_PART2_IMPLEMENTATION.md` - Arquitectura técnica
- `AI_LEARNING_SYSTEM_PART3_RFX_IMPLEMENTATION.md` - Este documento

**Estado:** ✅ DOCUMENTACIÓN COMPLETA - LISTO PARA IMPLEMENTACIÓN
