#!/bin/bash

# 🚀 AI-RFX Backend PM2 Startup Script
# Script para facilitar el inicio de la aplicación con PM2

set -e  # Exit on any error

echo "🚀 AI-RFX Backend PM2 Startup Script"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if PM2 is installed
check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        print_error "PM2 no está instalado."
        print_info "Instala PM2 con: npm install -g pm2"
        exit 1
    fi
    print_status "PM2 está instalado"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        print_error "Virtual environment no encontrado en ./venv"
        print_info "Crea el virtual environment con: python3 -m venv venv"
        exit 1
    fi
    print_status "Virtual environment encontrado"
}

# Check if .env file exists and validate AI-RFX variables
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file no encontrado"
        print_info "Crea un archivo .env con las variables del proyecto AI-RFX:"
        print_info "⚠️  Variables REQUERIDAS:"
        print_info "- SUPABASE_URL (Base de datos principal)"
        print_info "- SUPABASE_ANON_KEY (Clave de acceso a Supabase)"
        print_info "- OPENAI_API_KEY (API para procesamiento de IA)"
        print_info "- SECRET_KEY (Clave secreta de Flask)"
        print_info ""
        print_info "🎨 Variables del SISTEMA:"
        print_info "- ENVIRONMENT (development/staging/production)"
        print_info "- DEBUG (true/false)"
        print_info "- HOST, PORT (configuración del servidor)"
        print_info ""
        print_info "🤖 FEATURE FLAGS (AI Agent Improvements):"
        print_info "- ENABLE_EVALS (activar evaluaciones)"
        print_info "- ENABLE_META_PROMPTING (meta prompting)"
        print_info "- ENABLE_VERTICAL_AGENT (agente vertical)"
        print_info "- EVAL_DEBUG_MODE (debug de evaluaciones)"
        print_info ""
        print_info "📋 Puedes copiar desde: env-variables.txt"
        
        # Ask if user wants to continue anyway
        read -p "¿Continuar sin .env file? (y/N): " continue_without_env
        if [[ ! $continue_without_env =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_status ".env file encontrado"
        
        # Validate specific AI-RFX variables if .env exists
        validate_ai_rfx_variables
    fi
}

# Validate specific AI-RFX variables
validate_ai_rfx_variables() {
    print_info "Validando variables específicas del proyecto AI-RFX..."
    
    local missing_vars=()
    local required_vars=("SUPABASE_URL" "SUPABASE_ANON_KEY" "OPENAI_API_KEY" "SECRET_KEY")
    
    # Check required variables
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env 2>/dev/null; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_warning "Variables REQUERIDAS faltantes en .env:"
        for var in "${missing_vars[@]}"; do
            print_error "   - $var"
        done
        return 1
    fi
    
    # Check feature flags (optional but inform)
    local feature_flags=("ENABLE_EVALS" "ENABLE_META_PROMPTING" "ENABLE_VERTICAL_AGENT" "EVAL_DEBUG_MODE")
    local missing_flags=()
    
    for flag in "${feature_flags[@]}"; do
        if ! grep -q "^$flag=" .env 2>/dev/null; then
            missing_flags+=("$flag")
        fi
    done
    
    if [ ${#missing_flags[@]} -gt 0 ]; then
        print_warning "Feature flags no configurados (opcional):"
        for flag in "${missing_flags[@]}"; do
            print_info "   - $flag"
        done
    fi
    
    print_status "Variables del proyecto AI-RFX validadas"
    return 0
}

# Create logs directory if it doesn't exist
create_logs_dir() {
    if [ ! -d "logs" ]; then
        mkdir -p logs
        print_status "Directorio logs creado"
    else
        print_status "Directorio logs existe"
    fi
}

# Function to start development server
start_dev() {
    print_info "Iniciando servidor de desarrollo..."
    pm2 start ecosystem.dev.config.js
    print_status "Servidor de desarrollo iniciado (Ubuntu)"
    print_info "🌐 Servidor disponible en: http://localhost:3186"
    print_info "💚 Health check: http://localhost:3186/health"
    print_info "📄 Health detallado: http://localhost:3186/health/detailed"
    print_info ""
    print_info "🤖 Endpoints AI-RFX principales:"
    print_info "   POST /api/rfx/process        - Procesar documentos RFX"
    print_info "   POST /api/proposals/generate - Generar propuestas"
    print_info "   GET  /api/pricing/presets    - Presets de pricing"
    print_info "   GET  /api/rfx/history        - Historial RFX"
    print_info ""
    print_info "📊 Feature Flags activos: ENABLE_EVALS=true, EVAL_DEBUG_MODE=true"
}

# Function to start production server
start_prod() {
    print_info "Iniciando servidor de producción con Gunicorn..."
    
    # Check if gunicorn is installed in venv
    if ! ./venv/bin/pip show gunicorn &> /dev/null; then
        print_warning "Gunicorn no está instalado en el virtual environment"
        print_info "Instalando Gunicorn..."
        ./venv/bin/pip install gunicorn
    fi
    
    pm2 start ecosystem.prod.config.js
    print_status "Servidor de producción iniciado con Gunicorn (Ubuntu)"
    print_info "🌐 Servidor disponible en: http://localhost:3187"
    print_info "💚 Health check: http://localhost:3187/health"
    print_info "📄 Health detallado: http://localhost:3187/health/detailed"
    print_info "📊 Gunicorn workers: 2 (configurables en ecosystem.config.js)"
    print_info "⚠️  Recuerda cambiar SECRET_KEY para producción"
}

# Function to start staging server
start_staging() {
    print_info "Iniciando servidor de staging..."
    print_warning "⚠️  Staging usa la configuración de desarrollo con puerto 3186"
    print_info "💡 Para staging real, considera crear ecosystem.staging.config.js"
    pm2 start ecosystem.dev.config.js
    print_status "Servidor de staging iniciado (usando config dev)"
    print_info "🌐 Servidor disponible en: http://localhost:3186"
    print_info "💚 Health check: http://localhost:3186/health"
    print_info "🧪 Testing: ENABLE_EVALS y EVAL_DEBUG_MODE activados"
}

# Function to show status
show_status() {
    print_info "Estado actual de los procesos PM2:"
    pm2 status
}

# Function to show logs
show_logs() {
    local app_name=${1:-"ai-rfx-backend-dev"}
    print_info "Mostrando logs para: $app_name"
    pm2 logs "$app_name"
}

# Function to stop all processes
stop_all() {
    print_info "Deteniendo todos los procesos AI-RFX..."
    pm2 stop ai-rfx-backend-dev 2>/dev/null || true
    pm2 stop ai-rfx-backend-prod 2>/dev/null || true
    pm2 stop ai-rfx-backend-staging 2>/dev/null || true
    print_status "Todos los procesos detenidos"
}

# Function to restart process
restart_app() {
    local app_name=${1:-"ai-rfx-backend-dev"}
    print_info "Reiniciando: $app_name"
    pm2 restart "$app_name"
    print_status "$app_name reiniciado"
}

# Function to test AI-RFX endpoints
test_endpoints() {
    print_info "Probando endpoints AI-RFX..."
    print_warning "💡 Testing en Ubuntu Dev (puerto 3186)"
    print_info "   Para Local Dev usar: http://localhost:5001"
    print_info "   Para Ubuntu Prod usar: http://localhost:3187"
    
    # Test health check
    print_info "1. Health Check Básico:"
    curl -s http://localhost:3186/health | jq '.' 2>/dev/null || curl -s http://localhost:3186/health
    
    echo ""
    print_info "2. Health Check Detallado:"
    curl -s http://localhost:3186/health/detailed | jq '.' 2>/dev/null || curl -s http://localhost:3186/health/detailed
    
    echo ""
    print_info "3. Pricing Presets:"
    curl -s http://localhost:3186/api/pricing/presets | jq '.' 2>/dev/null || curl -s http://localhost:3186/api/pricing/presets
    
    echo ""
    print_info "4. RFX History:"
    curl -s http://localhost:3186/api/rfx/history | jq '.' 2>/dev/null || curl -s http://localhost:3186/api/rfx/history
}

# Function to show AI-RFX specific logs
show_ai_logs() {
    local app_name=${1:-"ai-rfx-backend-dev"}
    print_info "Mostrando logs AI-RFX específicos para: $app_name"
    print_info "Filtrando por: RFX, Pricing, Proposal, OpenAI, EVAL"
    echo ""
    pm2 logs "$app_name" --lines 100 | grep -E "(RFX|Pricing|Proposal|OpenAI|EVAL)"
}

# Main menu
show_menu() {
    echo ""
    echo "🚀 AI-RFX Backend - Gestión PM2 (Ubuntu Server)"
    echo "================================================"
    echo "Selecciona una opción:"
    echo "1) 🖥️  Iniciar Ubuntu Development (puerto 3186)"
    echo "2) 🏭 Iniciar Ubuntu Production (puerto 3187)"
    echo "3) 🧪 Iniciar Staging (puerto 3186)"
    echo "4) 📊 Ver estado"
    echo "5) 📋 Ver logs"
    echo "6) 🔍 Ver logs AI-RFX específicos"
    echo "7) 🧪 Test endpoints AI-RFX"
    echo "8) 🔄 Reiniciar aplicación"
    echo "9) ⏹️  Detener todo"
    echo "10) 📱 Monitor PM2"
    echo "11) 👋 Salir"
    echo ""
    echo "💡 Para desarrollo local usar: python3 start_backend.py (puerto 5001)"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    "dev"|"development")
        check_pm2
        check_venv
        check_env_file
        create_logs_dir
        start_dev
        exit 0
        ;;
    "prod"|"production")
        check_pm2
        check_venv
        check_env_file
        create_logs_dir
        start_prod
        exit 0
        ;;
    "staging")
        check_pm2
        check_venv
        check_env_file
        create_logs_dir
        start_staging
        exit 0
        ;;
    "status")
        show_status
        exit 0
        ;;
    "logs")
        show_logs "${2:-ai-rfx-backend-dev}"
        exit 0
        ;;
    "stop")
        stop_all
        exit 0
        ;;
    "restart")
        restart_app "${2:-ai-rfx-backend-dev}"
        exit 0
        ;;
    "monitor"|"monit")
        pm2 monit
        exit 0
        ;;
    "help"|"-h"|"--help")
        echo "🚀 AI-RFX Backend PM2 Management Script"
        echo "========================================"
        echo "Uso: $0 [comando] [opciones]"
        echo ""
        echo "📋 Comandos Principales:"
        echo "  dev, development     - Inicia servidor de desarrollo"
        echo "  prod, production     - Inicia servidor de producción (Gunicorn)"
        echo "  staging             - Inicia servidor de staging"
        echo ""
        echo "📊 Monitoreo y Logs:"
        echo "  status              - Muestra estado de procesos PM2"
        echo "  logs [app_name]     - Muestra logs (por defecto: ai-rfx-backend-dev)"
        echo "  monitor, monit      - Abre monitor interactivo de PM2"
        echo ""
        echo "🔧 Gestión:"
        echo "  restart [app_name]  - Reinicia aplicación (por defecto: ai-rfx-backend-dev)"
        echo "  stop                - Detiene todas las aplicaciones AI-RFX"
        echo "  help, -h, --help    - Muestra esta ayuda"
        echo ""
        echo "🤖 Ejemplos AI-RFX:"
        echo "  $0 dev              - Inicia con ENABLE_EVALS=true"
        echo "  $0 prod             - Inicia con Gunicorn + workers"
        echo "  $0 staging          - Inicia con ENABLE_META_PROMPTING=true"
        echo "  $0 logs             - Ver logs de desarrollo"
        echo "  $0 logs ai-rfx-backend-prod - Ver logs de producción"
        echo ""
        echo "🔗 Endpoints principales:"
        echo "  🏠 Local Dev:     http://localhost:5001/health          - Local development"
        echo "  🖥️ Ubuntu Dev:     http://localhost:3186/health          - Ubuntu development" 
        echo "  🏭 Ubuntu Prod:    http://localhost:3187/health          - Ubuntu production"
        echo "  📡 APIs:          /api/rfx/process, /api/pricing/*      - Main endpoints"
        exit 0
        ;;
