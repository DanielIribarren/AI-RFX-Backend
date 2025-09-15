#!/usr/bin/env python3
"""
🚀 DÍA 1: MIGRACIÓN RFX → SAAS GENERAL
Script completo automatizado - Sin tocar Supabase Dashboard

Ejecutar: python day_1_migration.py
Tiempo estimado: 10-15 minutos
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import shutil

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_day_1.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Day1Migration:
    """
    Automatización completa del Día 1 de migración
    """
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "migration_backups"
        self.migration_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.migration_branch = "saas-migration"
        
    def run_complete_day_1(self):
        """
        Ejecutar todo el Día 1 automáticamente
        """
        try:
            logger.info("🚀 INICIANDO DÍA 1: MIGRACIÓN RFX → SAAS GENERAL")
            logger.info("=" * 60)
            
            # 1. Preparación y validaciones iniciales
            self._validate_environment()
            
            # 2. Crear directorio de backups
            self._create_backup_directory()
            
            # 3. Backup completo del proyecto
            self._backup_complete_project()
            
            # 4. Backup de base de datos
            self._backup_database()
            
            # 5. Crear branch de migración
            self._create_migration_branch()
            
            # 6. Analizar dependencias
            dependencies = self._analyze_project_dependencies()
            
            # 7. Generar plan de migración
            migration_plan = self._generate_migration_plan(dependencies)
            
            # 8. Crear documentos de rollback
            self._create_rollback_plan()
            
            # 9. Validaciones finales
            self._run_final_validations()
            
            # 10. Resumen y siguientes pasos
            self._generate_day_1_summary(migration_plan)
            
            logger.info("✅ DÍA 1 COMPLETADO EXITOSAMENTE!")
            logger.info("🎯 LISTO PARA DÍA 2: Migración de esquema de BD")
            
        except Exception as e:
            logger.error(f"❌ ERROR EN DÍA 1: {str(e)}")
            logger.error("🔄 Ejecutando rollback automático...")
            self._emergency_rollback()
            raise
    
    def _validate_environment(self):
        """Validar que el entorno está listo para migración"""
        logger.info("🔍 Validando entorno de desarrollo...")
        
        # Verificar que estamos en el directorio correcto
        required_files = [
            "backend/app.py",
            "backend/models",
            "backend/services",
            ".env"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise FileNotFoundError(f"Archivos requeridos no encontrados: {missing_files}")
        
        # Verificar Git
        try:
            subprocess.run(["git", "status"], check=True, capture_output=True)
            logger.info("✅ Repositorio Git detectado")
        except subprocess.CalledProcessError:
            raise RuntimeError("Este proyecto debe estar en un repositorio Git")
        
        # Verificar Python y dependencias
        try:
            import supabase
            logger.info("✅ Supabase client disponible")
        except ImportError:
            logger.warning("⚠️ Supabase client no instalado. Instalando...")
            subprocess.run([sys.executable, "-m", "pip", "install", "supabase"], check=True)
        
        logger.info("✅ Entorno validado correctamente")
    
    def _create_backup_directory(self):
        """Crear directorio de backups"""
        self.backup_dir.mkdir(exist_ok=True)
        logger.info(f"📁 Directorio de backups: {self.backup_dir}")
    
    def _backup_complete_project(self):
        """Backup completo del código fuente"""
        logger.info("💾 Creando backup completo del proyecto...")
        
        backup_name = f"project_backup_{self.migration_date}"
        backup_path = self.backup_dir / backup_name
        
        # Crear backup del proyecto (sin node_modules, __pycache__, etc.)
        exclude_patterns = [
            "__pycache__",
            "node_modules",
            ".git",
            "*.pyc",
            ".env",
            "migration_backups"
        ]
        
        # Usar Git para crear un archive limpio
        try:
            subprocess.run([
                "git", "archive", 
                "--format=tar.gz", 
                f"--output={backup_path}.tar.gz",
                "HEAD"
            ], check=True)
            
            logger.info(f"✅ Backup del proyecto creado: {backup_path}.tar.gz")
            
        except subprocess.CalledProcessError:
            # Fallback: copy manual
            logger.warning("🔄 Usando método de backup manual...")
            shutil.copytree(
                self.project_root, 
                backup_path,
                ignore=shutil.ignore_patterns(*exclude_patterns)
            )
            logger.info(f"✅ Backup manual creado: {backup_path}")
    
    def _backup_database(self):
        """Backup de la base de datos Supabase"""
        logger.info("🗄️ Creando backup de base de datos...")
        
        # Crear script de backup de BD
        backup_script = f"""
