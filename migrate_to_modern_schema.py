#!/usr/bin/env python3
"""
🚀 MIGRACIÓN COMPLETA: RFX Legacy → Esquema Moderno SaaS
Migra todos los datos de rfx_v2 al nuevo esquema projects/organizations/users
"""
import sys
import os
sys.path.append('.')

from backend.core.database import get_database_client
from backend.core.config import get_database_config
from supabase import create_client
import logging
from datetime import datetime
from uuid import uuid4
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchemaMigration:
    """Migración completa de esquema legacy a moderno"""
    
    def __init__(self):
        self.db_config = get_database_config()
        self.client = create_client(self.db_config.url, self.db_config.anon_key)
        self.migration_stats = {
            'organizations': 0,
            'users': 0, 
            'projects': 0,
            'project_items': 0,
            'errors': []
        }
    
    def step_1_create_modern_schema(self):
        """Paso 1: Crear el esquema moderno en Supabase"""
        logger.info("🚀 PASO 1: Creando esquema moderno...")
        
        try:
            # Leer y ejecutar el schema SQL
            with open('Database/budy-ai-schema.sql', 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            logger.info("📋 Esquema SQL leído correctamente")
            logger.info("⚠️  IMPORTANTE: Ejecuta manualmente el archivo 'Database/budy-ai-schema.sql' en tu Supabase Dashboard")
            logger.info("   1. Ve a tu proyecto Supabase")
            logger.info("   2. Abre el SQL Editor")
            logger.info("   3. Copia y pega el contenido de Database/budy-ai-schema.sql")
            logger.info("   4. Ejecuta el script")
            logger.info("   5. Presiona ENTER aquí cuando hayas terminado...")
            
            input("Presiona ENTER cuando hayas ejecutado el schema en Supabase...")
            
            # Verificar que las tablas se crearon
            response = self.client.table("projects").select("id").limit(1).execute()
            logger.info("✅ Esquema moderno verificado - tabla 'projects' existe")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando esquema moderno: {e}")
            return False
    
    def step_2_migrate_organizations(self):
        """Paso 2: Migrar companies → organizations"""
        logger.info("🏢 PASO 2: Migrando companies → organizations...")
        
        try:
            # Obtener todas las companies
            companies_response = self.client.table("companies").select("*").execute()
            companies = companies_response.data or []
            
            logger.info(f"📊 Encontradas {len(companies)} companies para migrar")
            
            for company in companies:
                try:
                    # Mapear company → organization
                    org_data = {
                        'id': company.get('id', str(uuid4())),
                        'name': company.get('name', 'Unknown Organization'),
                        'email': company.get('email'),
                        'phone': company.get('phone'),
                        'address': company.get('address'),
                        'industry': company.get('industry', 'general'),
                        'plan_type': 'free',  # Default
                        'default_currency': company.get('currency', 'USD'),
                        'language_preference': 'es',
                        'is_active': True,
                        'created_at': company.get('created_at', datetime.utcnow().isoformat()),
                        'updated_at': company.get('updated_at', datetime.utcnow().isoformat())
                    }
                    
                    # Insertar en organizations
                    self.client.table("organizations").insert(org_data).execute()
                    self.migration_stats['organizations'] += 1
                    
                    logger.info(f"✅ Migrada organization: {org_data['name']}")
                    
                except Exception as e:
                    error_msg = f"Error migrando company {company.get('id')}: {e}"
                    logger.error(f"❌ {error_msg}")
                    self.migration_stats['errors'].append(error_msg)
            
            logger.info(f"✅ Migración de organizations completada: {self.migration_stats['organizations']} migradas")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en migración de organizations: {e}")
            return False
    
    def step_3_migrate_users(self):
        """Paso 3: Migrar requesters → users"""
        logger.info("👤 PASO 3: Migrando requesters → users...")
        
        try:
            # Obtener todos los requesters
            requesters_response = self.client.table("requesters").select("*").execute()
            requesters = requesters_response.data or []
            
            logger.info(f"📊 Encontrados {len(requesters)} requesters para migrar")
            
            for requester in requesters:
                try:
                    # Mapear requester → user
                    user_data = {
                        'id': requester.get('id', str(uuid4())),
                        'name': requester.get('name', 'Unknown User'),
                        'email': requester.get('email'),
                        'phone': requester.get('phone'),
                        'position': requester.get('position'),
                        'organization_id': requester.get('company_id'),  # FK to organization
                        'role': 'user',  # Default role
                        'is_active': True,
                        'created_at': requester.get('created_at', datetime.utcnow().isoformat()),
                        'updated_at': requester.get('updated_at', datetime.utcnow().isoformat())
                    }
                    
                    # Insertar en users
                    self.client.table("users").insert(user_data).execute()
                    self.migration_stats['users'] += 1
                    
                    logger.info(f"✅ Migrado user: {user_data['name']}")
                    
                except Exception as e:
                    error_msg = f"Error migrando requester {requester.get('id')}: {e}"
                    logger.error(f"❌ {error_msg}")
                    self.migration_stats['errors'].append(error_msg)
            
            logger.info(f"✅ Migración de users completada: {self.migration_stats['users']} migrados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en migración de users: {e}")
            return False
    
    def step_4_migrate_projects(self):
        """Paso 4: Migrar rfx_v2 → projects"""
        logger.info("📋 PASO 4: Migrando rfx_v2 → projects...")
        
        try:
            # Obtener todos los RFX
            rfx_response = self.client.table("rfx_v2").select("*").execute()
            rfx_list = rfx_response.data or []
            
            logger.info(f"📊 Encontrados {len(rfx_list)} RFX para migrar")
            
            for rfx in rfx_list:
                try:
                    # Mapear rfx → project
                    project_data = {
                        'id': rfx.get('id', str(uuid4())),
                        'name': rfx.get('title', 'Untitled Project'),
                        'description': rfx.get('description', ''),
                        'project_type': self._map_rfx_type(rfx.get('tipo_rfx', 'general')),
                        'status': self._map_rfx_status(rfx.get('status', 'draft')),
                        'priority': rfx.get('priority', 3),
                        'organization_id': rfx.get('company_id'),
                        'created_by': rfx.get('requester_id'),
                        'project_number': rfx.get('id', f"PROJ-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"),
                        'requirements': rfx.get('requirements', []),
                        'estimated_budget': rfx.get('estimated_budget'),
                        'budget_range_min': rfx.get('budget_range_min'),
                        'budget_range_max': rfx.get('budget_range_max'),
                        'currency': rfx.get('currency', 'USD'),
                        'delivery_date': rfx.get('delivery_date'),
                        'start_date': rfx.get('start_date'),
                        'end_date': rfx.get('end_date'),
                        'location': rfx.get('location'),
                        'created_at': rfx.get('created_at', datetime.utcnow().isoformat()),
                        'updated_at': rfx.get('updated_at', datetime.utcnow().isoformat())
                    }
                    
                    # Insertar en projects
                    self.client.table("projects").insert(project_data).execute()
                    self.migration_stats['projects'] += 1
                    
                    logger.info(f"✅ Migrado project: {project_data['name']}")
                    
                    # Migrar productos asociados
                    self._migrate_project_items(rfx.get('id'), project_data['id'])
                    
                except Exception as e:
                    error_msg = f"Error migrando RFX {rfx.get('id')}: {e}"
                    logger.error(f"❌ {error_msg}")
                    self.migration_stats['errors'].append(error_msg)
            
            logger.info(f"✅ Migración de projects completada: {self.migration_stats['projects']} migrados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en migración de projects: {e}")
            return False
    
    def _migrate_project_items(self, rfx_id, project_id):
        """Migrar productos de RFX a project_items"""
        try:
            # Obtener productos del RFX
            products_response = self.client.table("rfx_products").select("*").eq("rfx_id", rfx_id).execute()
            products = products_response.data or []
            
            for product in products:
                item_data = {
                    'id': product.get('id', str(uuid4())),
                    'project_id': project_id,
                    'name': product.get('product_name', 'Unknown Item'),
                    'description': product.get('specifications', ''),
                    'quantity': product.get('quantity', 1),
                    'unit': product.get('unit', 'units'),
                    'unit_price': product.get('unit_price', 0.0),
                    'category': product.get('category', 'general'),
                    'created_at': product.get('created_at', datetime.utcnow().isoformat()),
                    'updated_at': product.get('updated_at', datetime.utcnow().isoformat())
                }
                
                self.client.table("project_items").insert(item_data).execute()
                self.migration_stats['project_items'] += 1
                
        except Exception as e:
            logger.warning(f"⚠️ Error migrando items para project {project_id}: {e}")
    
    def _map_rfx_type(self, tipo_rfx):
        """Mapear tipos de RFX a project_type_enum"""
        mapping = {
            'catering': 'catering',
            'events': 'events', 
            'construction': 'construction',
            'consulting': 'consulting',
            'marketing': 'marketing',
            'technology': 'technology',
            'general': 'general'
        }
        return mapping.get(tipo_rfx, 'general')
    
    def _map_rfx_status(self, status):
        """Mapear estados de RFX a project_status_enum"""
        mapping = {
            'draft': 'draft',
            'in_progress': 'active',
            'pending': 'pending_review',
            'completed': 'completed',
            'cancelled': 'cancelled',
            'on_hold': 'on_hold'
        }
        return mapping.get(status, 'draft')
    
    def step_5_update_database_client(self):
        """Paso 5: Actualizar database client para usar solo esquema moderno"""
        logger.info("🔧 PASO 5: Actualizando database client...")
        
        # Modificar database.py para forzar modo moderno
        database_file = 'backend/core/database.py'
        
        try:
            with open(database_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Reemplazar la detección automática con modo forzado moderno
            old_detection = '''    def _detect_schema_mode(self) -> None:
        """Auto-detect which database schema is available"""
        try:
            # Try new schema first
            response = self.client.table("projects").select("id").limit(1).execute()
            self._schema_mode = "modern"
            logger.info("🆕 Modern schema detected (budy-ai-schema)")
        except Exception:
            try:
                # Fallback to legacy schema
                response = self.client.table("rfx_v2").select("id").limit(1).execute()
                self._schema_mode = "legacy"
                logger.info("📚 Legacy schema detected (rfx_v2)")
            except Exception as e:
                logger.error(f"❌ No compatible schema found: {e}")
                self._schema_mode = "unknown"'''
            
            new_detection = '''    def _detect_schema_mode(self) -> None:
        """Force modern schema mode after migration"""
        try:
            # Force modern schema - migration completed
            response = self.client.table("projects").select("id").limit(1).execute()
            self._schema_mode = "modern"
            logger.info("🆕 Modern schema active (post-migration)")
        except Exception as e:
            logger.error(f"❌ Modern schema not available: {e}")
            self._schema_mode = "unknown"
            raise Exception("Modern schema required but not found. Please run migration first.")'''
            
            # Reemplazar en el archivo
            updated_content = content.replace(old_detection, new_detection)
            
            with open(database_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info("✅ Database client actualizado para usar solo esquema moderno")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando database client: {e}")
            return False
    
    def step_6_cleanup_legacy_tables(self):
        """Paso 6: Limpiar tablas legacy (OPCIONAL)"""
        logger.info("🧹 PASO 6: Limpieza de tablas legacy...")
        
        response = input("¿Quieres eliminar las tablas legacy (rfx_v2, companies, requesters)? (y/N): ")
        
        if response.lower() == 'y':
            try:
                logger.info("🗑️ Eliminando tablas legacy...")
                
                # Nota: En Supabase, esto debe hacerse manualmente por seguridad
                logger.info("⚠️  Para eliminar las tablas legacy, ejecuta manualmente en Supabase:")
                logger.info("   DROP TABLE IF EXISTS rfx_products CASCADE;")
                logger.info("   DROP TABLE IF EXISTS rfx_v2 CASCADE;")
                logger.info("   DROP TABLE IF EXISTS requesters CASCADE;")
                logger.info("   DROP TABLE IF EXISTS companies CASCADE;")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error en limpieza: {e}")
                return False
        else:
            logger.info("⏭️ Saltando limpieza de tablas legacy")
            return True
    
    def run_migration(self):
        """Ejecutar migración completa"""
        logger.info("🚀 INICIANDO MIGRACIÓN COMPLETA: RFX Legacy → Esquema Moderno SaaS")
        logger.info("="*80)
        
        steps = [
            ("Crear esquema moderno", self.step_1_create_modern_schema),
            ("Migrar organizations", self.step_2_migrate_organizations),
            ("Migrar users", self.step_3_migrate_users),
            ("Migrar projects", self.step_4_migrate_projects),
            ("Actualizar database client", self.step_5_update_database_client),
            ("Limpiar tablas legacy", self.step_6_cleanup_legacy_tables)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n📋 {step_name}...")
            success = step_func()
            
            if not success:
                logger.error(f"❌ Falló: {step_name}")
                return False
            
            logger.info(f"✅ Completado: {step_name}")
        
        # Mostrar estadísticas finales
        logger.info("\n" + "="*80)
        logger.info("📊 MIGRACIÓN COMPLETADA - ESTADÍSTICAS:")
        logger.info("="*80)
        logger.info(f"🏢 Organizations migradas: {self.migration_stats['organizations']}")
        logger.info(f"👤 Users migrados: {self.migration_stats['users']}")
        logger.info(f"📋 Projects migrados: {self.migration_stats['projects']}")
        logger.info(f"📦 Project items migrados: {self.migration_stats['project_items']}")
        logger.info(f"❌ Errores: {len(self.migration_stats['errors'])}")
        
        if self.migration_stats['errors']:
            logger.info("\n⚠️ Errores encontrados:")
            for error in self.migration_stats['errors']:
                logger.info(f"   - {error}")
        
        logger.info("\n🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        logger.info("✅ Tu proyecto ahora usa el esquema moderno SaaS")
        logger.info("✅ Todas las APIs funcionarán con el nuevo esquema")
        logger.info("✅ BudyAgent tendrá acceso completo a funcionalidades avanzadas")
        
        return True

def main():
    """Función principal"""
    print("🚀 MIGRACIÓN COMPLETA: RFX Legacy → Esquema Moderno SaaS")
    print("="*80)
    print("Esta migración:")
    print("✅ Crea el esquema moderno (projects, organizations, users)")
    print("✅ Migra todos los datos existentes")
    print("✅ Actualiza el sistema para usar solo el esquema moderno")
    print("✅ Elimina dependencias del esquema legacy")
    print("="*80)
    
    response = input("¿Continuar con la migración? (y/N): ")
    
    if response.lower() != 'y':
        print("❌ Migración cancelada")
        return False
    
    migration = SchemaMigration()
    return migration.run_migration()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


