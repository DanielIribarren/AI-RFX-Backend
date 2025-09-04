module.exports = {
  apps: [
    {
      // 🚀 Configuración para desarrollo
      name: 'ai-rfx-backend-dev',
      script: 'run_backend_simple.py',
      interpreter: './venv/bin/python',
      cwd: '/Users/danielairibarren/workspace/RFX-Automation/APP-Sabra/AI-RFX-Backend-Clean',
      
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
        // OPENAI_API_KEY: 'your_openai_api_key_here', // ← Configurar en .env
        
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
      
      // Configuración de logs
      log_file: './logs/ai-rfx-combined.log',
      out_file: './logs/ai-rfx-out.log',
      error_file: './logs/ai-rfx-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      
      // Configuración de restart
      watch: false, // Cambiar a true para desarrollo
      ignore_watch: ['node_modules', 'logs', '__pycache__', '.git'],
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
      // 🏭 Configuración para producción con Gunicorn
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
      cwd: '/Users/danielairibarren/workspace/RFX-Automation/APP-Sabra/AI-RFX-Backend-Clean',
      
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
        
        // OpenAI (usar API key de producción si tienes diferente)
        // OPENAI_API_KEY: 'your_openai_api_key_here', // ← Configurar en .env
        
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
        ENABLE_META_PROMPTING: 'false',  // Cambiar cuando esté listo
        ENABLE_VERTICAL_AGENT: 'false', // Cambiar cuando esté listo
        EVAL_DEBUG_MODE: 'false'        // Desactivar en producción
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
      instances: 1, // Cambiar según necesidades del servidor
      exec_mode: 'fork',
      
      // Health monitoring para producción
      health_check_url: 'http://localhost:5001/health',
      health_check_grace_period: 60000,
      
      // Auto restart configuración
      autorestart: true,
      max_memory_restart: '1G',
      
      // Configuración adicional para producción
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 10000
    },
    
    {
      // 🧪 Configuración para testing/staging
      name: 'ai-rfx-backend-staging',
      script: 'run_backend_simple.py',
      interpreter: './venv/bin/python',
      cwd: '/Users/danielairibarren/workspace/RFX-Automation/APP-Sabra/AI-RFX-Backend-Clean',
      
      // Variables de entorno para staging
      env_staging: {
        ENVIRONMENT: 'staging',
        FLASK_ENV: 'staging',
        FLASK_DEBUG: 'true',
        PYTHONPATH: '.',
        PORT: '3186',
        HOST: '0.0.0.0',
        
        // Base de datos (mismo Supabase pero podrías usar proyecto diferente)
        SUPABASE_URL: 'https://your-project.supabase.co',
        SUPABASE_ANON_KEY: 'your_supabase_anon_key_here',
        
        // OpenAI
        // OPENAI_API_KEY: 'your_openai_api_key_here', // ← Configurar en .env
        
        // Aplicación
        SECRET_KEY: 'staging-secret-key-change-this',
        DEBUG: 'true',
        
        // CORS
        CORS_ORIGINS: 'http://localhost:3000,http://127.0.0.1:3000,https://staging-frontend.vercel.app',
        
        // File Upload
        MAX_FILE_SIZE: '16777216',
        UPLOAD_FOLDER: '/tmp/rfx_uploads',
        
        // Feature Flags - Staging (environment de testing)
        ENABLE_EVALS: 'true',
        ENABLE_META_PROMPTING: 'true',   // Activar para testing en staging
        ENABLE_VERTICAL_AGENT: 'false',
        EVAL_DEBUG_MODE: 'true'         // Activar para debugging
      },
      
      // Configuración de logs para staging
      log_file: './logs/ai-rfx-staging-combined.log',
      out_file: './logs/ai-rfx-staging-out.log',
      error_file: './logs/ai-rfx-staging-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      
      // Configuración de restart para staging
      watch: true,
      ignore_watch: ['node_modules', 'logs', '__pycache__', '.git'],
      restart_delay: 1000,
      max_restarts: 3,
      min_uptime: '5s',
      
      // Configuración de instancias para staging
      instances: 1,
      exec_mode: 'fork',
      
      // Health monitoring para staging
      health_check_url: 'http://localhost:5001/health',
      health_check_grace_period: 30000,
      
      // Auto restart configuración
      autorestart: true,
      max_memory_restart: '400M'
    }
  ],
  
  // 🔧 Configuración de deployment
  deploy: {
    production: {
      user: 'deploy',
      host: ['your-production-server.com'],
      ref: 'origin/main',
      repo: 'git@github.com:your-username/ai-rfx-backend.git',
      path: '/var/www/ai-rfx-backend',
      'post-deploy': 'source venv/bin/activate && pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      env: {
        NODE_ENV: 'production'
      }
    },
    
    staging: {
      user: 'deploy',
      host: ['your-staging-server.com'], 
      ref: 'origin/develop',
      repo: 'git@github.com:your-username/ai-rfx-backend.git',
      path: '/var/www/ai-rfx-backend-staging',
      'post-deploy': 'source venv/bin/activate && pip install -r requirements.txt && pm2 reload ecosystem.config.js --env staging',
      env: {
        NODE_ENV: 'staging'
      }
    }
  }
};
