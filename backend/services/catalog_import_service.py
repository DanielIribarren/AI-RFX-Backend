"""
Catalog Import Service V2 - AI-First Simple
El AI mapea columnas del Excel a columnas de BD, luego pandas parsea correctamente.
"""

from typing import Dict, List
import pandas as pd
import logging
from datetime import datetime
from openai import OpenAI
import json

logger = logging.getLogger(__name__)


class CatalogImportService:
    """Servicio de importación AI-First"""
    
    SUPPORTED_FORMATS = {'.xlsx', '.xls', '.csv'}
    
    # Columnas requeridas en BD
    DB_SCHEMA = {
        'product_code': 'Código único del producto (SKU, referencia, código)',
        'product_name': 'Nombre descriptivo del producto',
        'unit_cost': 'Costo unitario (número decimal)',
        'unit_price': 'Precio de venta unitario (número decimal)',
        'unit': 'Unidad de medida (opcional: kg, unidad, caja, etc.)'
    }
    
    def __init__(self, db, openai_client: OpenAI, redis_client=None):
        self.db = db
        self.openai = openai_client
        self.redis = redis_client
    
    def import_catalog(self, file, organization_id: str = None, user_id: str = None) -> dict:
        """
        Importa catálogo desde Excel/CSV usando AI para mapeo
        
        Lógica inteligente:
        - Si organization_id existe → importar a catálogo de organización
        - Si NO existe → importar a catálogo individual del user_id
        """
        
        if not organization_id and not user_id:
            raise ValueError("Must provide either organization_id or user_id")
        
        owner_type = "organization" if organization_id else "user"
        owner_id = organization_id or user_id
        logger.info(f"📥 Starting AI-First catalog import for {owner_type} {owner_id}")
        start_time = datetime.now()
        
        try:
            # 1. Parse file
            df = self._parse_file(file)
            logger.info(f"📊 Parsed {len(df)} rows with columns: {df.columns.tolist()}")
            
            # 2. AI mapea columnas (inteligente, no hardcoded)
            mapping = self._ai_map_columns(df.columns.tolist())
            logger.info(f"🤖 AI mapping: {mapping}")
            
            # 3. Validar mapeo crítico
            self._validate_mapping(mapping, df.columns.tolist())
            
            # 4. Extract products con mapeo correcto
            products = self._extract_products(df, mapping, organization_id, user_id)
            logger.info(f"✅ Extracted {len(products)} products")
            
            # 5. Upsert inteligente (por código primero, luego nombre)
            stats = self._smart_upsert(products, organization_id, user_id)
            
            # 6. Invalidate cache
            if self.redis:
                try:
                    cache_key = f"catalog_embeddings:{owner_type}:{owner_id}"
                    self.redis.delete(cache_key)
                except:
                    pass
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'products_imported': stats['inserted'],
                'products_updated': stats['updated'],
                'duration_seconds': round(duration, 2),
                'mapping_used': mapping
            }
            
        except Exception as e:
            logger.error(f"❌ Import failed: {e}", exc_info=True)
            raise
    
    def _parse_file(self, file) -> pd.DataFrame:
        """Parse Excel/CSV file"""
        filename = file.filename.lower()
        
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip()
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to parse file: {str(e)}")
    
    def _ai_map_columns(self, excel_columns: List[str]) -> Dict[str, str]:
        """AI mapea columnas del Excel a columnas de BD"""
        
        prompt = f"""Eres un experto en mapeo de datos de catálogos de productos.

**COLUMNAS DEL EXCEL DEL CLIENTE:**
{json.dumps(excel_columns, indent=2)}

**COLUMNAS REQUERIDAS EN BASE DE DATOS:**
{json.dumps(self.DB_SCHEMA, indent=2)}

**TU TAREA:**
Mapea cada columna del Excel a la columna correcta de la base de datos.

**REGLAS CRÍTICAS:**
1. `product_code` = Columna que tiene códigos/SKU/referencias (ej: "PRD-0001", "SKU123")
2. `product_name` = Columna con nombres descriptivos (ej: "Tequeños", "Empanadas")
3. `unit_cost` = Columna con costos (números decimales)
4. `unit_price` = Columna con precios de venta (números decimales)
5. `unit` = Columna con unidades de medida (opcional)

**IMPORTANTE:**
- NO confundas código con nombre
- Si una columna tiene valores como "PRD-0001", es `product_code`, NO `product_name`
- Si una columna tiene valores como "Tequeños de Queso", es `product_name`, NO `product_code`

**FORMATO DE RESPUESTA (JSON):**
{{
  "product_code": "nombre_columna_excel",
  "product_name": "nombre_columna_excel",
  "unit_cost": "nombre_columna_excel",
  "unit_price": "nombre_columna_excel",
  "unit": "nombre_columna_excel_o_null"
}}

Responde SOLO con el JSON, sin explicaciones."""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            mapping = json.loads(response.choices[0].message.content)
            
            # Limpiar nulls
            mapping = {k: v for k, v in mapping.items() if v and v != "null"}
            
            return mapping
            
        except Exception as e:
            logger.error(f"❌ AI mapping failed: {e}")
            raise ValueError(f"AI could not map columns: {str(e)}")
    
    def _validate_mapping(self, mapping: Dict, excel_columns: List[str]):
        """Valida que el mapeo sea correcto"""
        
        # Validar columnas críticas
        required = ['product_code', 'product_name']
        missing = [col for col in required if col not in mapping]
        
        if missing:
            raise ValueError(f"AI mapping missing critical columns: {missing}")
        
        # Validar que columnas existen en Excel
        for db_col, excel_col in mapping.items():
            if excel_col not in excel_columns:
                raise ValueError(f"Mapped column '{excel_col}' not found in Excel. Available: {excel_columns}")
        
        logger.info(f"✅ Mapping validation passed")
    
    def _extract_products(self, df: pd.DataFrame, mapping: dict, organization_id: str = None, user_id: str = None) -> List[dict]:
        """Extract products usando mapeo AI"""
        
        products = []
        
        for idx, row in df.iterrows():
            try:
                # Extraer con mapeo correcto
                product = {
                    'organization_id': organization_id,  # Puede ser None
                    'user_id': user_id if not organization_id else None,  # Solo si no hay org
                    'product_code': str(row[mapping['product_code']]).strip(),
                    'product_name': str(row[mapping['product_name']]).strip(),
                    'is_active': True
                }
                
                # Campos opcionales
                if 'unit_cost' in mapping:
                    try:
                        product['unit_cost'] = float(row[mapping['unit_cost']])
                    except:
                        product['unit_cost'] = 0.0
                
                if 'unit_price' in mapping:
                    try:
                        product['unit_price'] = float(row[mapping['unit_price']])
                    except:
                        product['unit_price'] = 0.0
                
                if 'unit' in mapping:
                    product['unit'] = str(row[mapping['unit']]).strip()
                
                # Validar datos críticos
                if (product['product_code'] and product['product_code'] != 'nan' and
                    product['product_name'] and product['product_name'] != 'nan'):
                    products.append(product)
                    
            except Exception as e:
                logger.warning(f"⚠️ Skipping row {idx}: {e}")
                continue
        
        return products
    
    def _smart_upsert(self, products: List[dict], organization_id: str = None, user_id: str = None) -> dict:
        """Upsert inteligente: busca por código primero, luego por nombre"""
        
        inserted = 0
        updated = 0
        
        for product in products:
            try:
                # 1. Buscar por product_code (más confiable)
                query_builder = self.db.client.table('product_catalog').select('id')
                
                # Filtrar por organization_id O user_id
                if organization_id:
                    query_builder = query_builder.eq('organization_id', organization_id)
                else:
                    query_builder = query_builder.eq('user_id', user_id).is_('organization_id', 'null')
                
                existing = query_builder\
                    .eq('product_code', product['product_code'])\
                    .limit(1)\
                    .execute()
                
                # 2. Fallback: buscar por product_name
                if not existing.data:
                    query_builder = self.db.client.table('product_catalog').select('id')
                    
                    if organization_id:
                        query_builder = query_builder.eq('organization_id', organization_id)
                    else:
                        query_builder = query_builder.eq('user_id', user_id).is_('organization_id', 'null')
                    
                    existing = query_builder\
                        .eq('product_name', product['product_name'])\
                        .limit(1)\
                        .execute()
                
                if existing.data:
                    # Update
                    self.db.client.table('product_catalog')\
                        .update(product)\
                        .eq('id', existing.data[0]['id'])\
                        .execute()
                    updated += 1
                else:
                    # Insert
                    self.db.client.table('product_catalog')\
                        .insert(product)\
                        .execute()
                    inserted += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to save product {product.get('product_code')}: {e}")
                continue
        
        logger.info(f"✅ Saved {inserted} new, {updated} updated products")
        
        return {'inserted': inserted, 'updated': updated}
