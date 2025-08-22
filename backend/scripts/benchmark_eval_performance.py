#!/usr/bin/env python3
"""
🏁 Benchmark de Performance - Sistema de Evaluación Inteligente RFX

Mide el impacto en performance del sistema de evaluación inteligente,
comparando tiempos con/sin evaluaciones y proporcionando métricas detalladas.

Autor: AI Assistant
Fecha: 2025-01-31
"""

import os
import sys
import time
import statistics
import traceback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from datetime import datetime
from typing import Dict, List, Tuple, Any
from unittest.mock import patch
from dataclasses import dataclass

# Configurar environment para testing
os.environ.update({
    'SUPABASE_URL': 'https://test.supabase.co',
    'SUPABASE_ANON_KEY': 'test_key_123',
    'OPENAI_API_KEY': 'sk-test1234567890abcdef1234567890abcdef1234567890abcdef',
    'ENVIRONMENT': 'testing',
    'ENABLE_EVALS': 'true',
    'EVAL_DEBUG_MODE': 'false'
})

# Agregar path del proyecto root para imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

@dataclass
class BenchmarkResult:
    """Resultado de benchmark para un componente"""
    component: str
    iterations: int
    times: List[float]
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    memory_usage_mb: float
    success_rate: float

@dataclass
class PerformanceComparison:
    """Comparación de performance con/sin evaluaciones"""
    without_evals: BenchmarkResult
    with_evals: BenchmarkResult
    performance_impact_percent: float
    overhead_ms: float

