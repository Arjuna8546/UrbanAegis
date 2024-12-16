"""
Django settings for steely project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from dotenv import load_dotenv

load_dotenv()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'


ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'core',
    'seller',
    'user',
    'cart',
    'order',
    'coupon',
    'offer',
    'wallet',
    'dashboard',

    'django_celery_beat',
    'django_celery_results',

    'django.contrib.sites',    # Required for managing social authentication sites
    'social_django',           # The core social-auth-app-django app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'steely.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'steely.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),      # Default PostgreSQL port
    }
}

CELERY_RESULT_BACKEND = "django-db"
CELERY_RESULT_EXTENDED = True

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',   # Google OAuth2 backend
    'django.contrib.auth.backends.ModelBackend',  # Django's default auth backend
)

AUTH_USER_MODEL = 'core.Users'

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",  # Assuming your 'static' folder is at the project root level
]

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_REDIS_URL', 'redis://localhost:6379')

CLOUDINARY = {
    'cloud_name':  os.getenv('CLOUDINARY_CLOUD_NAME'),
    'api_key': os.getenv('CLOUDINARY_API_KEY'),
    'api_secret': os.getenv('CLOUDINARY_API_SECRET')
}

cloudinary.config(
    cloud_name=CLOUDINARY['cloud_name'],
    api_key=CLOUDINARY['api_key'],
    api_secret=CLOUDINARY['api_secret']
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # For Gmail's SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # Your email address
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # Your email password
# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# django-allauth settings
 # To not require username if only email is required


SITE_ID = 1


SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')


LOGIN_REDIRECT_URL = '/'      # Redirect after successful login
LOGOUT_REDIRECT_URL = '/'     # Redirect after logout
LOGIN_URL = '/login/' 
# settings.py

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',       # Get user details from provider
    'social_core.pipeline.social_auth.social_uid',           # Get unique social ID
    'social_core.pipeline.social_auth.auth_allowed',         # Check if login is allowed
    'social_core.pipeline.social_auth.social_user',          # Try to find the user by social ID
    'social_core.pipeline.user.get_username',                # Generate a username if needed
    'core.pipeline.create_user',                    # Custom pipeline function for user creation
    'social_core.pipeline.social_auth.associate_user',       # Associate social account with user
    'social_core.pipeline.social_auth.load_extra_data',      # Load extra data from provider
    'social_core.pipeline.user.user_details',                # Update user details if needed
)

RAZORPAY_KEY_ID = 'rzp_test_xgAbYbKWLNZHR0'
RAZORPAY_KEY_SECRET = 'pBaRn0FrJtHGQABUEkHfJwCZ'

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'