esac

# Interactive mode
print_info "Verificando requisitos..."
check_pm2
check_venv
check_env_file
create_logs_dir

print_status "Todos los requisitos verificados"

while true; do
    show_menu
    read -p "Opción [1-9]: " choice
    
    case $choice in
        1)
            start_dev
            ;;
        2)
            start_prod
            ;;
        3)
            start_staging
            ;;
        4)
            show_status
            ;;
        5)
            echo "Apps disponibles: ai-rfx-backend-dev, ai-rfx-backend-prod, ai-rfx-backend-staging"
            read -p "Nombre de la app (Enter para dev): " app_name
            show_logs "${app_name:-ai-rfx-backend-dev}"
            ;;
        6)
            echo "Apps disponibles: ai-rfx-backend-dev, ai-rfx-backend-prod, ai-rfx-backend-staging"
            read -p "Nombre de la app (Enter para dev): " app_name
            show_ai_logs "${app_name:-ai-rfx-backend-dev}"
            ;;
        7)
            test_endpoints
            ;;
        8)
            echo "Apps disponibles: ai-rfx-backend-dev, ai-rfx-backend-prod, ai-rfx-backend-staging"
            read -p "Nombre de la app (Enter para dev): " app_name
            restart_app "${app_name:-ai-rfx-backend-dev}"
            ;;
        9)
            stop_all
            ;;
        10)
            print_info "Abriendo monitor PM2... (Presiona 'q' para salir)"
            sleep 2
            pm2 monit
            ;;
        11)
            print_info "¡Hasta luego!"
            exit 0
            ;;
        *)
            print_error "Opción inválida. Selecciona 1-11."
            ;;
    esac
    
    echo ""
    read -p "Presiona Enter para continuar..."
done
