import requests
import random
from django.utils import timezone
from datetime import timedelta
from .models import OtpCode

from django.core.cache import cache
from django.conf import settings

def send_eskiz_sms(phone, message):
    """
    Sends an SMS via Eskiz.uz API v2.
    """
    # 1. Get Token from Cache or Request New One
    token = cache.get('eskiz_token')
    
    if not token:
        auth_url = "https://notify.eskiz.uz/api/auth/login"
        auth_payload = {
            'email': settings.ESKIZ_EMAIL,
            'password': settings.ESKIZ_SECRET_KEY # Use the Secret Key here
        }
        try:
            auth_response = requests.post(auth_url, data=auth_payload)
            auth_data = auth_response.json()
            token = auth_data['data']['token']
            # Store token for 25 days (2160000 seconds)
            cache.set('eskiz_token', token, timeout=2160000)
        except Exception as e:
            return {"status": "error", "message": f"Auth failed: {str(e)}"}

    # 2. Send the SMS
    send_url = "https://notify.eskiz.uz/api/message/sms/send"
    # Format phone: Eskiz needs 998901234567 (no +)
    clean_phone = phone.replace('+', '').strip()
    
    send_payload = {
        'mobile_phone': clean_phone,
        'message': message,
        'from': '4546', # 4546 is the default sender for physical persons
    }
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.post(send_url, data=send_payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": f"Send failed: {str(e)}"}