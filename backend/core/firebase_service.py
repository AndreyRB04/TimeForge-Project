"""
INSTRUCCIONES:
1. Agrega 'firebase-admin' al requirements.txt
2. Agrega este archivo como backend/core/firebase_service.py
3. Agrega las funciones de views al views.py
4. Agrega las rutas al urls.py
"""

# ── firebase_service.py ──────────────────────────────────────────────────────

import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

_firebase_app = None

def get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        creds_json = os.environ.get('FIREBASE_CREDENTIALS', '')
        if creds_json:
            creds_dict = json.loads(creds_json)
            cred = credentials.Certificate(creds_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def enviar_notificacion(fcm_token, titulo, cuerpo, datos=None):
    """Envía una notificación push a un dispositivo específico"""
    try:
        get_firebase_app()
        message = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo,
            ),
            data=datos or {},
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='@mipmap/ic_launcher',
                    color='#6C63FF',
                    sound='default',
                ),
            ),
        )
        response = messaging.send(message)
        return True
    except Exception as e:
        print(f'Error enviando notificación: {e}')
        return False


def enviar_notificacion_multiple(tokens, titulo, cuerpo, datos=None):
    """Envía una notificación a múltiples dispositivos"""
    try:
        get_firebase_app()
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            data=datos or {},
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)
        return response.success_count
    except Exception as e:
        print(f'Error enviando notificaciones: {e}')
        return 0
