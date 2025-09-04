module.exports = {
  apps: [
    {
      // 🚀 Configuración para desarrollo en Ubuntu Server
      name: 'ai-rfx-backend-dev',
      script: 'run_backend_simple.py',
      interpreter: './venv/bin/python',
      // ⚠️ IMPORTANTE: Esta ruta debe coincidir con tu servidor Ubuntu
      cwd: '/home/ubuntu/nodejs/AI-RFX-Backend-Clean', // Ajusta esta ruta
      
      // Variables de entorno - Development
      env: {
        ENVIRONMENT: 'development',
        FLASK_ENV: 'development', 
        FLASK_DEBUG: 'true',
        PYTHONPATH: '.',
        PORT: '3186',
        HOST: '0.0.0.0',
        
        // Base de datos
        SUPABASE_URL: 'https://your-project.supabase.co',
        SUPABASE_ANON_KEY: 'your_supabase_anon_key_here',
        
        // OpenAI
        OPENAI_API_KEY: 'your_openai_api_key_here',
        
        // Aplicación
        SECRET_KEY: 'dev-secret-key-change-in-production',
        DEBUG: 'true',
        
        // CORS
        CORS_ORIGINS: 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001',
        
        // File Upload
        MAX_FILE_SIZE: '16777216',
        UPLOAD_FOLDER: '/tmp/rfx_uploads',
        
        // Feature Flags - AI Agent Improvements
        ENABLE_EVALS: 'true',
        ENABLE_META_PROMPTING: 'false',
        ENABLE_VERTICAL_AGENT: 'false',
        EVAL_DEBUG_MODE: 'true'
      },
      
      // Configuración de logs para Ubuntu
      log_file: './logs/ai-rfx-combined.log',
      out_file: './logs/ai-rfx-out.log',
      error_file: './logs/ai-rfx-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      
      // Configuración de restart
      watch: false,
      ignore_watch: ['node_modules', 'logs', '__pycache__', '.git', '*.pyc'],
      restart_delay: 1000,
      max_restarts: 5,
      min_uptime: '5s',
      
      // Configuración de instancias
      instances: 1,
      exec_mode: 'fork',
      
      // Health monitoring
              health_check_url: 'http://localhost:3186/health',
      health_check_grace_period: 30000,
      
      // Auto restart en caso de error
      autorestart: true,
      max_memory_restart: '500M'
    },
    
    {
      // 🏭 Configuración para producción con Gunicorn en Ubuntu
      name: 'ai-rfx-backend-prod',
      script: './venv/bin/gunicorn',
      args: [
        '--bind', '0.0.0.0:3186',
        '--workers', '2',
        '--worker-class', 'sync',
        '--worker-connections', '1000',
        '--timeout', '60',
        '--keepalive', '2',
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        '--access-logfile', './logs/gunicorn-access.log',
        '--error-logfile', './logs/gunicorn-error.log',
        '--log-level', 'info',
        'backend.wsgi:application'
      ],
      // ⚠️ IMPORTANTE: Ajusta esta ruta para tu servidor Ubuntu
      cwd: '/home/ubuntu/nodejs/AI-RFX-Backend-Clean', // Ajusta esta ruta
      
      // Variables de entorno para producción
      env_production: {
        ENVIRONMENT: 'production',
        FLASK_ENV: 'production',
        FLASK_DEBUG: 'false',
        PYTHONPATH: '.',
        PORT: '3186',
        HOST: '0.0.0.0',
        
        // Worker configuration
        WEB_CONCURRENCY: '2',
        
        // Base de datos (usar variables de producción)
        SUPABASE_URL: 'https://your-project.supabase.co',
        SUPABASE_ANON_KEY: 'your_supabase_anon_key_here',
        
        // OpenAI
        OPENAI_API_KEY: 'your_openai_api_key_here',
        
        // Aplicación
        SECRET_KEY: 'production-secret-key-change-this', // ⚠️ CAMBIAR para producción
        DEBUG: 'false',
        
        // CORS (añadir dominios de producción)
        CORS_ORIGINS: 'https://your-frontend-domain.com,https://your-app.vercel.app',
        
        // File Upload
        MAX_FILE_SIZE: '16777216',
        UPLOAD_FOLDER: '/tmp/rfx_uploads',
        
        // Feature Flags - Producción
        ENABLE_EVALS: 'true',
        ENABLE_META_PROMPTING: 'false',
        ENABLE_VERTICAL_AGENT: 'false',
        EVAL_DEBUG_MODE: 'false'
      },
      
      // Configuración de logs para producción
      log_file: './logs/ai-rfx-prod-combined.log',
      out_file: './logs/ai-rfx-prod-out.log', 
      error_file: './logs/ai-rfx-prod-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      
      // Configuración de restart para producción
      watch: false,
      restart_delay: 2000,
      max_restarts: 10,
      min_uptime: '10s',
      
      // Múltiples instancias para producción
      instances: 1,
      exec_mode: 'fork',
      
      // Health monitoring para producción
              health_check_url: 'http://localhost:3186/health',
      health_check_grace_period: 60000,
      
      // Auto restart configuración
      autorestart: true,
      max_memory_restart: '1G',
      
      // Configuración adicional para producción
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 10000
    }
  ]
};