-- BACKUP DE BASE DE DATOS RFX V2.2
-- Fecha: {datetime.now().isoformat()}
-- Pre-migración a SaaS General

-- Este backup contiene:
-- 1. Esquema completo actual
-- 2. Todos los datos en rfx_v2, companies, requesters, etc.
-- 3. Configuraciones de pricing V2.2

-- INSTRUCCIONES DE RESTORE:
-- 1. Conectar a Supabase Dashboard
-- 2. SQL Editor → Paste este contenido
-- 3. Ejecutar para restaurar estado original

-- NOTA: Este es un backup de referencia
-- Para backup real, usar: pg_dump desde Supabase
"""
        
        backup_sql_path = self.backup_dir / f"database_backup_{self.migration_date}.sql"
        with open(backup_sql_path, 'w') as f:
            f.write(backup_script)
        
        # Crear script de backup de datos críticos
        backup_data_script = self._generate_data_backup_queries()
        
        backup_data_path = self.backup_dir / f"data_backup_queries_{self.migration_date}.sql"
        with open(backup_data_path, 'w') as f:
            f.write(backup_data_script)
        
        logger.info(f"✅ Scripts de backup de BD creados:")
        logger.info(f"   📄 {backup_sql_path}")
        logger.info(f"   📄 {backup_data_path}")
        logger.info("💡 Para backup real ejecutar: pg_dump en Supabase")
    
    def _generate_data_backup_queries(self) -> str:
        """Generar queries para backup de datos críticos"""
        return """
-- QUERIES PARA BACKUP DE DATOS CRÍTICOS
-- Ejecutar en Supabase SQL Editor antes de migración

-- 1. Contar registros actuales
SELECT 'rfx_v2' as table_name, COUNT(*) as count FROM rfx_v2
UNION ALL
SELECT 'companies' as table_name, COUNT(*) as count FROM companies
UNION ALL  
SELECT 'requesters' as table_name, COUNT(*) as count FROM requesters
UNION ALL
SELECT 'suppliers' as table_name, COUNT(*) as count FROM suppliers;

-- 2. Backup de configuraciones críticas
SELECT json_agg(row_to_json(rfx_v2.*)) as rfx_backup 
FROM rfx_v2 
WHERE created_at > CURRENT_DATE - INTERVAL '30 days';

-- 3. Backup de pricing configs
SELECT json_agg(row_to_json(rpc.*)) as pricing_configs_backup
FROM rfx_pricing_configurations rpc 
WHERE is_active = true;

-- 4. Verificar integridad referencial
SELECT 
  COUNT(*) as total_rfx,
  COUNT(DISTINCT company_id) as unique_companies,
  COUNT(DISTINCT requester_id) as unique_requesters
