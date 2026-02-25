"""
🔄 Data Mappers - Funciones utilitarias para mapeo de datos entre schemas
Extrae lógica de mapeo para evitar dependencias circulares
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def map_rfx_data_for_proposal(rfx_data_raw: Dict[str, Any], rfx_products: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Mapea datos de BD V2.0 a estructura esperada por ProposalGenerationService
    
    Args:
        rfx_data_raw: Datos del RFX desde la base de datos V2.0
        
    Returns:
        Dict con estructura esperada por el proposal generator
    """
    logger.info(f"🔄 Mapping RFX data for proposal generation")
    
    try:
        # Extraer información de la empresa/cliente
        companies_info = rfx_data_raw.get("companies", {})
        if isinstance(companies_info, list) and companies_info:
            companies_info = companies_info[0]  # Tomar el primer elemento si es lista
        elif not isinstance(companies_info, dict):
            companies_info = {}
        
        # Extraer información del solicitante
        requesters_info = rfx_data_raw.get("requesters", {})
        if isinstance(requesters_info, list) and requesters_info:
            requesters_info = requesters_info[0]  # Tomar el primer elemento si es lista
        elif not isinstance(requesters_info, dict):
            requesters_info = {}
        
        # Priorizar productos estructurados con precios de rfx_products table
        products = []
        
        if rfx_products and isinstance(rfx_products, list):
            # Usar productos estructurados con precios reales de la base de datos
            logger.info(f"🔍 Using structured products with real prices: {len(rfx_products)} products")
            for prod in rfx_products:
                if isinstance(prod, dict):
                    products.append({
                        "name": prod.get("product_name", "Product"),
                        "quantity": prod.get("quantity", 1),
                        "unit": prod.get("unit", "units"),
                        "description": prod.get("description", ""),
                        "estimated_unit_price": prod.get("estimated_unit_price") or 0.0,  # Precio de venta
                        "unit_cost": prod.get("unit_cost") or 0.0,  # Costo del proveedor ⭐ NUEVO
                    })
        else:
            # Fallback: Mapear productos desde requested_products (JSONB) sin precios
            logger.warning("🔍 No structured products found, using requested_products without prices")
            requested_products = rfx_data_raw.get("requested_products", [])
            
            if requested_products and isinstance(requested_products, list):
                for prod in requested_products:
                    if isinstance(prod, dict):
                        products.append({
                            "name": prod.get("nombre", prod.get("name", "Product")),
                            "quantity": prod.get("cantidad", prod.get("quantity", 1)),
                            "unit": prod.get("unidad", prod.get("unit", "units")),
                            "description": prod.get("descripcion", prod.get("description", "")),
                            "estimated_unit_price": 0.0,  # No prices in JSONB
                            "total_estimated_cost": 0.0   # No costs in JSONB
                        })
            
            # Si no hay productos en requested_products, buscar en metadatos
            if not products:
                metadata = rfx_data_raw.get("metadata_json", {})
                if isinstance(metadata, dict) and "productos" in metadata:
                    productos_meta = metadata["productos"]
                    if isinstance(productos_meta, list):
                        for prod in productos_meta:
                            if isinstance(prod, dict):
                                products.append({
                                    "name": prod.get("nombre", "Product"),
                                    "quantity": prod.get("cantidad", 1),
                                    "unit": prod.get("unidad", "units"),
                                    "description": prod.get("descripcion", ""),
                                    "estimated_unit_price": 0.0,  # No prices in metadata
                                    "total_estimated_cost": 0.0   # No costs in metadata
                                })
        
        # Estructura final esperada por ProposalGenerationService (español legacy)
        mapped_data = {
            "companies": {
                "name": companies_info.get("name", requesters_info.get("name", "Cliente")),
                "email": companies_info.get("email", requesters_info.get("email", "")),
                "industry": companies_info.get("industry", ""),
                "address": companies_info.get("address", "")
            },
            "productos": products,  # Cambiar de "products" a "productos" para consistencia
            "location": rfx_data_raw.get("location", "Por definir"),
            "delivery_date": rfx_data_raw.get("delivery_date", "Por definir"),
            "delivery_time": rfx_data_raw.get("delivery_time", ""),
            "estimated_budget": rfx_data_raw.get("estimated_budget", 0),
            "rfx_type": rfx_data_raw.get("rfx_type", "catering"),
            "rfx_code": rfx_data_raw.get("rfx_code") or (rfx_data_raw.get("metadata_json", {}) or {}).get("rfx_code"),
            "title": rfx_data_raw.get("title", ""),
            "description": rfx_data_raw.get("description", ""),
            "organization_id": rfx_data_raw.get("organization_id"),
            "metadata": rfx_data_raw.get("metadata_json", {})
        }
        
        logger.info(f"✅ Successfully mapped RFX data: {len(products)} products, client: {mapped_data['companies']['name']}")
        return mapped_data
        
    except Exception as e:
        logger.error(f"❌ Error mapping RFX data for proposal: {e}")
        
        # Fallback básico en caso de error
        return {
            "companies": {"name": "Cliente", "email": ""},
            "requesters": {"name": "Solicitante", "email": ""},
            "products": [],
            "location": "Por definir",
            "delivery_date": "Por definir",
            "delivery_time": "",
            "estimated_budget": 0,
            "rfx_type": "catering",
            "title": "",
            "description": "",
            "metadata": {}
        }
