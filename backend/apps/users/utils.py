import os
import re

import requests
import random
from django.utils import timezone
from datetime import timedelta
from .models import User

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
    



DEVSMS_TOKEN = os.getenv('DEVSMS_TOKEN')

def send_sms(phone_number):

    clean_phone = re.sub(r'\D', '', phone_number) # Remove all non-digits
    if len(clean_phone) >= 9: # Ensure it has at least 9 digits
        phone_number = clean_phone[-9:]

    otp = random.randint(100000, 999999)    

    url = "https://devsms.uz/api/send_sms.php"
    headers = {
        "Authorization": f"Bearer {DEVSMS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "phone": "998" + phone_number,
        "message": f"Smart Drive ilovasi - amaliyotni tasdiqlash kodi: {otp}",
        # "message": f"SmartDrive tasdiqlash kodi: {otp}",
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.json())
    return otp


#sample usage
if __name__ == "__main__":
    phone_number = "998931680043"
    response = send_sms(phone_number)
    print(response)