FROM rfx_v2;
"""
    
    def _create_migration_branch(self):
        """Crear branch de migración en Git"""
        logger.info("🌿 Creando branch de migración...")
        
        try:
            # Verificar estado limpio
            result = subprocess.run(
                ["git", "status", "--porcelain"], 
                capture_output=True, text=True, check=True
            )
            
            if result.stdout.strip():
                logger.info("📝 Hay cambios sin commit. Creando commit automático...")
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run([
                    "git", "commit", "-m", 
                    f"Pre-migration snapshot - {self.migration_date}"
                ], check=True)
            
            # Crear tag del estado original
            original_tag = f"v2.2-rfx-original-{self.migration_date}"
            subprocess.run([
                "git", "tag", original_tag,
                "-m", "Estado original antes de migración a SaaS general"
            ], check=True)
            logger.info(f"🏷️ Tag creado: {original_tag}")
            
            # Crear branch de migración
            subprocess.run([
                "git", "checkout", "-b", self.migration_branch
            ], check=True)
            
            logger.info(f"✅ Branch creado y activado: {self.migration_branch}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error en Git: {str(e)}")
            raise
    
    def _analyze_project_dependencies(self) -> Dict[str, List[str]]:
        """Analizar dependencias del proyecto para migración"""
        logger.info("🔍 Analizando dependencias del proyecto...")
        
        dependencies = {
            "files_with_rfx": [],
            "files_with_rfx_v2": [],
            "files_with_suppliers": [],
            "backend_models": [],
            "api_endpoints": [],
            "frontend_components": []
        }
        
        # Buscar archivos con referencias RFX
        for file_path in self.project_root.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                
                if "rfx" in content.lower():
                    dependencies["files_with_rfx"].append(str(file_path))
                    
                if "rfx_v2" in content:
                    dependencies["files_with_rfx_v2"].append(str(file_path))
                    
                if "suppliers" in content and "table" in content:
                    dependencies["files_with_suppliers"].append(str(file_path))
                    
                # Identificar modelos
                if file_path.name.endswith("_models.py"):
                    dependencies["backend_models"].append(str(file_path))
                    
                # Identificar APIs
                if "api/" in str(file_path) and file_path.name.endswith(".py"):
                    dependencies["api_endpoints"].append(str(file_path))
                    
            except Exception as e:
                logger.warning(f"⚠️ No se pudo leer {file_path}: {str(e)}")
        
        # Buscar archivos TypeScript/JavaScript (frontend)
        for file_path in self.project_root.rglob("*.ts"):
            if self._should_skip_file(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                if "rfx" in content.lower() or "RFX" in content:
                    dependencies["frontend_components"].append(str(file_path))
            except:
                pass
        
        # Log resumen
        logger.info("📊 Análisis de dependencias completado:")
        for key, files in dependencies.items():
            if files:
                logger.info(f"   {key}: {len(files)} archivos")
        
        # Guardar análisis detallado
        analysis_path = self.backup_dir / f"dependency_analysis_{self.migration_date}.json"
        with open(analysis_path, 'w') as f:
            json.dump(dependencies, f, indent=2)
        
        logger.info(f"💾 Análisis guardado en: {analysis_path}")
        
        return dependencies
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Determinar si se debe saltar un archivo en el análisis"""
        skip_patterns = [
            "__pycache__",
            ".git",
            "node_modules",
            ".env",
            "migration_backups",
            ".log"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def _generate_migration_plan(self, dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generar plan detallado de migración"""
        logger.info("📋 Generando plan de migración...")
        
        migration_plan = {
            "overview": {
                "total_files_to_modify": (
                    len(dependencies["files_with_rfx"]) +
                    len(dependencies["backend_models"]) +
                    len(dependencies["api_endpoints"])
                ),
                "estimated_duration": "7 días",
                "risk_level": "Medio",
                "rollback_available": True
            },
            "daily_breakdown": {
                "day_1": {
                    "status": "✅ COMPLETADO",
                    "tasks": [
                        "Backup completo",
                        "Análisis de dependencias",
                        "Creación de branch",
                        "Plan de rollback"
                    ]
                },
                "day_2": {
                    "status": "🔄 SIGUIENTE",
                    "tasks": [
                        f"Migrar {len(dependencies['files_with_rfx_v2'])} archivos con rfx_v2",
                        "Crear tabla 'projects'",
                        "Migrar datos rfx_v2 → projects",
                        "Actualizar referencias de BD"
                    ],
                    "estimated_hours": "6-8 horas"
                },
                "day_3": {
                    "status": "⏳ PENDIENTE", 
                    "tasks": [
                        f"Actualizar {len(dependencies['backend_models'])} modelos",
                        "Crear project_models.py",
                        "Backward compatibility",
                        "Tests unitarios"
                    ]
                },
                "day_4": {
                    "status": "⏳ PENDIENTE",
                    "tasks": [
                        f"Actualizar {len(dependencies['api_endpoints'])} endpoints",
                        "Nuevas APIs contextuales",
                        "Mantener APIs legacy"
                    ]
                },
                "day_5": {
                    "status": "⏳ PENDIENTE",
                    "tasks": [
                        "4 tablas nuevas IA contextual",
                        "Índices optimizados",
                        "Vistas útiles"
                    ]
                },
                "day_6": {
                    "status": "⏳ PENDIENTE",
                    "tasks": [
                        "Servicio IA contextual",
                        "Workflow inteligente",
                        "Integración OpenAI"
                    ]
                },
                "day_7": {
                    "status": "⏳ PENDIENTE",
                    "tasks": [
                        "Testing completo",
                        "Performance validation",
                        "Documentación final"
                    ]
                }
            },
            "files_to_modify": dependencies
        }
        
        # Guardar plan
        plan_path = self.backup_dir / f"migration_plan_{self.migration_date}.json"
        with open(plan_path, 'w') as f:
            json.dump(migration_plan, f, indent=2)
        
        logger.info(f"📋 Plan de migración guardado: {plan_path}")
        
        return migration_plan
    
    def _create_rollback_plan(self):
        """Crear plan de rollback detallado"""
        logger.info("🔄 Creando plan de rollback...")
        
        rollback_script = f"""#!/bin/bash
# SCRIPT DE ROLLBACK AUTOMÁTICO
# Fecha de creación: {datetime.now().isoformat()}

echo "🔄 INICIANDO ROLLBACK DE MIGRACIÓN RFX → SAAS"
echo "⚠️  ADVERTENCIA: Esto revertirá TODOS los cambios"
echo "Presiona ENTER para continuar o Ctrl+C para cancelar"
read

echo "📍 Paso 1: Revertir Git al estado original..."
git checkout main
git branch -D {self.migration_branch} 2>/dev/null || true

echo "📍 Paso 2: Restaurar desde tag original..."
git reset --hard v2.2-rfx-original-{self.migration_date}

echo "📍 Paso 3: Limpiar archivos de migración..."
rm -rf migration_backups/

echo "📍 Paso 4: Restaurar dependencias..."
pip install -r requirements.txt

echo "📍 Paso 5: Reiniciar servicios..."
# Opcional: reiniciar backend
# python backend/app.py &

echo "✅ ROLLBACK COMPLETADO"
echo "🎯 Estado restaurado a RFX V2.2 original"
echo "💡 Logs de migración conservados para análisis"
"""
        
        rollback_path = self.backup_dir / "emergency_rollback.sh"
        with open(rollback_path, 'w') as f:
            f.write(rollback_script)
        
        # Hacer ejecutable
        os.chmod(rollback_path, 0o755)
        
        logger.info(f"🔄 Script de rollback creado: {rollback_path}")
        logger.info("💡 Ejecutar con: ./migration_backups/emergency_rollback.sh")
    
    def _run_final_validations(self):
        """Validaciones finales del Día 1"""
        logger.info("✅ Ejecutando validaciones finales...")
        
        validations = []
        
        # 1. Verificar backup existe
        backup_files = list(self.backup_dir.glob("project_backup_*"))
        validations.append({
            "check": "Backup del proyecto",
            "passed": len(backup_files) > 0,
            "details": f"{len(backup_files)} archivos de backup"
        })
        
        # 2. Verificar branch de migración
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], 
                capture_output=True, text=True, check=True
            )
            current_branch = result.stdout.strip()
            validations.append({
                "check": "Branch de migración activo",
                "passed": current_branch == self.migration_branch,
                "details": f"Branch actual: {current_branch}"
            })
        except:
            validations.append({
                "check": "Branch de migración activo", 
                "passed": False,
                "details": "Error al verificar branch"
            })
        
        # 3. Verificar análisis de dependencias
        analysis_files = list(self.backup_dir.glob("dependency_analysis_*"))
        validations.append({
            "check": "Análisis de dependencias",
            "passed": len(analysis_files) > 0,
            "details": f"Archivos analizados: {len(analysis_files)}"
        })
        
        # 4. Verificar plan de migración
        plan_files = list(self.backup_dir.glob("migration_plan_*"))
        validations.append({
            "check": "Plan de migración generado",
            "passed": len(plan_files) > 0,
            "details": f"Plan disponible: {len(plan_files) > 0}"
        })
        
        # 5. Verificar script de rollback
        rollback_script = self.backup_dir / "emergency_rollback.sh"
        validations.append({
            "check": "Script de rollback",
            "passed": rollback_script.exists(),
            "details": f"Rollback disponible: {rollback_script.exists()}"
        })
        
        # Log validaciones
        logger.info("📊 RESULTADOS DE VALIDACIÓN:")
        all_passed = True
        for validation in validations:
            status = "✅" if validation["passed"] else "❌"
            logger.info(f"   {status} {validation['check']}: {validation['details']}")
            if not validation["passed"]:
                all_passed = False
        
        if not all_passed:
            raise RuntimeError("❌ Algunas validaciones fallaron. Revisar logs.")
            
        logger.info("✅ Todas las validaciones pasaron correctamente")
    
    def _generate_day_1_summary(self, migration_plan: Dict[str, Any]):
        """Generar resumen del Día 1 y siguientes pasos"""
        logger.info("📋 GENERANDO RESUMEN DEL DÍA 1...")
        
        summary = f"""
🎉 RESUMEN DÍA 1: MIGRACIÓN RFX → SAAS GENERAL
{'=' * 60}

✅ COMPLETADO EXITOSAMENTE:
   📦 Backup completo del proyecto creado
   🌿 Branch '{self.migration_branch}' creado y activo
   🔍 Análisis de dependencias completado
   📋 Plan de migración de 7 días generado
   🔄 Script de rollback disponible
   ✅ Todas las validaciones pasaron

📊 ESTADÍSTICAS:
   🔧 Archivos a modificar: {migration_plan['overview']['total_files_to_modify']}
   ⏱️  Duración estimada: {migration_plan['overview']['estimated_duration']}
   🎯 Nivel de riesgo: {migration_plan['overview']['risk_level']}

🚀 SIGUIENTE PASO: DÍA 2
   📅 Fecha recomendada: Mañana
   ⏱️  Tiempo estimado: 6-8 horas
   🎯 Objetivo: Migración de esquema de base de datos
   
   Para continuar ejecutar:
   $ python day_2_migration.py

🔄 ROLLBACK DISPONIBLE:
   Si algo sale mal: ./migration_backups/emergency_rollback.sh
   
🎯 PRÓXIMOS 6 DÍAS:
   Día 2: Migración BD (rfx_v2 → projects)
   Día 3: Modelos Python actualizados
   Día 4: APIs generalizadas  
   Día 5: 4 tablas IA contextual
   Día 6: Servicios IA inteligente
   Día 7: Testing y validación final

📁 ARCHIVOS GENERADOS:
   {self.backup_dir}/
   ├── project_backup_{self.migration_date}.tar.gz
   ├── dependency_analysis_{self.migration_date}.json
   ├── migration_plan_{self.migration_date}.json
   └── emergency_rollback.sh

💡 NOTAS IMPORTANTES:
   • Branch actual: {self.migration_branch}
   • Backup original disponible
   • Rollback automático configurado
   • Todo versionado en Git

🎉 ¡DÍA 1 COMPLETADO! LISTO PARA DÍA 2
"""
        
        # Guardar resumen
        summary_path = self.backup_dir / f"day_1_summary_{self.migration_date}.md"
        with open(summary_path, 'w') as f:
            f.write(summary)
        
        # Log resumen
        print(summary)
        logger.info(f"📄 Resumen completo guardado: {summary_path}")
    
    def _emergency_rollback(self):
        """Rollback automático en caso de error"""
        logger.error("🔄 Ejecutando rollback de emergencia...")
        
        try:
            # Volver a main
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "branch", "-D", self.migration_branch], 
                         check=True, capture_output=True)
            logger.info("✅ Rollback Git completado")
            
        except Exception as rollback_error:
            logger.error(f"❌ Error en rollback: {str(rollback_error)}")
            logger.error("🔧 Rollback manual requerido:")
            logger.error("   git checkout main")
            logger.error(f"   git branch -D {self.migration_branch}")


def main():
    """
    Función principal - Ejecutar migración Día 1
    """
    try:
        migration = Day1Migration()
        migration.run_complete_day_1()
        
        print("\n🎉 ¡DÍA 1 COMPLETADO EXITOSAMENTE!")
        print("🚀 Para continuar con Día 2:")
        print("   python day_2_migration.py")
        
    except KeyboardInterrupt:
        print("\n⚠️ Migración interrumpida por usuario")
        print("🔄 Para rollback: ./migration_backups/emergency_rollback.sh")
    except Exception as e:
        print(f"\n❌ Error en migración: {str(e)}")
        print("🔄 Rollback automático ejecutado")
        print("📋 Revisar logs: migration_day_1.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
