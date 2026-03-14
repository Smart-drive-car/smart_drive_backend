
from pathlib import Path
import os
from os import getenv
from dotenv import load_dotenv
load_dotenv()
import firebase_admin
from firebase_admin import credentials



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Path to your downloaded JSON file
# cred = credentials.Certificate(f"{BASE_DIR}/firebase/firebase_credentials.json")
# firebase_admin.initialize_app(cred)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-g%!koy3&&c(7@6!n!p$s7i3w_wphg=!lg2twe^ts&a!rhk@#)x'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

AUTH_USER_MODEL = 'users.User'

apps = [
    'apps.users',
    'apps.shared',
    'apps.vehicles',
]

libs = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'drf_spectacular',
]

default_libs = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

INSTALLED_APPS = default_libs + libs + apps

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smartdrive.urls'

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

WSGI_APPLICATION = 'smartdrive.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases



# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

MEDIA_URL = '/media/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DB_ENGINE = getenv('DB_ENGINE')
DB_NAME = getenv('DB_NAME')
DB_USER = getenv('DB_USER')
DB_PASSWORD = getenv('DB_PASSWORD')
DB_HOST = getenv('DB_HOST')
DB_PORT = getenv('DB_PORT')
ESKIZ_EMAIL = getenv('ESKIZ_EMAIL')
ESKIZ_SECRET_KEY = getenv('ESKIZ_SECRET_KEY')


DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'SmartDrive API',
    'VERSION': '1.0.0',
}