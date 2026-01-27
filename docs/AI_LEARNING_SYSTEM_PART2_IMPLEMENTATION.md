# 🏗️ AI LEARNING SYSTEM - PARTE 2: ARQUITECTURA DE IMPLEMENTACIÓN

**Versión:** 1.0  
**Fecha:** 26 de Enero, 2026  
**Propósito:** Diseño técnico y arquitectura de implementación del sistema de aprendizaje

---

## 📋 CONTENIDO

1. [Arquitectura General](#arquitectura-general)
2. [Componentes Core](#componentes-core)
3. [Data Pipeline](#data-pipeline)
4. [Storage Layer](#storage-layer)
5. [API Design](#api-design)
6. [Monitoring & Observability](#monitoring--observability)

---

## 🏛️ ARQUITECTURA GENERAL

### Visión de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI LEARNING SYSTEM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐      ┌────────────────┐      ┌──────────────┐  │
│  │   USER INPUT   │─────▶│  INTERACTION   │─────▶│   LEARNING   │  │
│  │  (Feedback)    │      │   CAPTURE      │      │   ENGINE     │  │
│  └────────────────┘      └────────────────┘      └──────────────┘  │
│                                 │                        │           │
│                                 ▼                        ▼           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    KNOWLEDGE LAYER                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │  Temporal    │  │   Vector     │  │   Interaction    │  │  │
│  │  │  Knowledge   │  │   Store      │  │   History        │  │  │
│  │  │  Graph       │  │  (Examples)  │  │   (Events)       │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 │                                    │
│                                 ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    INFERENCE ENGINE                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │  Few-Shot    │  │  Contextual  │  │  Collaborative   │  │  │
│  │  │  Retrieval   │  │  Bandit      │  │  Filtering       │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 │                                    │
│                                 ▼                                    │
│  ┌────────────────┐      ┌────────────────┐      ┌──────────────┐  │
│  │   ENHANCED     │◀─────│  PERSONALIZED  │◀─────│   CONTEXT    │  │
│  │   RESPONSE     │      │   PREDICTION   │      │   BUILDER    │  │
│  └────────────────┘      └────────────────┘      └──────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Principios de Diseño

#### 1. **Separation of Concerns**
```
📊 Data Layer      → Almacenamiento y persistencia
🧠 Learning Layer  → Algoritmos y entrenamiento
🎯 Inference Layer → Predicción y recomendación
📡 API Layer       → Exposición de funcionalidad
```

#### 2. **Event-Driven Architecture**
```python
# Cada interacción genera eventos
class InteractionEvent:
    event_type: str      # "feedback", "correction", "selection"
    user_id: str
    organization_id: str
    context: dict        # Estado del sistema al momento
    action: dict         # Qué hizo el usuario
    outcome: dict        # Resultado de la acción
    timestamp: datetime
```

#### 3. **Multi-Tenant Isolation**
```
Organization A     Organization B     Organization C
     │                   │                   │
     ├─ Users            ├─ Users            ├─ Users
     ├─ Knowledge        ├─ Knowledge        ├─ Knowledge
     ├─ Examples         ├─ Examples         ├─ Examples
     └─ Preferences      └─ Preferences      └─ Preferences
     
     ❌ NO CROSS-CONTAMINATION
```

---

## 🔧 COMPONENTES CORE

### 1. Interaction Capture Service

**Responsabilidad:** Capturar y normalizar todas las interacciones del usuario.

```python
class InteractionCaptureService:
    """
    Servicio central para capturar interacciones de usuario
    """
    
    def __init__(self, event_bus, validator):
        self.event_bus = event_bus
        self.validator = validator
        self.interaction_types = {
            'feedback': FeedbackInteraction,
            'correction': CorrectionInteraction,
            'selection': SelectionInteraction,
            'rejection': RejectionInteraction
        }
    
    async def capture_interaction(
        self,
        interaction_type: str,
        user_id: str,
        organization_id: str,
        payload: dict
    ) -> InteractionEvent:
        """
        Captura y valida una interacción
        
        Args:
            interaction_type: Tipo de interacción (feedback, correction, etc.)
            user_id: ID del usuario
            organization_id: ID de la organización
            payload: Datos específicos de la interacción
        
        Returns:
            InteractionEvent normalizado
        """
        # 1. Validar payload
        interaction_class = self.interaction_types[interaction_type]
        validated_payload = self.validator.validate(
            payload, 
            schema=interaction_class.schema
        )
        
        # 2. Crear evento
        event = InteractionEvent(
            event_type=interaction_type,
            user_id=user_id,
            organization_id=organization_id,
            context=self._capture_context(),
            action=validated_payload,
            outcome=None,  # Se llena después
            timestamp=datetime.utcnow()
        )
        
        # 3. Publicar al event bus
        await self.event_bus.publish('interaction.captured', event)
        
        # 4. Persistir
        await self._persist_interaction(event)
        
        return event
    
    def _capture_context(self) -> dict:
        """Captura el contexto completo del sistema"""
        return {
            'session_id': get_current_session_id(),
            'request_id': get_current_request_id(),
            'user_agent': get_user_agent(),
            'feature_flags': get_active_feature_flags(),
            'ab_tests': get_active_ab_tests()
        }
```

### 2. Learning Engine

**Responsabilidad:** Procesar interacciones y actualizar modelos de conocimiento.

```python
class LearningEngine:
    """
    Motor de aprendizaje que procesa eventos y actualiza conocimiento
    """
    
    def __init__(
        self,
        knowledge_graph: TemporalKnowledgeGraph,
        vector_store: VectorStore,
        bandit_optimizer: ContextualBandit,
        collab_filter: CollaborativeFilteringEngine
    ):
        self.kg = knowledge_graph
        self.vector_store = vector_store
        self.bandit = bandit_optimizer
        self.collab_filter = collab_filter
        
        # Subscribers a eventos
        self.event_handlers = {
            'interaction.captured': self.process_interaction,
            'feedback.received': self.process_feedback,
            'correction.applied': self.process_correction
        }
    
    async def process_interaction(self, event: InteractionEvent):
        """
        Pipeline de procesamiento de interacciones
        """
        logger.info(f"Processing interaction: {event.event_type}")
        
        # 1. Extraer entidades y relaciones
        entities = await self._extract_entities(event)
        relations = await self._extract_relations(event, entities)
        
        # 2. Actualizar Knowledge Graph
        await self._update_knowledge_graph(entities, relations, event)
        
        # 3. Crear ejemplo para Few-Shot Learning
        if self._is_valuable_example(event):
            await self._store_as_example(event)
        
        # 4. Actualizar Collaborative Filtering
        await self._update_user_product_matrix(event)
        
        # 5. Actualizar Contextual Bandit
        if event.outcome:
            await self._update_bandit_reward(event)
        
        logger.info(f"✅ Interaction processed: {event.event_type}")
    
    async def _extract_entities(self, event: InteractionEvent) -> List[Entity]:
        """
        Extrae entidades del evento usando NER o LLM
        """
        # Ejemplo: "Usuario corrigió precio de Tequeños de $0.80 a $0.68"
        # Entidades: Product(Tequeños), Price($0.68), User(user_id)
        
        extraction_prompt = f"""
        Extract entities from this interaction:
        
        Event Type: {event.event_type}
        Action: {event.action}
        
        Return entities in JSON format:
        {{
            "entities": [
                {{"type": "product", "name": "...", "id": "..."}},
                {{"type": "price", "amount": ..., "currency": "..."}},
                ...
            ]
        }}
        """
        
        result = await self.llm.extract_structured(extraction_prompt)
        return [Entity(**e) for e in result['entities']]
    
    async def _update_knowledge_graph(
        self,
        entities: List[Entity],
        relations: List[Relation],
        event: InteractionEvent
    ):
        """
        Actualiza el grafo de conocimiento temporal
        """
        for entity in entities:
            await self.kg.upsert_entity(
                entity,
                t_occurred=event.timestamp,
                t_ingested=datetime.utcnow(),
                source=f"user:{event.user_id}"
            )
        
        for relation in relations:
            await self.kg.upsert_relation(
                relation,
                t_occurred=event.timestamp,
                t_ingested=datetime.utcnow(),
                confidence=self._calculate_confidence(event)
            )
    
    def _is_valuable_example(self, event: InteractionEvent) -> bool:
        """
        Determina si la interacción es valiosa como ejemplo
        """
        # Criterios:
        # 1. Feedback positivo del usuario
        # 2. Corrección aplicada (indica patrón a aprender)
        # 3. Selección entre múltiples opciones
        # 4. No es ruido (validación de calidad)
        
        if event.event_type == 'correction':
            return True
        
        if event.event_type == 'feedback':
            return event.action.get('rating', 0) >= 4
        
        if event.event_type == 'selection':
            return event.action.get('confidence', 0) >= 0.7
        
        return False
    
    async def _store_as_example(self, event: InteractionEvent):
        """
        Almacena la interacción como ejemplo para Few-Shot Learning
        """
        example = {
            'input': event.context.get('query'),
            'output': event.action.get('result'),
            'metadata': {
                'user_id': event.user_id,
                'organization_id': event.organization_id,
                'timestamp': event.timestamp,
                'quality_score': self._calculate_quality_score(event)
            }
        }
        
        # Generar embedding
        embedding = await self.embedding_model.encode(
            f"{example['input']} -> {example['output']}"
        )
        
        # Almacenar en vector store
        await self.vector_store.add(
            id=f"example_{event.user_id}_{event.timestamp}",
            embedding=embedding,
            metadata=example,
            filters={
                'organization_id': event.organization_id,
                'type': 'few_shot_example'
            }
        )
```

### 3. Inference Engine

**Responsabilidad:** Generar predicciones y recomendaciones personalizadas.

```python
class InferenceEngine:
    """
    Motor de inferencia que combina múltiples técnicas
    """
    
    def __init__(
        self,
        few_shot_engine: FewShotLearningEngine,
        knowledge_graph: TemporalKnowledgeGraph,
        bandit: ContextualBandit,
        collab_filter: CollaborativeFilteringEngine
    ):
        self.few_shot = few_shot_engine
        self.kg = knowledge_graph
        self.bandit = bandit
        self.collab_filter = collab_filter
    
    async def predict(
        self,
        query: str,
        user_id: str,
        organization_id: str,
        context: dict
    ) -> PredictionResult:
        """
        Genera predicción personalizada usando múltiples técnicas
        """
        # 1. Recuperar ejemplos relevantes (Few-Shot)
        examples = await self.few_shot.retrieve_examples(
            query=query,
            k=5,
            filters={'organization_id': organization_id}
        )
        
        # 2. Consultar Knowledge Graph
        kg_context = await self.kg.query_relevant_knowledge(
            query=query,
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
        
        # 3. Obtener recomendaciones (Collaborative Filtering)
        recommendations = await self.collab_filter.recommend_products(
            user_id=user_id,
            k=10
        )
        
        # 4. Seleccionar estrategia (Contextual Bandit)
        strategy = await self.bandit.select_arm(
            context={
                'user_id': user_id,
                'query_type': self._classify_query(query),
                'has_history': len(examples) > 0,
                **context
            }
        )
        
        # 5. Construir prompt enriquecido
        enriched_prompt = self._build_enriched_prompt(
            query=query,
            examples=examples,
            kg_context=kg_context,
            recommendations=recommendations,
            strategy=strategy
        )
        
        # 6. Generar predicción
        prediction = await self.llm.generate(enriched_prompt)
        
        # 7. Post-procesamiento
        result = PredictionResult(
            prediction=prediction,
            confidence=self._calculate_confidence(prediction, examples),
            strategy_used=strategy,
            examples_used=len(examples),
            kg_facts_used=len(kg_context),
            recommendations=recommendations[:3],
            metadata={
                'user_id': user_id,
                'organization_id': organization_id,
                'timestamp': datetime.utcnow()
            }
        )
        
        return result
    
    def _build_enriched_prompt(
        self,
        query: str,
        examples: List[dict],
        kg_context: List[dict],
        recommendations: List[str],
        strategy: str
    ) -> str:
        """
        Construye prompt enriquecido con todo el contexto
        """
        prompt_parts = []
        
        # System message
        prompt_parts.append(
            "You are an AI assistant specialized in RFX automation. "
            "Use the following context to provide accurate, personalized responses."
        )
        
        # Knowledge Graph context
        if kg_context:
            prompt_parts.append("\n## Relevant Knowledge:")
            for fact in kg_context:
                prompt_parts.append(
                    f"- {fact['subject']} {fact['relation']} {fact['object']} "
                    f"(as of {fact['timestamp']})"
                )
        
        # Few-Shot examples
        if examples:
            prompt_parts.append("\n## Similar Past Interactions:")
            for i, ex in enumerate(examples, 1):
                prompt_parts.append(
                    f"\nExample {i}:\n"
                    f"Input: {ex['input']}\n"
                    f"Output: {ex['output']}"
                )
        
        # Recommendations
        if recommendations:
            prompt_parts.append(
                f"\n## Recommended Products: {', '.join(recommendations)}"
            )
        
        # Strategy-specific instructions
        strategy_instructions = {
            'precise': "Prioritize accuracy over speed. Use all available context.",
            'fast': "Provide quick response using most relevant examples only.",
            'balanced': "Balance accuracy and speed appropriately."
        }
        prompt_parts.append(
            f"\n## Strategy: {strategy_instructions.get(strategy, '')}"
        )
        
        # User query
        prompt_parts.append(f"\n## User Query:\n{query}\n\nResponse:")
        
        return "\n".join(prompt_parts)
```

### 4. Context Builder

**Responsabilidad:** Construir contexto rico para cada predicción.

```python
class ContextBuilder:
    """
    Construye contexto enriquecido para inferencia
    """
    
    def __init__(
        self,
        user_service,
        organization_service,
        history_service
    ):
        self.user_service = user_service
        self.org_service = organization_service
        self.history_service = history_service
    
    async def build_context(
        self,
        user_id: str,
        organization_id: str,
        query: str
    ) -> dict:
        """
        Construye contexto completo para una query
        """
        # 1. User profile
        user_profile = await self.user_service.get_profile(user_id)
        
        # 2. Organization preferences
        org_preferences = await self.org_service.get_preferences(organization_id)
        
        # 3. Recent history
        recent_interactions = await self.history_service.get_recent(
            user_id=user_id,
            limit=20
        )
        
        # 4. User patterns
        user_patterns = await self._extract_user_patterns(user_id)
        
        # 5. Temporal context
        temporal_context = self._get_temporal_context()
        
        return {
            'user': {
                'id': user_id,
                'role': user_profile.get('role'),
                'preferences': user_profile.get('preferences', {}),
                'expertise_level': self._infer_expertise_level(recent_interactions)
            },
            'organization': {
                'id': organization_id,
                'industry': org_preferences.get('industry'),
                'size': org_preferences.get('size'),
                'preferences': org_preferences
            },
            'history': {
                'recent_interactions': recent_interactions[:5],
                'total_interactions': len(recent_interactions),
                'patterns': user_patterns
            },
            'temporal': temporal_context,
            'query': {
                'text': query,
                'type': self._classify_query_type(query),
                'entities': await self._extract_query_entities(query)
            }
        }
    
    async def _extract_user_patterns(self, user_id: str) -> dict:
        """
        Extrae patrones de comportamiento del usuario
        """
        interactions = await self.history_service.get_all(user_id)
        
        patterns = {
            'preferred_products': self._find_frequent_products(interactions),
            'price_sensitivity': self._calculate_price_sensitivity(interactions),
            'typical_quantities': self._calculate_typical_quantities(interactions),
            'preferred_suppliers': self._find_preferred_suppliers(interactions),
            'time_patterns': self._analyze_time_patterns(interactions)
        }
        
        return patterns
    
    def _get_temporal_context(self) -> dict:
        """
        Contexto temporal (día de la semana, hora, temporada, etc.)
        """
        now = datetime.now()
        
        return {
            'timestamp': now,
            'day_of_week': now.strftime('%A'),
            'hour': now.hour,
            'is_business_hours': 9 <= now.hour <= 17,
            'month': now.month,
            'quarter': (now.month - 1) // 3 + 1,
            'is_holiday_season': now.month in [11, 12]
        }
```

---

## 📊 DATA PIPELINE

### Event Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        EVENT PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  USER ACTION                                                     │
│       ↓                                                          │
│  ┌─────────────────┐                                            │
│  │ Interaction API │                                            │
│  └────────┬────────┘                                            │
│           ↓                                                      │
│  ┌─────────────────┐                                            │
│  │  Event Bus      │ ← Redis Streams / Kafka                   │
│  └────────┬────────┘                                            │
│           ↓                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              EVENT PROCESSORS (Async)                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │   │
│  │  │   KG     │  │  Vector  │  │  Bandit  │  │ Collab │ │   │
│  │  │ Updater  │  │  Store   │  │ Updater  │  │ Filter │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│           ↓                                                      │
│  ┌─────────────────┐                                            │
│  │  Storage Layer  │                                            │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline Implementation

```python
class EventPipeline:
    """
    Pipeline asíncrono para procesamiento de eventos
    """
    
    def __init__(self, event_bus, processors):
        self.event_bus = event_bus
        self.processors = processors
        self.retry_policy = RetryPolicy(max_retries=3, backoff='exponential')
    
    async def start(self):
        """Inicia el pipeline de procesamiento"""
        # Suscribirse a eventos
        await self.event_bus.subscribe(
            'interaction.*',
            self.process_event
        )
        
        logger.info("✅ Event pipeline started")
    
    async def process_event(self, event: InteractionEvent):
        """
        Procesa un evento a través de todos los procesadores
        """
        correlation_id = event.context.get('request_id')
        
        logger.info(
            f"📥 Processing event: {event.event_type}",
            extra={'correlation_id': correlation_id}
        )
        
        # Procesar en paralelo cuando sea posible
        tasks = []
        for processor in self.processors:
            if processor.can_process(event):
                task = self._process_with_retry(processor, event)
                tasks.append(task)
        
        # Esperar a que todos completen
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Manejar errores
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.error(
                f"❌ {len(errors)} processors failed",
                extra={'correlation_id': correlation_id, 'errors': errors}
            )
            # Enviar a dead letter queue
            await self._send_to_dlq(event, errors)
        else:
            logger.info(
                f"✅ Event processed successfully",
                extra={'correlation_id': correlation_id}
            )
    
    async def _process_with_retry(
        self,
        processor,
        event: InteractionEvent
    ):
        """Procesa con política de reintentos"""
        for attempt in range(self.retry_policy.max_retries):
            try:
                return await processor.process(event)
            except Exception as e:
                if attempt == self.retry_policy.max_retries - 1:
                    raise
                
                wait_time = self.retry_policy.calculate_backoff(attempt)
                logger.warning(
                    f"⚠️ Processor {processor.name} failed, retrying in {wait_time}s",
                    extra={'attempt': attempt + 1, 'error': str(e)}
                )
                await asyncio.sleep(wait_time)
```

---

## 💾 STORAGE LAYER

### Database Schema

```sql
-- ============================================
-- INTERACTION HISTORY
-- ============================================
CREATE TABLE interaction_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Context
    context JSONB NOT NULL,
    action JSONB NOT NULL,
    outcome JSONB,
    
    -- Metadata
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    
    -- Indexing
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_user_timestamp (user_id, timestamp DESC),
    INDEX idx_org_timestamp (organization_id, timestamp DESC),
    INDEX idx_event_type (event_type),
    INDEX idx_request_id (request_id)
);

-- ============================================
-- FEW-SHOT EXAMPLES (Vector Store Metadata)
-- ============================================
CREATE TABLE few_shot_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Example data
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    
    -- Quality metrics
    quality_score FLOAT NOT NULL DEFAULT 0.5,
    usage_count INTEGER NOT NULL DEFAULT 0,
    success_rate FLOAT,
    
    -- Metadata
    source_event_id UUID REFERENCES interaction_events(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,
    
    -- Vector store reference
    vector_id VARCHAR(255) UNIQUE,
    
    INDEX idx_org_quality (organization_id, quality_score DESC),
    INDEX idx_user_created (user_id, created_at DESC)
);

-- ============================================
-- KNOWLEDGE GRAPH (Temporal Edges)
-- ============================================
CREATE TABLE kg_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Entity data
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    properties JSONB NOT NULL,
    
    -- Temporal
    t_created TIMESTAMP NOT NULL DEFAULT NOW(),
    t_valid TIMESTAMP NOT NULL DEFAULT NOW(),
    t_invalid TIMESTAMP,
    
    -- Source
    source VARCHAR(255),
    confidence FLOAT NOT NULL DEFAULT 1.0,
    
    UNIQUE(organization_id, entity_type, entity_id, t_valid),
    INDEX idx_org_type (organization_id, entity_type),
    INDEX idx_temporal (t_valid, t_invalid)
);

CREATE TABLE kg_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Relation
    source_entity_id UUID NOT NULL REFERENCES kg_entities(id),
    target_entity_id UUID NOT NULL REFERENCES kg_entities(id),
    relation_type VARCHAR(100) NOT NULL,
    properties JSONB,
    
    -- Temporal (bi-temporal)
    t_occurred TIMESTAMP NOT NULL,
    t_ingested TIMESTAMP NOT NULL DEFAULT NOW(),
    t_valid TIMESTAMP NOT NULL DEFAULT NOW(),
    t_invalid TIMESTAMP,
    
    -- Source
    source VARCHAR(255),
    confidence FLOAT NOT NULL DEFAULT 1.0,
    
    INDEX idx_source_entity (source_entity_id),
    INDEX idx_target_entity (target_entity_id),
    INDEX idx_relation_type (relation_type),
    INDEX idx_temporal (t_valid, t_invalid)
);

-- ============================================
-- CONTEXTUAL BANDIT STATE
-- ============================================
CREATE TABLE bandit_arms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Arm definition
    arm_name VARCHAR(100) NOT NULL,
    arm_config JSONB NOT NULL,
    
    -- Thompson Sampling parameters
    alpha INTEGER NOT NULL DEFAULT 1,
    beta INTEGER NOT NULL DEFAULT 1,
    
    -- Metrics
    total_pulls INTEGER NOT NULL DEFAULT 0,
    total_rewards FLOAT NOT NULL DEFAULT 0,
    avg_reward FLOAT,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(organization_id, arm_name),
    INDEX idx_org_updated (organization_id, updated_at DESC)
);

CREATE TABLE bandit_pulls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arm_id UUID NOT NULL REFERENCES bandit_arms(id),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Context
    context JSONB NOT NULL,
    
    -- Outcome
    reward FLOAT,
    feedback JSONB,
    
    -- Metadata
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_arm_timestamp (arm_id, timestamp DESC),
    INDEX idx_user_timestamp (user_id, timestamp DESC)
);

-- ============================================
-- COLLABORATIVE FILTERING
-- ============================================
CREATE TABLE user_product_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    product_id UUID NOT NULL REFERENCES products(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Interaction type
    interaction_type VARCHAR(50) NOT NULL, -- 'view', 'select', 'purchase', 'reject'
    
    -- Implicit rating (derived from interactions)
    implicit_rating FLOAT NOT NULL DEFAULT 0,
    
    -- Metadata
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    context JSONB,
    
    INDEX idx_user_product (user_id, product_id),
    INDEX idx_product_rating (product_id, implicit_rating DESC),
    INDEX idx_org_timestamp (organization_id, timestamp DESC)
);

CREATE TABLE user_embeddings (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Embedding vector (stored as array)
    embedding FLOAT[] NOT NULL,
    embedding_dim INTEGER NOT NULL,
    
    -- Metadata
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1,
    
    INDEX idx_org (organization_id)
);

CREATE TABLE product_embeddings (
    product_id UUID PRIMARY KEY REFERENCES products(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    -- Embedding vector
    embedding FLOAT[] NOT NULL,
    embedding_dim INTEGER NOT NULL,
    
    -- Metadata
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1,
    
    INDEX idx_org (organization_id)
);
```

### Vector Store Integration

```python
class VectorStoreManager:
    """
    Gestiona almacenamiento vectorial para Few-Shot Learning
    """
    
    def __init__(self, vector_db):
        # Opciones: Pinecone, Weaviate, Qdrant, Chroma
        self.vector_db = vector_db
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def store_example(
        self,
        example_id: str,
        input_text: str,
        output_text: str,
        metadata: dict
    ):
        """Almacena ejemplo con su embedding"""
        # Generar embedding
        text = f"Input: {input_text}\nOutput: {output_text}"
        embedding = self.embedding_model.encode(text)
        
        # Almacenar
        await self.vector_db.upsert(
            id=example_id,
            vector=embedding.tolist(),
            metadata={
                'input': input_text,
                'output': output_text,
                **metadata
            }
        )
    
    async def search_similar_examples(
        self,
        query: str,
        organization_id: str,
        k: int = 5
    ) -> List[dict]:
        """Busca ejemplos similares"""
        # Generar embedding del query
        query_embedding = self.embedding_model.encode(query)
        
        # Búsqueda
        results = await self.vector_db.query(
            vector=query_embedding.tolist(),
            filter={'organization_id': organization_id},
            top_k=k,
            include_metadata=True
        )
        
        return [
            {
                'id': r.id,
                'score': r.score,
                'input': r.metadata['input'],
                'output': r.metadata['output'],
                'metadata': r.metadata
            }
            for r in results
        ]
```

---

## 🔌 API DESIGN

### REST Endpoints

```python
# ============================================
# INTERACTION CAPTURE API
# ============================================

@router.post("/api/learning/interactions")
@jwt_required
async def capture_interaction(
    interaction_type: str,
    payload: dict,
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(get_current_organization_id)
):
    """
    Captura una interacción del usuario
    
    Body:
    {
        "interaction_type": "feedback" | "correction" | "selection" | "rejection",
        "payload": {
            // Específico al tipo de interacción
        }
    }
    """
    event = await interaction_service.capture_interaction(
        interaction_type=interaction_type,
        user_id=user_id,
        organization_id=organization_id,
        payload=payload
    )
    
    return {
        "status": "success",
        "event_id": event.id,
        "message": "Interaction captured successfully"
    }

# ============================================
# PREDICTION API
# ============================================

@router.post("/api/learning/predict")
@jwt_required
async def get_prediction(
    query: str,
    context: dict = None,
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(get_current_organization_id)
):
    """
    Genera predicción personalizada
    
    Body:
    {
        "query": "Estimate price for Tequeños (200 units)",
        "context": {
            "event_type": "corporate_event",
            "date": "2026-02-15",
            ...
        }
    }
    """
    # Construir contexto completo
    full_context = await context_builder.build_context(
        user_id=user_id,
        organization_id=organization_id,
        query=query
    )
    
    if context:
        full_context.update(context)
    
    # Generar predicción
    result = await inference_engine.predict(
        query=query,
        user_id=user_id,
        organization_id=organization_id,
        context=full_context
    )
    
    return {
        "status": "success",
        "prediction": result.prediction,
        "confidence": result.confidence,
        "metadata": {
            "strategy_used": result.strategy_used,
            "examples_used": result.examples_used,
            "kg_facts_used": result.kg_facts_used,
            "recommendations": result.recommendations
        }
    }

# ============================================
# FEEDBACK API
# ============================================

@router.post("/api/learning/feedback")
@jwt_required
async def submit_feedback(
    prediction_id: str,
    feedback_type: str,
    rating: int = None,
    correction: dict = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Envía feedback sobre una predicción
    
    Body:
    {
        "prediction_id": "uuid",
        "feedback_type": "rating" | "correction" | "acceptance",
        "rating": 1-5,  // opcional
        "correction": {  // opcional
            "field": "price",
            "old_value": 0.80,
            "new_value": 0.68,
            "reason": "Bulk discount applied"
        }
    }
    """
    await feedback_service.process_feedback(
        prediction_id=prediction_id,
        user_id=user_id,
        feedback_type=feedback_type,
        rating=rating,
        correction=correction
    )
    
    return {
        "status": "success",
        "message": "Feedback received and learning updated"
    }

# ============================================
# ANALYTICS API
# ============================================

@router.get("/api/learning/analytics")
@jwt_required
async def get_learning_analytics(
    organization_id: str = Depends(get_current_organization_id),
    time_range: str = "7d"
):
    """
    Obtiene métricas de aprendizaje
    """
    analytics = await analytics_service.get_metrics(
        organization_id=organization_id,
        time_range=time_range
    )
    
    return {
        "status": "success",
        "data": {
            "total_interactions": analytics.total_interactions,
            "learning_rate": analytics.learning_rate,
            "accuracy_improvement": analytics.accuracy_improvement,
            "user_satisfaction": analytics.user_satisfaction,
            "top_learned_patterns": analytics.top_patterns,
            "bandit_performance": analytics.bandit_stats,
            "example_quality": analytics.example_quality_stats
        }
    }
```

---

## 📈 MONITORING & OBSERVABILITY

### Key Metrics

```python
class LearningMetrics:
    """
    Métricas clave del sistema de aprendizaje
    """
    
    # ============================================
    # INTERACTION METRICS
    # ============================================
    
    @staticmethod
    def track_interaction_captured(event_type: str, organization_id: str):
        """Contador de interacciones capturadas"""
        metrics.increment(
            'learning.interactions.captured',
            tags={
                'event_type': event_type,
                'organization_id': organization_id
            }
        )
    
    @staticmethod
    def track_processing_time(event_type: str, duration_ms: float):
        """Latencia de procesamiento"""
        metrics.histogram(
            'learning.processing.duration_ms',
            duration_ms,
            tags={'event_type': event_type}
        )
    
    # ============================================
    # PREDICTION METRICS
    # ============================================
    
    @staticmethod
    def track_prediction_generated(strategy: str, confidence: float):
        """Predicciones generadas"""
        metrics.increment(
            'learning.predictions.generated',
            tags={'strategy': strategy}
        )
        metrics.histogram(
            'learning.predictions.confidence',
            confidence,
            tags={'strategy': strategy}
        )
    
    @staticmethod
    def track_prediction_accuracy(was_correct: bool, strategy: str):
        """Precisión de predicciones"""
        metrics.increment(
            'learning.predictions.accuracy',
            tags={
                'correct': str(was_correct),
                'strategy': strategy
            }
        )
    
    # ============================================
    # LEARNING METRICS
    # ============================================
    
    @staticmethod
    def track_example_stored(quality_score: float):
        """Ejemplos almacenados"""
        metrics.increment('learning.examples.stored')
        metrics.histogram(
            'learning.examples.quality_score',
            quality_score
        )
    
    @staticmethod
    def track_kg_update(entity_count: int, relation_count: int):
        """Actualizaciones del Knowledge Graph"""
        metrics.increment('learning.kg.updates')
        metrics.gauge('learning.kg.entities', entity_count)
        metrics.gauge('learning.kg.relations', relation_count)
    
    @staticmethod
    def track_bandit_pull(arm: str, reward: float):
        """Pulls del Contextual Bandit"""
        metrics.increment(
            'learning.bandit.pulls',
            tags={'arm': arm}
        )
        metrics.histogram(
            'learning.bandit.reward',
            reward,
            tags={'arm': arm}
        )
    
    # ============================================
    # QUALITY METRICS
    # ============================================
    
    @staticmethod
    def track_user_satisfaction(rating: int):
        """Satisfacción del usuario"""
        metrics.histogram(
            'learning.user.satisfaction',
            rating
        )
    
    @staticmethod
    def track_correction_rate(organization_id: str):
        """Tasa de correcciones (indica necesidad de aprendizaje)"""
        metrics.increment(
            'learning.corrections.count',
            tags={'organization_id': organization_id}
        )
```

### Dashboards

```yaml
# Grafana Dashboard Configuration
dashboards:
  - name: "AI Learning System Overview"
    panels:
      - title: "Interactions Captured (per hour)"
        query: "sum(rate(learning_interactions_captured[1h])) by (event_type)"
        type: "graph"
      
      - title: "Prediction Confidence Distribution"
        query: "histogram_quantile(0.95, learning_predictions_confidence)"
        type: "heatmap"
      
      - title: "Learning Rate (examples/hour)"
        query: "rate(learning_examples_stored[1h])"
        type: "graph"
      
      - title: "Bandit Arm Performance"
        query: "avg(learning_bandit_reward) by (arm)"
        type: "bar"
      
      - title: "User Satisfaction Trend"
        query: "avg_over_time(learning_user_satisfaction[24h])"
        type: "graph"
      
      - title: "Knowledge Graph Growth"
        query: "learning_kg_entities + learning_kg_relations"
        type: "graph"

  - name: "Learning Quality Metrics"
    panels:
      - title: "Prediction Accuracy by Strategy"
        query: "sum(learning_predictions_accuracy{correct='true'}) / sum(learning_predictions_accuracy) by (strategy)"
        type: "gauge"
      
      - title: "Example Quality Score Distribution"
        query: "histogram_quantile(0.5, learning_examples_quality_score)"
        type: "histogram"
      
      - title: "Correction Rate (lower is better)"
        query: "rate(learning_corrections_count[1h])"
        type: "graph"
```

### Alerting

```python
class LearningAlerts:
    """
    Alertas para el sistema de aprendizaje
    """
    
    # ============================================
    # CRITICAL ALERTS
    # ============================================
    
    @staticmethod
    def alert_processing_failure_rate_high():
        """
        Alerta: Tasa de fallos de procesamiento > 5%
        """
        return Alert(
            name="learning_processing_failure_rate_high",
            condition="rate(learning_processing_errors[5m]) > 0.05",
            severity="critical",
            message="Learning event processing failure rate is above 5%",
            actions=["page_oncall", "create_incident"]
        )
    
    @staticmethod
    def alert_prediction_confidence_low():
        """
        Alerta: Confianza de predicciones < 0.5 (50%)
        """
        return Alert(
            name="learning_prediction_confidence_low",
            condition="avg(learning_predictions_confidence) < 0.5",
            severity="warning",
            message="Average prediction confidence is below 50%",
            actions=["notify_team"]
        )
    
    # ============================================
    # WARNING ALERTS
    # ============================================
    
    @staticmethod
    def alert_correction_rate_increasing():
        """
        Alerta: Tasa de correcciones aumentando (indica degradación)
        """
        return Alert(
            name="learning_correction_rate_increasing",
            condition="deriv(learning_corrections_count[1h]) > 0.1",
            severity="warning",
            message="Correction rate is increasing - model may be degrading",
            actions=["notify_team", "trigger_retraining"]
        )
    
    @staticmethod
    def alert_kg_update_lag():
        """
        Alerta: Knowledge Graph no se actualiza hace > 1 hora
        """
        return Alert(
            name="learning_kg_update_lag",
            condition="time() - learning_kg_last_update > 3600",
            severity="warning",
            message="Knowledge Graph hasn't been updated in over 1 hour",
            actions=["check_pipeline", "notify_team"]
        )
```

---

## 🔄 CONTINUOUS IMPROVEMENT

### A/B Testing Framework

```python
class ABTestingFramework:
    """
    Framework para A/B testing de estrategias de aprendizaje
    """
    
    def __init__(self, experiment_service):
        self.experiment_service = experiment_service
    
    async def assign_variant(
        self,
        user_id: str,
        experiment_name: str
    ) -> str:
        """
        Asigna variante de experimento al usuario
        """
        experiment = await self.experiment_service.get_experiment(experiment_name)
        
        if not experiment or not experiment.is_active:
            return 'control'
        
        # Hash consistente para asignación estable
        user_hash = hashlib.md5(
            f"{user_id}:{experiment_name}".encode()
        ).hexdigest()
        
        hash_value = int(user_hash, 16) % 100
        
        cumulative = 0
        for variant, percentage in experiment.variants.items():
            cumulative += percentage
            if hash_value < cumulative:
                return variant
        
        return 'control'
    
    async def track_experiment_outcome(
        self,
        user_id: str,
        experiment_name: str,
        variant: str,
        outcome_metric: str,
        value: float
    ):
        """
        Registra resultado de experimento
        """
        await self.experiment_service.record_outcome(
            experiment_name=experiment_name,
            variant=variant,
            metric=outcome_metric,
            value=value,
            user_id=user_id
        )

# Ejemplo de uso
@router.post("/api/learning/predict")
async def get_prediction(query: str, user_id: str):
    # Asignar variante de experimento
    strategy_variant = await ab_testing.assign_variant(
        user_id=user_id,
        experiment_name="prediction_strategy_v2"
    )
    
    # Usar estrategia según variante
    if strategy_variant == 'few_shot_only':
        result = await inference_engine.predict_few_shot_only(query)
    elif strategy_variant == 'kg_enhanced':
        result = await inference_engine.predict_kg_enhanced(query)
    else:  # control
        result = await inference_engine.predict(query)
    
    # Registrar resultado
    await ab_testing.track_experiment_outcome(
        user_id=user_id,
        experiment_name="prediction_strategy_v2",
        variant=strategy_variant,
        outcome_metric="confidence",
        value=result.confidence
    )
    
    return result
```

---

**Continúa en:** `AI_LEARNING_SYSTEM_PART3_RFX_IMPLEMENTATION.md`
