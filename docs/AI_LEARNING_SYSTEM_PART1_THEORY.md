# 🧠 AI LEARNING SYSTEM - PARTE 1: FUNDAMENTOS TEÓRICOS

**Versión:** 1.0  
**Fecha:** 26 de Enero, 2026  
**Propósito:** Fundamentos teóricos y algoritmos profesionales para sistema de aprendizaje continuo

---

## 📋 CONTENIDO

1. [Visión General](#visión-general)
2. [Continual Learning](#continual-learning)
3. [Knowledge Graphs Temporales](#knowledge-graphs-temporales)
4. [Few-Shot Learning](#few-shot-learning)
5. [Contextual Bandits](#contextual-bandits)
6. [Collaborative Filtering](#collaborative-filtering)

---

## 🎯 VISIÓN GENERAL

### Objetivo Principal

Crear un sistema de aprendizaje continuo que permita a los agentes de IA:
- **Aprender** de las interacciones y correcciones de los usuarios
- **Personalizar** respuestas basadas en patrones históricos
- **Mejorar** la precisión de predicciones con el tiempo
- **Adaptarse** a las G específicas de cada organización

### Principios Fundamentales

```
🧠 APRENDIZAJE CONTINUO (Continual Learning)
   ├─ Sin reentrenamiento completo del modelo
   ├─ Actualización incremental de conocimiento
   └─ Preservación de aprendizajes previos

🎯 PERSONALIZACIÓN CONTEXTUAL
   ├─ Por usuario individual
   ├─ Por organización
   └─ Por industria/dominio

⚡ TIEMPO REAL
   ├─ Aprendizaje inmediato de feedback
   ├─ Aplicación instantánea de patrones
   └─ Sin latencia perceptible

🔒 PRIVACIDAD Y SEGURIDAD
   ├─ Datos aislados por organización
   ├─ Control de acceso granular
   └─ Cumplimiento GDPR/CCPA
```

---

## 📚 1. CONTINUAL LEARNING (APRENDIZAJE CONTINUO)

### Definición

> Capacidad de aprender de flujos de información no estacionarios de forma incremental, preservando conocimiento previo mientras se integra nueva información.

### Características Clave

#### A. Adaptación
- Los sistemas pueden adaptarse a nuevas distribuciones de datos sin reentrenamiento masivo
- Mantienen **plasticidad neural**: capacidad de cambiar predicciones basadas en nueva información
- Evitan **pérdida de plasticidad**: rigidez que impide aprender de nuevos datos

#### B. Similitud de Tareas (Transfer Learning)
- Aprovechan conocimiento de tareas relacionadas
- **Transferencia positiva**: aprendizaje en tarea A mejora desempeño en tarea B
- Ejemplo: Si el agente aprende precios de catering, puede transferir ese conocimiento a eventos corporativos

#### C. Agnóstico a Tareas
- Pueden identificar cuando datos pertenecen a distribuciones diferentes
- No requieren etiquetas explícitas de "tipo de tarea"
- Ejemplo: Distinguir automáticamente entre RFX de catering vs. RFX de construcción

#### D. Tolerancia al Ruido
- Filtran señales erróneas en los datos
- Aprenden la distribución real sin componentes de ruido
- Crítico para datos generados por usuarios (errores de tipeo, inconsistencias)

#### E. Eficiencia de Recursos
- Compactos en almacenamiento
- Eficientes en cómputo
- Bajo consumo energético
- **Clave para escalabilidad empresarial**

### Técnicas Principales

#### 1. Elastic Weight Consolidation (EWC)

Protege pesos importantes de tareas previas durante el aprendizaje de nuevas tareas.

```python
class EWCLearning:
    """
    Elastic Weight Consolidation: Protege conocimiento previo
    """
    def __init__(self, model, fisher_matrix, lambda_ewc=0.4):
        self.model = model
        self.fisher = fisher_matrix  # Importancia de cada peso
        self.lambda_ewc = lambda_ewc
        self.old_params = copy.deepcopy(model.parameters())
    
    def compute_loss(self, new_loss):
        """
        Loss = new_task_loss + penalty_for_changing_important_weights
        """
        ewc_loss = 0
        for name, param in self.model.named_parameters():
            fisher_weight = self.fisher[name]
            old_param = self.old_params[name]
            # Penalizar cambios en pesos importantes
            ewc_loss += (fisher_weight * (param - old_param).pow(2)).sum()
        
        return new_loss + (self.lambda_ewc / 2) * ewc_loss
```

**Ventajas:**
- ✅ Preserva conocimiento crítico de tareas previas
- ✅ Permite aprender nuevas tareas sin "olvidar"
- ✅ Matemáticamente fundamentado (Fisher Information Matrix)

**Cuándo usar:**
- Cuando hay tareas secuenciales relacionadas
- Cuando el "olvido catastrófico" es un riesgo

#### 2. Memory Replay

Almacena ejemplos de tareas previas y los "reproduce" periódicamente durante el entrenamiento.

```python
class MemoryReplay:
    """
    Almacena y reproduce ejemplos históricos para evitar olvido
    """
    def __init__(self, buffer_size=1000):
        self.memory_buffer = []
        self.buffer_size = buffer_size
    
    def store_experience(self, data, label):
        """Almacena experiencia en buffer"""
        if len(self.memory_buffer) >= self.buffer_size:
            # Estrategia: reemplazar ejemplos antiguos o menos importantes
            self.memory_buffer.pop(0)
        self.memory_buffer.append((data, label))
    
    def train_with_replay(self, new_batch):
        """Mezcla datos nuevos con ejemplos del pasado"""
        replay_batch = random.sample(self.memory_buffer, k=32)
        combined_batch = new_batch + replay_batch
        return combined_batch
```

**Ventajas:**
- ✅ Simple de implementar
- ✅ Efectivo para evitar olvido
- ✅ No requiere modificar arquitectura del modelo

**Desventajas:**
- ❌ Requiere almacenamiento de ejemplos
- ❌ Puede tener problemas de privacidad (almacena datos reales)

#### 3. Progressive Neural Networks

Añade nuevas "columnas" de red neuronal para nuevas tareas, preservando las anteriores.

```python
class ProgressiveNetwork:
    """
    Red neuronal que crece con nuevas tareas
    """
    def __init__(self):
        self.columns = []  # Una columna por tarea
    
    def add_task(self, new_task):
        """Añade nueva columna para nueva tarea"""
        new_column = NeuralColumn(
            lateral_connections=self.columns  # Conexiones a columnas previas
        )
        self.columns.append(new_column)
        # Columnas previas se congelan (no se modifican)
```

**Ventajas:**
- ✅ Cero olvido (columnas previas no se modifican)
- ✅ Transfer learning automático (conexiones laterales)
- ✅ Escalable a muchas tareas

**Desventajas:**
- ❌ Crece en tamaño con cada nueva tarea
- ❌ Más complejo de implementar

---

## 🕸️ 2. KNOWLEDGE GRAPHS TEMPORALES

### Definición

> Grafos de conocimiento que rastrean entidades, relaciones y su evolución temporal, permitiendo memoria dinámica y contextual para agentes de IA.

### Arquitectura: Graphiti (Zep AI)

```
┌─────────────────────────────────────────────────────────────┐
│                    GRAPHITI ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │   Episode    │─────▶│  Extraction  │─────▶│  Graph   │  │
│  │  (Event/Msg) │      │   Engine     │      │  Update  │  │
│  └──────────────┘      └──────────────┘      └──────────┘  │
│         │                      │                     │       │
│         ▼                      ▼                     ▼       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         TEMPORAL KNOWLEDGE GRAPH                     │  │
│  │  ┌────────┐    ┌────────┐    ┌────────┐            │  │
│  │  │ Entity │───▶│ Entity │───▶│ Entity │            │  │
│  │  │  (t1)  │    │  (t2)  │    │  (t3)  │            │  │
│  │  └────────┘    └────────┘    └────────┘            │  │
│  │       │             │             │                  │  │
│  │       └─────────────┴─────────────┘                  │  │
│  │              Relationships                           │  │
│  │        (with validity intervals)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              HYBRID SEARCH ENGINE                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ Semantic │  │ Keyword  │  │ Graph Traversal  │  │  │
│  │  │(Vectors) │  │  (BM25)  │  │   (Cypher)       │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Características Clave

#### A. Modelo Bi-Temporal

```python
class TemporalEdge:
    """
    Cada relación tiene dos timestamps:
    - t_occurred: Cuándo ocurrió el evento en el mundo real
    - t_ingested: Cuándo se ingresó al sistema
    """
    def __init__(self, source, target, relation_type):
        self.source = source
        self.target = target
        self.relation_type = relation_type
        self.t_occurred = None      # Tiempo del evento real
        self.t_ingested = None       # Tiempo de ingesta
        self.t_valid = None          # Inicio de validez
        self.t_invalid = None        # Fin de validez (puede ser None)
    
    def is_valid_at(self, timestamp):
        """Verifica si la relación era válida en un momento dado"""
        if self.t_valid is None:
            return False
        if self.t_invalid is None:
            return timestamp >= self.t_valid
        return self.t_valid <= timestamp < self.t_invalid
```

#### B. Resolución de Conflictos

```python
class ConflictResolver:
    """
    Cuando nueva información contradice conocimiento existente
    """
    def resolve_conflict(self, existing_fact, new_fact):
        # Estrategia 1: Más reciente gana
        if new_fact.t_occurred > existing_fact.t_occurred:
            existing_fact.t_invalid = new_fact.t_occurred
            return new_fact
        
        # Estrategia 2: Mantener ambos con intervalos de validez
        if self.are_both_valid_at_different_times(existing_fact, new_fact):
            return [existing_fact, new_fact]
        
        # Estrategia 3: Confianza/fuente
        if new_fact.confidence > existing_fact.confidence:
            existing_fact.t_invalid = new_fact.t_ingested
            return new_fact
        
        return existing_fact
```

#### C. Consultas Históricas

```cypher
-- Cypher query: Estado del conocimiento en un momento específico
MATCH (e:Entity)-[r:RELATIONSHIP]->(e2:Entity)
WHERE r.t_valid <= $timestamp 
  AND (r.t_invalid IS NULL OR r.t_invalid > $timestamp)
RETURN e, r, e2

-- Ejemplo: ¿Qué precio tenía "Tequeños" el 15 de diciembre?
MATCH (p:Product {name: "Tequeños"})-[r:HAS_PRICE]->(price:Price)
WHERE r.t_valid <= datetime("2024-12-15")
  AND (r.t_invalid IS NULL OR r.t_invalid > datetime("2024-12-15"))
RETURN price.amount
```

### Ventajas sobre RAG Estático

| Característica | RAG Estático | Graphiti (Temporal KG) |
|----------------|--------------|------------------------|
| **Actualización** | Batch recomputation | Incremental real-time |
| **Latencia** | 10-30 segundos | <300ms (P95) |
| **Conflictos** | Sobrescribe o duplica | Resuelve con temporalidad |
| **Historial** | No disponible | Queries temporales completas |
| **Relaciones** | Implícitas en embeddings | Explícitas en grafo |
| **Escalabilidad** | Recomputa todo el grafo | Solo actualiza nodos afectados |

---

## 🎓 3. FEW-SHOT LEARNING & ADAPTIVE PROMPTING

### Definición

> Técnica que permite a modelos de IA aprender nuevas tareas con pocos ejemplos (2-10), adaptando su comportamiento mediante ejemplos contextuales en el prompt.

### Pipeline Completo

```
1. USER QUERY
   "Estimar precio para Tequeños (200 unidades)"
            ↓
2. SEMANTIC SEARCH (Vector Store)
   Buscar ejemplos similares históricos
            ↓
3. RETRIEVE TOP-K EXAMPLES (k=3-5)
   Seleccionar los más relevantes
            ↓
4. PROMPT CONSTRUCTION
   System + Examples + Query
            ↓
5. LLM PROCESSING
   Modelo infiere patrón
            ↓
6. OUTPUT
   "$0.68/u (bulk discount 18%)"
```

### Implementación

```python
class FewShotLearningEngine:
    """
    Motor de aprendizaje few-shot con recuperación dinámica de ejemplos
    """
    def __init__(self, vector_store, embedding_model):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.example_cache = {}
    
    def retrieve_examples(self, query, k=5, filters=None):
        """Recupera los k ejemplos más relevantes"""
        # 1. Generar embedding del query
        query_embedding = self.embedding_model.encode(query)
        
        # 2. Búsqueda semántica
        results = self.vector_store.similarity_search(
            query_embedding,
            k=k * 2,  # Recuperar más para filtrar
            filters=filters
        )
        
        # 3. Re-ranking por relevancia contextual
        ranked_results = self.rerank_by_context(
            results, query=query, context=filters
        )
        
        return ranked_results[:k]
    
    def construct_prompt(self, query, examples, system_message):
        """Construye prompt con ejemplos dinámicos"""
        prompt_parts = [
            f"System: {system_message}\n",
            "\n# Examples from your organization's history:\n"
        ]
        
        for i, example in enumerate(examples, 1):
            prompt_parts.append(
                f"\nExample {i}:\n"
                f"Input: {example['input']}\n"
                f"Output: {example['output']}\n"
            )
        
        prompt_parts.append(
            f"\n# Now solve:\nInput: {query}\nOutput:"
        )
        
        return "".join(prompt_parts)
```

### Estrategias de Selección

```python
class ExampleSelectionStrategy:
    @staticmethod
    def diversity_sampling(examples, k):
        """Selecciona ejemplos diversos"""
        selected = [examples[0]]  # Más similar
        remaining = examples[1:]
        
        while len(selected) < k and remaining:
            # Maximizar diversidad
            best_candidate = max(
                remaining,
                key=lambda x: min(
                    1 - cosine_similarity(x, s) for s in selected
                )
            )
            selected.append(best_candidate)
            remaining.remove(best_candidate)
        
        return selected
    
    @staticmethod
    def recency_weighted(examples, k, decay_factor=0.95):
        """Prioriza ejemplos recientes"""
        now = datetime.now()
        scored = []
        
        for ex in examples:
            days_old = (now - ex['timestamp']).days
            recency_score = decay_factor ** days_old
            final_score = ex['similarity'] * recency_score
            scored.append((final_score, ex))
        
        scored.sort(reverse=True)
        return [ex for _, ex in scored[:k]]
```

**Ventajas:**
- ✅ Sin Fine-Tuning: No requiere reentrenar el modelo
- ✅ Adaptación Rápida: Aprende de 2-5 ejemplos
- ✅ Bajo Costo: No consume recursos de entrenamiento
- ✅ Transparencia: Ejemplos interpretables
- ✅ Personalización: Cada organización tiene sus propios ejemplos

---

## 🎰 4. CONTEXTUAL BANDITS

### Definición

> Algoritmo de aprendizaje por refuerzo que balancea exploración (probar nuevas opciones) y explotación (usar la mejor opción conocida) en contextos específicos.

### Problema que Resuelve

```
Escenario: Usuario solicita presupuesto para evento de 300 personas

Opciones (Arms):
1. Usar precio estándar del catálogo
2. Usar precio promedio histórico del usuario
3. Usar precio de eventos similares (same size)
4. Usar precio con descuento por volumen automático

¿Cuál opción genera mayor satisfacción del cliente?
→ Depende del CONTEXTO (tipo de cliente, historial, industria, etc.)
```

### Implementación: Thompson Sampling

```python
class ContextualBandit:
    """
    Contextual Bandit con Thompson Sampling
    """
    def __init__(self, arms):
        self.arms = arms
        # Distribuciones Beta para cada arm
        self.arm_distributions = {
            arm: {'alpha': 1, 'beta': 1}
            for arm in arms
        }
    
    def select_arm(self, context):
        """
        Thompson Sampling:
        1. Para cada arm, samplea de su distribución Beta
        2. Selecciona el arm con el sample más alto
        """
        samples = {}
        for arm in self.arms:
            alpha = self.arm_distributions[arm]['alpha']
            beta = self.arm_distributions[arm]['beta']
            samples[arm] = np.random.beta(alpha, beta)
        
        return max(samples, key=samples.get)
    
    def update(self, arm, context, reward):
        """Actualiza distribución basado en reward"""
        normalized_reward = self._normalize_reward(reward)
        
        if normalized_reward >= 0.5:  # Success
            self.arm_distributions[arm]['alpha'] += 1
        else:  # Failure
            self.arm_distributions[arm]['beta'] += 1
```

### Comparación de Estrategias

| Estrategia | Exploración/Explotación | Complejidad | Convergencia |
|------------|-------------------------|-------------|--------------|
| **Thompson Sampling** | Automático (probabilístico) | Media | Rápida ⭐ |
| **ε-greedy** | Manual (parámetro ε) | Baja | Lenta |
| **UCB** | Automático (determinístico) | Media | Media |

---

## 🤝 5. COLLABORATIVE FILTERING

### Definición

> Técnica que aprovecha similitudes entre usuarios e ítems para generar recomendaciones personalizadas.

### Tipos

#### A. User-Based
```
"Usuarios similares a ti también usaron..."
Usuario A: ✓ Tequeños, ✓ Empanadas, ✓ Canapés
Usuario B: ✓ Tequeños, ✓ Empanadas, ? Canapés
                                      ↑
                              Recomendar Canapés a B
```

#### B. Item-Based
```
"Productos similares a los que usaste..."
Tequeños → Empanadas (80% co-occurrence)
Tequeños → Canapés (75% co-occurrence)
```

### Implementación con Embeddings

```python
class CollaborativeFilteringEngine:
    """
    Sistema de recomendaciones basado en embeddings
    """
    def __init__(self, embedding_dim=64):
        self.embedding_dim = embedding_dim
        self.user_embeddings = {}
        self.product_embeddings = {}
    
    def train(self, interactions):
        """
        Matrix Factorization: R ≈ U × P^T
        """
        # Crear matriz de interacciones
        users = list(set(i['user_id'] for i in interactions))
        products = list(set(i['product_id'] for i in interactions))
        
        R = np.zeros((len(users), len(products)))
        # ... llenar matriz ...
        
        # SVD para factorización
        from scipy.sparse.linalg import svds
        U, sigma, Vt = svds(R, k=self.embedding_dim)
        
        # Guardar embeddings
        for i, user in enumerate(users):
            self.user_embeddings[user] = U[i]
        for i, product in enumerate(products):
            self.product_embeddings[product] = Vt.T[i]
    
    def recommend_products(self, user_id, k=10):
        """Recomienda top-k productos"""
        user_emb = self.user_embeddings[user_id]
        
        scores = {}
        for product_id, product_emb in self.product_embeddings.items():
            # Score = similitud coseno
            score = np.dot(user_emb, product_emb) / (
                np.linalg.norm(user_emb) * np.linalg.norm(product_emb)
            )
            scores[product_id] = score
        
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [p for p, s in ranked[:k]]
```

**Ventajas:**
- ✅ Serendipity: Descubre patrones no obvios
- ✅ Sin Features Manuales: Aprende automáticamente
- ✅ Escalable: Funciona con millones de usuarios/productos
- ✅ Explainable: Puede justificar recomendaciones

---

## 📊 RESUMEN COMPARATIVO

| Técnica | Cuándo Usar | Complejidad | Escalabilidad |
|---------|-------------|-------------|---------------|
| **Continual Learning** | Aprendizaje incremental sin olvido | Alta | Alta |
| **Knowledge Graphs** | Relaciones complejas y temporales | Alta | Media-Alta |
| **Few-Shot Learning** | Adaptación rápida con pocos ejemplos | Baja-Media | Alta |
| **Contextual Bandits** | Optimización de decisiones contextuales | Media | Alta |
| **Collaborative Filtering** | Recomendaciones basadas en similitud | Media | Muy Alta |

---

**Continúa en:** `AI_LEARNING_SYSTEM_PART2_IMPLEMENTATION.md`
