module.exports = {
  apps: [
    {
      name: 'RFX-dev',
      script: 'run_backend_simple.py',
      interpreter: './venv/bin/python',
      cwd: '/home/ubuntu/nodejs/AI-RFX-Backend-Clean',

      env: {
        ENVIRONMENT: 'development',
        FLASK_ENV: 'development', 
        FLASK_DEBUG: 'true',
        PYTHONPATH: '.',
        PORT: '3186',
        HOST: '0.0.0.0',
        
        // Base de datos
        SUPABASE_URL: 'https://mjwnmzdgxcxubanubvms.supabase.co',
        SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1qd25temRneGN4dWJhbnVidm1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkyMjg5MzIsImV4cCI6MjA2NDgwNDkzMn0.0fuBXpygfoj_Ar5Uav4Joo-DV-v2AU1HQAAHYARsRGY',
        
        // OpenAI
        OPENAI_API_KEY: '',
        
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

      // 🚫 quitamos post_update y pre_start, no van aquí
      log_file: './logs/ai-rfx-dev-combined.log',
      out_file: './logs/ai-rfx-dev-out.log',
      error_file: './logs/ai-rfx-dev-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      watch: false,
      ignore_watch: ['node_modules', 'logs', '__pycache__', '.git', '*.pyc'],
      restart_delay: 1000,
      max_restarts: 5,
      min_uptime: '5s',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      max_memory_restart: '500M'
    }
  ],

  deploy: {
    development: {
      user: 'ubuntu',
      host: ['your-server-ip'],
      ref: 'origin/main',
      repo: 'git@github.com:your-repo.git',
      path: '/home/ubuntu/nodejs',

      // ✅ Aquí colocamos tu script de setup
      'post-deploy': 'bash ./scripts/post_deploy_setup.sh && pm2 reload ecosystem.dev.config.js --env development',
      'pre-setup': 'apt update && apt install -y git'
    }
  }
};
