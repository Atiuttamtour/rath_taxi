"""
Django settings for atiuttam_project project.
Production Ready: Jazzmin Theme, India Timezone, WhiteNoise, & Cloud Database.
"""

from pathlib import Path
import dj_database_url
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-2%=zjp!5=+gokc30lsbo&725jzr5xb6i5_d89e^l=m2*nm@9_!')

# SECURITY WARNING: don't run with debug turned on in production!
# If 'RENDER' is in the environment, Debug is False (Secure). Otherwise True (Laptop).
DEBUG = 'RENDER' not in os.environ

# --- ALLOWED HOSTS CONFIGURATION ---
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS = [RENDER_EXTERNAL_HOSTNAME]
else:
    ALLOWED_HOSTS = ['*']

# --- PRODUCTION SECURITY OVERRIDES ---
# This tells Django it's behind Render's proxy so HTTPS works correctly
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# This fixes the "403 Forbidden" error by trusting your live URL
CSRF_TRUSTED_ORIGINS = [
    "https://rath-taxi.onrender.com",
    "https://*.onrender.com",
    "http://localhost:8081", # For Expo local testing
]

# Application definition

INSTALLED_APPS = [
    'jazzmin',                      # <--- 1. PROFESSIONAL THEME (Must be at top)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',                  # <--- Needed for App connection
    'rest_framework',               # <--- Needed for API
    'rath_api',                     # <--- YOUR MAIN APP
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',        # <--- MUST BE FIRST
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # <--- 2. FIX ADMIN PANEL CSS IN CLOUD
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'atiuttam_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'atiuttam_project.wsgi.application'


# --- 3. DATABASE CONFIGURATION (SMART SWITCH) ---
# If on Render (Cloud), use PostgreSQL. If on Laptop, use SQLite.
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # India Time
USE_I18N = True
USE_TZ = True


# --- 4. STATIC FILES (CSS/Images) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# This compresses CSS so it loads fast and works on Render
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# TELLING DJANGO TO USE OUR CUSTOM USER
AUTH_USER_MODEL = 'rath_api.User'

# ALLOW ALL BROWSERS TO TALK TO US
CORS_ALLOW_ALL_ORIGINS = True

# --- 5. PROFESSIONAL BRANDING SETTINGS ---
JAZZMIN_SETTINGS = {
    'site_title': 'Atiuttam Rath Admin',
    'site_header': 'Atiuttam Rath',
    'site_brand': 'Atiuttam Rath',
    'welcome_sign': 'Welcome to Atiuttam Rath HQ',
    'copyright': 'Atiuttam Rath Ltd',
    'search_model': 'rath_api.User',
    'show_ui_builder': False,
}

# --- PROFESSIONAL SETUP: Media Files (Images/Documents) ---
# This tells Django where to save the Driver Photos
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- 6. EMAIL OTP CONFIGURATION (Gmail) ---
# 🚀 FIX APPLIED: Switched to Port 465 (SSL) to bypass Render firewall block
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465          # Changed from 587
EMAIL_USE_SSL = True      # Changed to True
EMAIL_USE_TLS = False     # Changed to False (SSL replaces TLS on 465)
EMAIL_TIMEOUT = 10        # Added to prevent infinite hanging

# The Email Account that sends the OTPs
EMAIL_HOST_USER = 'atiuttamtravels@gmail.com'

# ⚠️ SECURITY STEP: Paste your 16-letter App Password below inside the quotes
EMAIL_HOST_PASSWORD = 'ynwopqoaeoazhpvz'

# The Name people see in their Inbox (Branding)
DEFAULT_FROM_EMAIL = 'Atiuttam.com <atiuttamtravels@gmail.com>'