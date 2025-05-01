# AWS API Gateway Settings

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# API Gateway Configuration
API_GATEWAY_STAGE = os.getenv('API_GATEWAY_STAGE', 'dev')
API_GATEWAY_NAME = os.getenv('API_GATEWAY_NAME', 'telepsych-api')

# CORS Configuration
CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = [
    'https://api.example.com',  # Replace with your API Gateway URL
]

# Authentication Configuration
OIDC_AUTHENTICATION_CLASS = 'oidc_provider.auth.Authentication'
OIDC_IDTOKEN_INCLUDE_CLAIMS = True
OIDC_IDTOKEN_SUB_GENERATOR = 'oidc_provider.lib.utils.common.default_sub_generator'

# X-Ray Configuration
XRAY_RECORDER = {
    'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR',
    'AWS_XRAY_DAEMON_ADDRESS': '127.0.0.1:2000',
}

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'telepsych'),
        'USER': os.getenv('DB_USER', 'admin'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'admin'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
    }
}

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'oidc_provider.authentication.OIDCAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}
