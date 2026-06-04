from unittest import result

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)


def send_notification(user, title, body, data=None):
    """Send notification to any user. user = User object"""
    print(f"Notification result: {result}")

    try:
        fcm_token = user.fcm_token.token
    except Exception:
        print(f"No FCM Token For User:{user.id}")
        return False

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        token=fcm_token,
        android=messaging.AndroidConfig(priority="high"),
    )

    try:
        response = messaging.send(message)
        print(f"Notification sent to {user.username}:", response)
        return True
    except Exception as e:
        print(f"FCM error for {user.username}:", e)
        return False
