"""
Subscription Plans Configuration (Hardcoded)

VERSIÓN: 2.1 - Modelo Granular de Créditos
Última actualización: 9 de Diciembre, 2025

Cambios en v2.1:
- Modelo granular: 5 créditos extracción + 5 créditos generación
- Plan STARTER agregado (250 créditos/mes)
- Regeneraciones gratuitas por plan configuradas
- Costos de operaciones definidos como constantes

Planes de suscripción definidos en código, no en base de datos.
Sigue principio KISS: simple, fácil de modificar, sin overengineering.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class SubscriptionPlan:
    """Definición de un plan de suscripción con sistema de créditos"""
    tier: str
    name: str
    max_users: int
    max_rfx_per_month: int
    credits_per_month: int  # Créditos mensuales
    price_monthly_usd: float
    features: list
    free_regenerations: int = 0  # Regeneraciones gratuitas de propuestas
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para JSON responses"""
        return {
            'tier': self.tier,
            'name': self.name,
            'max_users': self.max_users,
            'max_rfx_per_month': self.max_rfx_per_month,
            'credits_per_month': self.credits_per_month,
            'price_monthly_usd': self.price_monthly_usd,
            'features': self.features,
            'free_regenerations': self.free_regenerations
        }


# ========================
# COSTOS DE OPERACIONES (Modelo Granular v2.1)
# ========================

CREDIT_COSTS = {
    'extraction': 5,        # Extraer datos de documento
    'generation': 5,        # Generar propuesta inicial
    'complete': 10,         # Proceso completo (extracción + generación)
    'chat_message': 1,      # Mensaje de chat para actualizar RFX
    'regeneration': 5       # Regenerar propuesta (puede ser gratis según plan)
}

# Regeneraciones gratuitas por plan
FREE_REGENERATIONS = {
    'free': 1,              # 1 regeneración gratis
    'starter': 3,           # 3 regeneraciones gratis
    'pro': float('inf'),    # Regeneraciones ilimitadas
    'enterprise': float('inf')  # Regeneraciones ilimitadas
}


# ========================
# PLANES HARDCODEADOS
# ========================

PLANS: Dict[str, SubscriptionPlan] = {
    'free': SubscriptionPlan(
        tier='free',
        name='Free Plan',
        max_users=2,
        max_rfx_per_month=10,
        credits_per_month=100,  # ~10 RFX completos (10 créditos c/u)
        price_monthly_usd=0.0,
        free_regenerations=1,
        features=[
            'Up to 2 users',
            '100 credits per month (~10 RFX)',
            '1 free regeneration per proposal',
            'Basic proposal generation',
            'Email support',
            'Community access'
        ]
    ),
    
    'starter': SubscriptionPlan(
        tier='starter',
        name='Starter Plan',
        max_users=5,
        max_rfx_per_month=25,
        credits_per_month=250,  # ~25 RFX completos
        price_monthly_usd=29.0,
        free_regenerations=3,
        features=[
            'Up to 5 users',
            '250 credits per month (~25 RFX)',
            '3 free regenerations per proposal',
            'Advanced proposal generation',
            'Basic branding',
            'Priority email support'
        ]
    ),
    
    'pro': SubscriptionPlan(
        tier='pro',
        name='Professional Plan',
        max_users=50,
        max_rfx_per_month=500,
        credits_per_month=1500,  # ~150 RFX completos (con margen)
        price_monthly_usd=99.0,
        free_regenerations=float('inf'),  # Ilimitadas
        features=[
            'Up to 50 users',
            '1500 credits per month (~150 RFX)',
            'Unlimited free regenerations',
            'Advanced proposal generation',
            'Custom branding',
            'Priority email support',
            'Advanced analytics',
            'API access'
        ]
    ),
    
    'enterprise': SubscriptionPlan(
        tier='enterprise',
        name='Enterprise Plan',
        max_users=999999,  # Unlimited
        max_rfx_per_month=999999,  # Unlimited
        credits_per_month=999999,  # Unlimited
        price_monthly_usd=499.0,
        free_regenerations=float('inf'),  # Ilimitadas
        features=[
            'Unlimited users',
            'Unlimited RFX',
            'Unlimited credits',
            'Unlimited free regenerations',
            'White-label branding',
            'Dedicated account manager',
            '24/7 phone support',
            'Custom integrations',
            'SLA guarantee',
            'Advanced security features',
            'Custom training'
        ]
    )
}


# ========================
# HELPER FUNCTIONS
# ========================

def get_plan(tier: str) -> Optional[SubscriptionPlan]:
    """
    Obtener plan por tier.
    
    Args:
        tier: 'free', 'pro', o 'enterprise'
    
    Returns:
        SubscriptionPlan o None si no existe
    """
    return PLANS.get(tier.lower())


def get_all_plans() -> list:
    """
    Obtener todos los planes disponibles.
    
    Returns:
        Lista de diccionarios con información de planes
    """
    return [plan.to_dict() for plan in PLANS.values()]