class EvaluationBenchmark:
    """Benchmark completo del sistema de evaluación inteligente"""
    
    def __init__(self):
        self.iterations = 20  # Número de iteraciones para estadísticas sólidas
        self.warmup_iterations = 3  # Iteraciones de calentamiento
        
        # Datos de test por dominio
        self.test_data = {
            'catering_simple': {
                'cliente': 'Eventos Gourmet',
                'email': 'info@eventosgourmet.com',
                'productos': [
                    {'nombre': 'Tequeños fritos', 'cantidad': 80, 'unidad': 'unidades'},
                    {'nombre': 'Empanadas de queso', 'cantidad': 50, 'unidad': 'unidades'}
                ],
                'fecha': '2025-03-15',
                'hora_entrega': '18:00',
                'lugar': 'Hotel Plaza - Salón Principal'
            },
            'catering_completo': {
                'cliente': 'Corporación Premium Events S.A.',
                'email': 'eventos@premiumevents.com',
                'contacto': 'María González',
                'telefono': '+58-212-555-0123',
                'productos': [
                    {'nombre': 'Tequeños venezolanos premium', 'cantidad': 150, 'unidad': 'unidades'},
                    {'nombre': 'Empanadas de pollo desmechado', 'cantidad': 100, 'unidad': 'unidades'},
                    {'nombre': 'Shot de chocolate belga', 'cantidad': 120, 'unidad': 'unidades'},
                    {'nombre': 'Café gourmet colombiano', 'cantidad': 5, 'unidad': 'servicios'},
                    {'nombre': 'Agua mineral premium', 'cantidad': 200, 'unidad': 'botellas'},
                    {'nombre': 'Refrescos variados', 'cantidad': 150, 'unidad': 'latas'}
                ],
                'fecha': '2025-04-20',
                'hora_entrega': '19:30',
                'lugar': 'Centro Empresarial Torre Miranda - Piso 35 - Auditorio Principal',
                'presupuesto': 4500,
                'descripcion': 'Evento corporativo de lanzamiento de producto con catering premium venezolano para 80 invitados VIP'
            },
            'construction': {
                'cliente': 'Constructora Moderna C.A.',
                'email': 'proyectos@constructoramoderna.com',
                'productos': [
                    {'nombre': 'Cemento Portland tipo I', 'cantidad': 100, 'unidad': 'sacos'},
                    {'nombre': 'Acero de refuerzo 3/8"', 'cantidad': 2000, 'unidad': 'kg'},
                    {'nombre': 'Bloques de concreto 15x20x40', 'cantidad': 500, 'unidad': 'unidades'},
                    {'nombre': 'Pintura impermeabilizante', 'cantidad': 50, 'unidad': 'galones'}
                ],
                'fecha': '2025-02-28',
                'hora_entrega': '08:00',
                'lugar': 'Obra Residencial Las Mercedes - Caracas',
                'presupuesto': 25000
            },
            'it_services': {
                'cliente': 'TechSolutions Venezuela',
                'email': 'desarrollo@techsolutions.ve',
                'productos': [
                    {'nombre': 'Desarrollo aplicación web', 'cantidad': 1, 'unidad': 'proyecto'},
                    {'nombre': 'Base de datos PostgreSQL', 'cantidad': 1, 'unidad': 'instalación'},
                    {'nombre': 'Servidor cloud AWS', 'cantidad': 12, 'unidad': 'meses'},
                    {'nombre': 'Licencias software', 'cantidad': 10, 'unidad': 'usuarios'}
                ],
                'fecha': '2025-05-01',
                'lugar': 'Oficinas TechSolutions - Caracas',
                'descripcion': 'Sistema de gestión empresarial con tecnología moderna'
            }
        }
        
        print(f"🏁 BENCHMARK SISTEMA EVALUACIÓN INTELIGENTE")
        print(f"{'='*70}")
        print(f"📊 Configuración:")
        print(f"  🔄 Iteraciones: {self.iterations}")
        print(f"  🔥 Warmup: {self.warmup_iterations}")
        print(f"  📋 Datasets de test: {len(self.test_data)}")
        if PSUTIL_AVAILABLE:
            print(f"  💾 Memoria disponible: {psutil.virtual_memory().available / 1024 / 1024:.1f} MB")
            print(f"  🖥️ CPU cores: {psutil.cpu_count()}")
        else:
            print(f"  💾 Memoria: psutil no disponible")
            print(f"  🖥️ CPU: info no disponible")

    def get_memory_usage(self) -> float:
        """Obtener uso actual de memoria en MB"""
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        else:
            return 0.0  # Fallback cuando psutil no está disponible

    def benchmark_component(self, component_name: str, func: callable, *args, **kwargs) -> BenchmarkResult:
        """Benchmark de un componente específico"""
        print(f"\n🔍 Benchmarking {component_name}...")
        
        times = []
        errors = 0
        initial_memory = self.get_memory_usage()
        
        # Warmup
        for _ in range(self.warmup_iterations):
            try:
                func(*args, **kwargs)
            except Exception:
                pass
        
        # Benchmark real
        for i in range(self.iterations):
            try:
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                
                if i % 5 == 0:
                    print(f"  📈 Progress: {i}/{self.iterations} - Current: {execution_time*1000:.2f}ms")
                    
            except Exception as e:
                errors += 1
                print(f"  ❌ Error en iteración {i}: {e}")
        
        final_memory = self.get_memory_usage()
        memory_usage = final_memory - initial_memory
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        else:
            avg_time = min_time = max_time = std_dev = 0.0
        
        success_rate = (len(times) / self.iterations) * 100
        
        result = BenchmarkResult(
            component=component_name,
            iterations=self.iterations,
            times=times,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            std_dev=std_dev,
            memory_usage_mb=memory_usage,
            success_rate=success_rate
        )
        
        print(f"  ✅ {component_name} completado:")
        print(f"    ⏱️ Tiempo promedio: {avg_time*1000:.3f}ms")
        print(f"    📊 Min/Max: {min_time*1000:.3f}ms / {max_time*1000:.3f}ms")
        print(f"    📈 Std dev: {std_dev*1000:.3f}ms")
        print(f"    ✅ Success rate: {success_rate:.1f}%")
        print(f"    💾 Memory delta: {memory_usage:.2f}MB")
        
        return result

    def benchmark_domain_detection(self) -> BenchmarkResult:
        """Benchmark detección de dominio"""
        from backend.services.domain_detector import detect_rfx_domain
        
        def run_detection():
            # Rotar entre diferentes tipos de datos
            data_keys = list(self.test_data.keys())
            test_data = self.test_data[data_keys[int(time.time() * 1000) % len(data_keys)]]
            return detect_rfx_domain(test_data)
        
        return self.benchmark_component("Domain Detection", run_detection)

    def benchmark_generic_evaluators(self) -> BenchmarkResult:
        """Benchmark evaluadores genéricos"""
        from backend.evals.generic_evals import (
            evaluate_completeness, 
            evaluate_format_validation, 
            evaluate_consistency
        )
        
        def run_generic_evaluators():
            test_data = self.test_data['catering_completo']
            results = []
            results.append(evaluate_completeness(test_data))
            results.append(evaluate_format_validation(test_data))
            results.append(evaluate_consistency(test_data))
            return results
        
        return self.benchmark_component("Generic Evaluators", run_generic_evaluators)

    def benchmark_specific_evaluators(self) -> BenchmarkResult:
        """Benchmark evaluadores específicos"""
        from backend.evals.extraction_evals import (
            evaluate_product_count,
            evaluate_product_quality
        )
        
        def run_specific_evaluators():
            test_data = self.test_data['catering_completo']
            results = []
            results.append(evaluate_product_count(test_data))
            results.append(evaluate_product_quality(test_data))
            return results
        
        return self.benchmark_component("Specific Evaluators (Catering)", run_specific_evaluators)

    def benchmark_evaluation_orchestrator(self) -> BenchmarkResult:
        """Benchmark orquestador completo"""
        from backend.services.evaluation_orchestrator import evaluate_rfx_intelligently
        
        def run_orchestrator():
            # Alternar entre diferentes tipos de datos
            data_keys = list(self.test_data.keys())
            test_data = self.test_data[data_keys[int(time.time() * 1000) % len(data_keys)]]
            return evaluate_rfx_intelligently(test_data)
        
        return self.benchmark_component("Evaluation Orchestrator", run_orchestrator)

    def benchmark_rfx_processor_simulation(self, with_evals: bool) -> BenchmarkResult:
        """Simular procesamiento RFX con/sin evaluaciones"""
        
        def simulate_rfx_processing():
            # Simular procesamiento RFX realista
            # PDF extraction: ~50ms, AI processing: ~200ms, validation: ~10ms
            time.sleep(0.260)  # 260ms simulando procesamiento real
            
            if with_evals:
                # Simular evaluación inteligente
                from backend.services.evaluation_orchestrator import evaluate_rfx_intelligently
                test_data = self.test_data['catering_completo']
                eval_result = evaluate_rfx_intelligently(test_data)
                
                # Simular creación de metadata
                metadata = {
                    'intelligent_evaluation': {
                        'consolidated_score': eval_result['consolidated_score'],
                        'domain': eval_result['domain_detection']['primary_domain']
                    }
                }
                return metadata
            else:
                # Solo metadata básica
                return {'basic_metadata': True}
        
        component_name = f"RFX Processing ({'WITH' if with_evals else 'WITHOUT'} Evals)"
        return self.benchmark_component(component_name, simulate_rfx_processing)

    def compare_with_without_evals(self) -> PerformanceComparison:
        """Comparar performance con y sin evaluaciones"""
        print(f"\n{'='*70}")
        print(f"🔄 COMPARACIÓN CON/SIN EVALUACIONES")
        print(f"{'='*70}")
        
        # Benchmark sin evaluaciones
        with patch('backend.core.feature_flags.FeatureFlags.evals_enabled', return_value=False):
            without_evals = self.benchmark_rfx_processor_simulation(with_evals=False)
        
        # Benchmark con evaluaciones  
        with patch('backend.core.feature_flags.FeatureFlags.evals_enabled', return_value=True):
            with_evals = self.benchmark_rfx_processor_simulation(with_evals=True)
        
        # Calcular impacto
        if without_evals.avg_time > 0:
            performance_impact = ((with_evals.avg_time - without_evals.avg_time) / without_evals.avg_time) * 100
        else:
            performance_impact = 0.0
        
        overhead_ms = (with_evals.avg_time - without_evals.avg_time) * 1000
        
        comparison = PerformanceComparison(
            without_evals=without_evals,
            with_evals=with_evals,
            performance_impact_percent=performance_impact,
            overhead_ms=overhead_ms
        )
        
        print(f"\n📊 RESULTADOS DE COMPARACIÓN:")
        print(f"  🚫 Sin evaluaciones: {without_evals.avg_time*1000:.3f}ms ± {without_evals.std_dev*1000:.3f}ms")
        print(f"  ✅ Con evaluaciones: {with_evals.avg_time*1000:.3f}ms ± {with_evals.std_dev*1000:.3f}ms")
        print(f"  📈 Overhead: {overhead_ms:.3f}ms")
        print(f"  📊 Impacto en performance: {performance_impact:.2f}%")
        
        return comparison

    def run_complete_benchmark(self) -> Dict[str, Any]:
        """Ejecutar benchmark completo"""
        
        start_time = datetime.now()
        print(f"🚀 Iniciando benchmark completo - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {}
        
        try:
            # 1. Benchmark componentes individuales
            print(f"\n🔧 FASE 1: COMPONENTES INDIVIDUALES")
            print(f"{'='*50}")
            
            results['domain_detection'] = self.benchmark_domain_detection()
            results['generic_evaluators'] = self.benchmark_generic_evaluators()
            results['specific_evaluators'] = self.benchmark_specific_evaluators()
            results['orchestrator'] = self.benchmark_evaluation_orchestrator()
            
            # 2. Comparación con/sin evaluaciones
            print(f"\n🔧 FASE 2: COMPARACIÓN IMPACTO")
            print(f"{'='*50}")
            
            results['comparison'] = self.compare_with_without_evals()
            
            # 3. Generar reporte final
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results['benchmark_metadata'] = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'iterations': self.iterations,
                'total_tests': sum(r.iterations for r in results.values() if hasattr(r, 'iterations'))
            }
            
            self.generate_final_report(results)
            
            return results
            
        except Exception as e:
            print(f"\n❌ ERROR EN BENCHMARK: {e}")
            traceback.print_exc()
            return {'error': str(e)}

    def generate_final_report(self, results: Dict[str, Any]):
        """Generar reporte final con criterios de éxito"""
        
        print(f"\n{'='*70}")
        print(f"📋 REPORTE FINAL DE PERFORMANCE")
        print(f"{'='*70}")
        
        # Resumen ejecutivo
        comparison = results['comparison']
        
        print(f"\n🎯 RESUMEN EJECUTIVO:")
        print(f"  ⏱️ Overhead total: {comparison.overhead_ms:.3f}ms")
        print(f"  📊 Impacto performance: {comparison.performance_impact_percent:.2f}%")
        print(f"  ✅ Success rate promedio: {results['orchestrator'].success_rate:.1f}%")
        print(f"  💾 Memoria adicional: {results['orchestrator'].memory_usage_mb:.2f}MB")
        
        # Desglose por componente
        print(f"\n🔧 DESGLOSE POR COMPONENTE:")
        components = ['domain_detection', 'generic_evaluators', 'specific_evaluators', 'orchestrator']
        
        for component in components:
            if component in results:
                result = results[component]
                print(f"  📦 {result.component}:")
                print(f"    ⏱️ Tiempo: {result.avg_time*1000:.3f}ms ± {result.std_dev*1000:.3f}ms")
                print(f"    🎯 Range: {result.min_time*1000:.3f}ms - {result.max_time*1000:.3f}ms") 
                print(f"    ✅ Success: {result.success_rate:.1f}%")
        
        # Criterios de éxito
        print(f"\n🎯 CRITERIOS DE ÉXITO:")
        
        criteria_results = []
        
        # Criterio 1: Overhead < 10ms
        overhead_ok = comparison.overhead_ms < 10.0
        criteria_results.append(overhead_ok)
        status = "✅ PASS" if overhead_ok else "❌ FAIL"
        print(f"  {status} Overhead < 10ms: {comparison.overhead_ms:.3f}ms")
        
        # Criterio 2: Impacto < 3% (realista para baseline de ~260ms)
        impact_ok = comparison.performance_impact_percent < 3.0
        criteria_results.append(impact_ok)
        status = "✅ PASS" if impact_ok else "❌ FAIL"
        print(f"  {status} Impacto < 3%: {comparison.performance_impact_percent:.2f}%")
        
        # Criterio 3: Orchestrator < 10ms promedio
        orchestrator_ok = results['orchestrator'].avg_time < 0.010
        criteria_results.append(orchestrator_ok)
        status = "✅ PASS" if orchestrator_ok else "❌ FAIL"
        print(f"  {status} Orchestrator < 10ms: {results['orchestrator'].avg_time*1000:.3f}ms")
        
        # Criterio 4: Success rate > 95%
        success_ok = results['orchestrator'].success_rate > 95.0
        criteria_results.append(success_ok)
        status = "✅ PASS" if success_ok else "❌ FAIL"
        print(f"  {status} Success rate > 95%: {results['orchestrator'].success_rate:.1f}%")
        
        # Criterio 5: Memoria < 50MB
        memory_ok = results['orchestrator'].memory_usage_mb < 50.0
        criteria_results.append(memory_ok)
        status = "✅ PASS" if memory_ok else "❌ FAIL"
        print(f"  {status} Memoria < 50MB: {results['orchestrator'].memory_usage_mb:.2f}MB")
        
        # Resultado final
        all_passed = all(criteria_results)
        passed_count = sum(criteria_results)
        total_criteria = len(criteria_results)
        
        print(f"\n🏆 RESULTADO FINAL:")
        if all_passed:
            print(f"  🎉 ¡ÉXITO COMPLETO! {passed_count}/{total_criteria} criterios pasados")
            print(f"  ✅ Sistema listo para producción")
            print(f"  🚀 Performance excelente verificada")
        else:
            print(f"  ⚠️ {passed_count}/{total_criteria} criterios pasados")
            print(f"  🔧 Revisar componentes que no cumplen criterios")
        
        # Metadata del benchmark
        metadata = results['benchmark_metadata']
        print(f"\n📊 METADATA DEL BENCHMARK:")
        print(f"  ⏱️ Duración total: {metadata['duration_seconds']:.2f}s")
        print(f"  🔄 Total de tests: {metadata['total_tests']:,}")
        print(f"  📅 Timestamp: {metadata['end_time']}")
        
        return all_passed

def main():
    """Función principal del benchmark"""
    
    print(f"🏁 INICIANDO BENCHMARK DE PERFORMANCE")
    print(f"🎯 Sistema de Evaluación Inteligente RFX")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Verificar dependencias
        print(f"\n🔧 Verificando dependencias...")
        
        from backend.core.feature_flags import FeatureFlags
        from backend.services.evaluation_orchestrator import evaluate_rfx_intelligently
        from backend.services.domain_detector import detect_rfx_domain
        
        print(f"  ✅ Todas las dependencias disponibles")
        print(f"  🚩 Feature flags: {FeatureFlags.get_enabled_features()}")
        
        # Ejecutar benchmark
        benchmark = EvaluationBenchmark()
        results = benchmark.run_complete_benchmark()
        
        if 'error' in results:
            print(f"\n❌ Benchmark falló: {results['error']}")
            return 1
        
        # Determinar código de salida
        comparison = results.get('comparison')
        if comparison and comparison.performance_impact_percent < 15.0:
            print(f"\n✅ Benchmark completado exitosamente")
            return 0
        else:
            print(f"\n⚠️ Benchmark completado con advertencias de performance")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error ejecutando benchmark: {e}")
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)