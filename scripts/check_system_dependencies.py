#!/usr/bin/env python3
"""
🔍 Verificador de Dependencias del Sistema
Verifica que todas las dependencias del sistema operativo estén instaladas
"""
import subprocess
import sys
import platform


def check_command(command: str, name: str, alternative_commands: list = None) -> bool:
    """Verifica si un comando está disponible en el sistema"""
    commands_to_try = [command]
    if alternative_commands:
        commands_to_try.extend(alternative_commands)
    
    for cmd in commands_to_try:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ {name} está instalado ({cmd})")
                print(f"   Versión: {result.stdout.strip().split()[0] if result.stdout else 'N/A'}")
                return True
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"⚠️  Error verificando {name} con {cmd}: {e}")
            continue
    
    print(f"❌ {name} NO está instalado")
    return False


def check_python_package(package: str) -> bool:
    """Verifica si un paquete Python está instalado"""
    try:
        __import__(package)
        print(f"✅ {package} (Python) está instalado")
        return True
    except ImportError:
        print(f"❌ {package} (Python) NO está instalado")
        return False


def get_install_instructions(os_name: str) -> dict:
    """Retorna instrucciones de instalación según el sistema operativo"""
    instructions = {
        'Darwin': {  # macOS
            'poppler': 'brew install poppler',
            'cairo': 'brew install cairo'
        },
        'Linux': {
            'poppler': 'sudo apt-get install -y poppler-utils  # Ubuntu/Debian\nsudo yum install -y poppler-utils  # CentOS/RHEL',
            'cairo': 'sudo apt-get install -y libcairo2-dev  # Ubuntu/Debian\nsudo yum install -y cairo-devel  # CentOS/RHEL'
        },
        'Windows': {
            'poppler': 'Descargar desde: https://github.com/oschwartz10612/poppler-windows/releases',
            'cairo': 'Usar solo svglib (no requiere Cairo en Windows)'
        }
    }
    return instructions.get(os_name, instructions['Linux'])


def main():
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE DEPENDENCIAS DEL SISTEMA")
    print("=" * 60)
    print()
    
    os_name = platform.system()
    print(f"Sistema Operativo: {os_name}")
    print()
    
    # Track individual dependency status
    dependencies_status = {}
    
    # Verificar Poppler (requerido para PDF)
    print("📄 Verificando Poppler (para conversión PDF → imagen):")
    
    # Comandos alternativos para detectar Poppler en diferentes sistemas
    poppler_commands = [
        'pdfinfo',  # Comando estándar
        '/opt/homebrew/bin/pdfinfo',  # Homebrew en Apple Silicon
        '/usr/local/bin/pdfinfo',     # Homebrew en Intel Mac
        'pdftoppm'  # Comando alternativo de Poppler
    ]
    
    poppler_ok = check_command('pdfinfo', 'Poppler', poppler_commands[1:])
    if not poppler_ok:
        instructions = get_install_instructions(os_name)
        print(f"   💡 Instalar con: {instructions['poppler']}")
        print(f"   🔍 Verificando rutas comunes de Homebrew...")
        
        # Verificación adicional con which para Homebrew
        try:
            which_result = subprocess.run(['which', 'pdfinfo'], capture_output=True, text=True)
            if which_result.returncode == 0 and which_result.stdout.strip():
                poppler_path = which_result.stdout.strip()
                print(f"   ℹ️  Poppler encontrado en: {poppler_path}")
                # Intentar verificar versión directamente
                version_result = subprocess.run([poppler_path, '--version'], 
                                               capture_output=True, text=True)
                if version_result.returncode == 0:
                    print(f"   ✅ Poppler está funcionando correctamente")
                    if version_result.stdout:
                        version_info = version_result.stdout.strip().split('\n')[0]
                        print(f"   Versión: {version_info}")
                    poppler_ok = True
                else:
                    # Intentar con otro comando de Poppler
                    test_result = subprocess.run([poppler_path, '-v'], 
                                                capture_output=True, text=True)
                    if test_result.returncode == 0:
                        print(f"   ✅ Poppler está funcionando correctamente")
                        poppler_ok = True
        except Exception as e:
            print(f"   ⚠️  Error en verificación adicional: {e}")
    
    dependencies_status['poppler'] = poppler_ok        
    print()
    
    # Verificar paquetes Python críticos
    print("🐍 Verificando paquetes Python:")
    
    packages_to_check = [
        ('pdf2image', 'Conversión de PDF a imagen'),
        ('PIL', 'Procesamiento de imágenes (Pillow)'),
        ('svglib', 'Conversión de SVG (fallback)')
    ]
    
    for package, description in packages_to_check:
        print(f"   {description}:")
        package_ok = check_python_package(package)
        dependencies_status[package] = package_ok
        if not package_ok:
            print(f"      💡 Instalar con: pip install -r requirements.txt")
    
    # Verificar cairosvg (opcional, tiene fallback)
    print()
    print("🎨 Verificando dependencias opcionales (tienen fallback):")
    print("   Conversión de SVG (cairosvg):")
    cairo_ok = check_python_package('cairosvg')
    if not cairo_ok:
        print("      ℹ️  No es crítico - se usará svglib como alternativa")
        instructions = get_install_instructions(os_name)
        print(f"      💡 Para instalar Cairo: {instructions['cairo']}")
        print(f"      💡 Luego: pip install cairosvg")
    
    print()
    print("=" * 60)
    
    # Evaluar dependencias críticas
    critical_deps = ['poppler', 'pdf2image', 'PIL']
    critical_missing = [dep for dep in critical_deps if not dependencies_status.get(dep, False)]
    
    if not critical_missing:
        print("✅ TODAS LAS DEPENDENCIAS CRÍTICAS ESTÁN INSTALADAS")
        print("=" * 60)
        print()
        print("🎯 Estado de dependencias:")
        print(f"   📄 Poppler (PDF processing): {'✅' if dependencies_status.get('poppler') else '❌'}")
        print(f"   🐍 pdf2image: {'✅' if dependencies_status.get('pdf2image') else '❌'}")
        print(f"   🖼️  PIL (Pillow): {'✅' if dependencies_status.get('PIL') else '❌'}")
        print(f"   🎨 svglib: {'✅' if dependencies_status.get('svglib') else '❌'}")
        print(f"   🎨 cairosvg (opcional): {'✅' if cairo_ok else '❌'}")
        return 0
    else:
        print("⚠️  FALTAN ALGUNAS DEPENDENCIAS CRÍTICAS")
        print("=" * 60)
        print()
        print("❌ Dependencias críticas faltantes:")
        for dep in critical_missing:
            print(f"   - {dep}")
        print()
        print("📖 Para más información, consulta: INSTALL_SYSTEM_DEPENDENCIES.md")
        return 1


if __name__ == '__main__':
    sys.exit(main())