def validate_limit(tier: str, limit_type: str, current_value: int) -> bool:
    """
    Validar si un valor está dentro de los límites del plan.
    
    Args:
        tier: Plan tier ('free', 'pro', 'enterprise')
        limit_type: Tipo de límite ('users' o 'rfx')
        current_value: Valor actual a validar
    
    Returns:
        True si está dentro del límite, False si lo excede
    
    Ejemplo:
        validate_limit('free', 'users', 3)  # False (max 2)
        validate_limit('pro', 'rfx', 50)    # True (max 100)
    """
    plan = get_plan(tier)
    if not plan:
        return False
    
    if limit_type == 'users':
        return current_value <= plan.max_users
    elif limit_type == 'rfx':
        return current_value <= plan.max_rfx_per_month
    else:
        return False


def can_add_user(tier: str, current_users: int) -> bool:
    """
    Verificar si se puede agregar un usuario más.
    
    Args:
        tier: Plan tier
        current_users: Número actual de usuarios
    
    Returns:
        True si se puede agregar, False si se alcanzó el límite
    """
    plan = get_plan(tier)
    if not plan:
        return False
    
    return current_users < plan.max_users


def can_create_rfx(tier: str, rfx_this_month: int) -> bool:
    """
    Verificar si se puede crear un RFX más este mes.
    
    Args:
        tier: Plan tier
        rfx_this_month: Número de RFX creados este mes
    
    Returns:
        True si se puede crear, False si se alcanzó el límite
    """
    plan = get_plan(tier)
    if not plan:
        return False
    
    return rfx_this_month < plan.max_rfx_per_month


def get_upgrade_suggestion(tier: str) -> Optional[str]:
    """
    Sugerir upgrade si existe un plan superior.
    
    Args:
        tier: Plan actual
    
    Returns:
        Tier del plan sugerido o None
    """
    if tier == 'free':
        return 'starter'
    elif tier == 'starter':
        return 'pro'
    elif tier == 'pro':
        return 'enterprise'
    else:
        return None


def format_limit_error(tier: str, limit_type: str) -> dict:
    """
    Formatear mensaje de error cuando se alcanza un límite.
    
    Args:
        tier: Plan actual
        limit_type: Tipo de límite alcanzado ('users' o 'rfx')
    
    Returns:
        Diccionario con error formateado
    """
    plan = get_plan(tier)
    if not plan:
        return {
            'status': 'error',
            'message': 'Invalid plan tier'
        }
    
    if limit_type == 'users':
        limit = plan.max_users
        message = f"User limit reached. Your {plan.name} allows up to {limit} users."
    elif limit_type == 'rfx':
        limit = plan.max_rfx_per_month
        message = f"Monthly RFX limit reached. Your {plan.name} allows up to {limit} RFX per month."
    else:
        message = "Limit reached for your current plan."
    
    upgrade = get_upgrade_suggestion(tier)
    
    return {
        'status': 'error',
        'message': message,
        'current_plan': plan.to_dict(),
        'upgrade_available': upgrade,
        'upgrade_plan': PLANS[upgrade].to_dict() if upgrade else None
    }


# ========================
# FUNCIONES DE CRÉDITOS
# ========================

def get_operation_cost(operation: str) -> int:
    """
    Obtener costo en créditos de una operación.
    
    Args:
        operation: Tipo de operación ('extraction', 'generation', 'complete', 'chat_message', 'regeneration')
    
    Returns:
        Costo en créditos
    
    Raises:
        ValueError: Si la operación no existe
    """
    if operation not in CREDIT_COSTS:
        raise ValueError(f"Unknown operation: {operation}. Valid operations: {list(CREDIT_COSTS.keys())}")
    return CREDIT_COSTS[operation]


def get_free_regenerations(tier: str) -> int:
    """
    Obtener número de regeneraciones gratuitas para un plan.
    
    Args:
        tier: Plan tier
    
    Returns:
        Número de regeneraciones gratuitas (float('inf') para ilimitadas)
    """
    return FREE_REGENERATIONS.get(tier.lower(), 0)


def has_unlimited_regenerations(tier: str) -> bool:
    """
    Verificar si un plan tiene regeneraciones ilimitadas.
    
    Args:
        tier: Plan tier
    
    Returns:
        True si tiene regeneraciones ilimitadas
    """
    return get_free_regenerations(tier) == float('inf')


def calculate_credits_needed(extraction: bool = False, generation: bool = False, 
                            chat_messages: int = 0, regeneration: bool = False) -> int:
    """
    Calcular créditos necesarios para una operación.
    
    Args:
        extraction: Si se requiere extracción
        generation: Si se requiere generación
        chat_messages: Número de mensajes de chat
        regeneration: Si es una regeneración
    
    Returns:
        Total de créditos necesarios
    
    Ejemplo:
        calculate_credits_needed(extraction=True, generation=True)  # 10 créditos (proceso completo)
        calculate_credits_needed(regeneration=True)  # 5 créditos
        calculate_credits_needed(chat_messages=3)  # 3 créditos
    """
    total = 0
    
    if extraction:
        total += CREDIT_COSTS['extraction']
    
    if generation:
        total += CREDIT_COSTS['generation']
    
    if chat_messages > 0:
        total += CREDIT_COSTS['chat_message'] * chat_messages
    
    if regeneration:
        total += CREDIT_COSTS['regeneration']
    
    return total
