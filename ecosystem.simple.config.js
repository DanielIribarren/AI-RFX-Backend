module.exports = {
  apps: [
    {
      // 🚀 Configuración SIMPLE sin virtual environment
      name: 'ai-rfx-backend-simple',
      script: 'run_backend_simple.py',
      interpreter: 'python3', // ← Usar Python del sistema
      cwd: '/home/ubuntu/nodejs/AI-RFX-Backend-Clean',
      
      // Variables de entorno
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
        
        // Feature Flags
        ENABLE_EVALS: 'true',
        ENABLE_META_PROMPTING: 'false',
        ENABLE_VERTICAL_AGENT: 'false',
        EVAL_DEBUG_MODE: 'true'
      },
      
      // Configuración simple
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M'
    }
  ]
};
