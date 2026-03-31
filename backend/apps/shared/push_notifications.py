import logging

from django.conf import settings

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception:
    firebase_admin = None
    credentials = None
    messaging = None


logger = logging.getLogger(__name__)


def get_firebase_app():
    if firebase_admin is None or credentials is None:
        logger.warning('firebase_admin package is not available; push notifications are disabled.')
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    credentials_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
    if not credentials_path:
        logger.warning('FIREBASE_CREDENTIALS_PATH is not configured; push notifications are disabled.')
        return None

    try:
        cred = credentials.Certificate(credentials_path)
        return firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception('Failed to initialize Firebase app for push notifications.')
        return None


def send_push_to_tokens(tokens, title, body, data=None):
    if not tokens:
        return None

    app = get_firebase_app()
    if app is None or messaging is None:
        return None

    try:
        message = messaging.MulticastMessage(
            tokens=list(tokens),
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            android=messaging.AndroidConfig(priority='high'),
            apns=messaging.APNSConfig(
                headers={'apns-priority': '10'},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(content_available=True, sound='default')
                ),
            ),
        )
        return messaging.send_each_for_multicast(message, app=app)
    except Exception:
        logger.exception('Failed to send push notification via FCM.')
        return None

def send_notification_to_user(user, title, body, data=None):
    from apps.shared.models import Notification
    from apps.users.models import UserDeviceToken

    # Create the notification in DB
    Notification.objects.create(
        user=user,
        title=title,
        body=body,
        data=data or {}
    )

    # Get active device tokens
    tokens = UserDeviceToken.objects.filter(
        user=user,
        is_active=True
    ).values_list('token', flat=True)

    if tokens:
        return send_push_to_tokens(tokens, title, body, data)
    return None

