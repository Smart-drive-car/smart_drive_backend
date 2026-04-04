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
        response = messaging.send_each_for_multicast(message, app=app)
        logger.info(f"FCM Multicast response: {response.success_count} success, {response.failure_count} failures")
        
        token_results = []
        for i, res in enumerate(response.responses):
            token_results.append({
                "token": list(tokens)[i],
                "success": res.success,
                "message_id": res.message_id,
                "error": str(res.exception) if res.exception else None
            })
            if not res.success:
                logger.error(f"FCM error for token index {i}: {res.exception}")
                
        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count,
            "results": token_results
        }
    except Exception as e:
        logger.error(f"Failed to send push notification via FCM: {repr(e)}")
        return None

def send_notification_to_user(user, title, body, data=None):
    from apps.shared.models import Notification
    from apps.users.models import UserDeviceToken

    # Create the notification in DB
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        data=data or {}
    )
    logger.info(f"Saved DB Notification (ID: {notification.id}) for User {user.id}. Title: '{title}', Event: {data.get('event', 'unknown') if data else 'unknown'}")

    # Get active device tokens
    tokens = UserDeviceToken.objects.filter(
        user=user,
        is_active=True
    ).values_list('token', flat=True)

    if tokens:
        logger.info(f"Found {len(tokens)} tokens for user {user.id}. Sending push...")
        return send_push_to_tokens(tokens, title, body, data)
    
    logger.warning(f"No active tokens found for user {user.id}.")
    return None

