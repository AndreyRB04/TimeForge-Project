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
    """Envía una notificación push. Si el token es inválido, lo elimina de la BD."""
    try:
        get_firebase_app()
        message = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo,
            ),
            data={k: str(v) for k, v in (datos or {}).items()},
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
        messaging.send(message)
        return True
    except messaging.UnregisteredError:
        # Token expirado o inválido — eliminarlo de la BD para no reintentar
        print(f'Token FCM inválido, eliminando de la BD: {fcm_token[:20]}...')
        _eliminar_token_invalido(fcm_token)
        return False
    except Exception as e:
        print(f'Error enviando notificación: {e}')
        return False


def _eliminar_token_invalido(token):
    """Borra el FCMToken de la BD si ya no es válido."""
    try:
        from django.apps import apps
        FCMToken = apps.get_model('core', 'FCMToken')
        FCMToken.objects.filter(token=token).delete()
    except Exception as e:
        print(f'No se pudo eliminar token inválido: {e}')


def enviar_notificacion_multiple(tokens, titulo, cuerpo, datos=None):
    """Envía notificación a múltiples dispositivos y limpia los tokens inválidos."""
    if not tokens:
        return 0
    try:
        get_firebase_app()
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            data={k: str(v) for k, v in (datos or {}).items()},
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)

        # Limpiar tokens que fallaron por ser inválidos
        tokens_invalidos = [
            tokens[i]
            for i, r in enumerate(response.responses)
            if not r.success and isinstance(r.exception, messaging.UnregisteredError)
        ]
        if tokens_invalidos:
            print(f'Eliminando {len(tokens_invalidos)} tokens inválidos')
            _eliminar_tokens_invalidos_bulk(tokens_invalidos)

        return response.success_count
    except Exception as e:
        print(f'Error enviando notificaciones: {e}')
        return 0


def _eliminar_tokens_invalidos_bulk(tokens_list):
    try:
        from django.apps import apps
        FCMToken = apps.get_model('core', 'FCMToken')
        FCMToken.objects.filter(token__in=tokens_list).delete()
    except Exception as e:
        print(f'No se pudo eliminar tokens inválidos: {e}')
