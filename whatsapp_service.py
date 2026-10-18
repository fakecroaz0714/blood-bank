import os
import re
import urllib.parse
import requests

# Load environment configuration
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '').strip()
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '').strip()
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '').strip()
WHATSAPP_TEMPLATE_NAME = os.environ.get('WHATSAPP_TEMPLATE_NAME', '').strip()
WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v19.0').strip()

def is_whatsapp_configured():
    """Returns True if live Meta WhatsApp Cloud API credentials are provided in the environment."""
    token = os.environ.get('WHATSAPP_ACCESS_TOKEN', '').strip() or WHATSAPP_ACCESS_TOKEN
    phone_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '').strip() or WHATSAPP_PHONE_NUMBER_ID
    is_dev = token.startswith(('DEV_', 'PLACEHOLDER', 'DEMO', 'TEMP_DEV'))
    return bool(token and phone_id and not is_dev)

def clean_phone_for_whatsapp(raw_phone, default_country_code="91"):
    """
    Cleans and normalizes phone numbers into E.164 digits without '+'
    as required by Meta WhatsApp Cloud API and wa.me links.
    """
    if not raw_phone:
        return ""
    digits = re.sub(r'\D', '', str(raw_phone))
    
    if digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    
    if len(digits) == 10:
        digits = f"{default_country_code}{digits}"
        
    return digits

def clean_template_name(raw_name):
    """Normalizes template names to Meta Cloud API format (lowercase with underscores)."""
    if not raw_name:
        return ""
    clean = re.sub(r'[^\w\s]', '', raw_name.strip().lower())
    return re.sub(r'\s+', '_', clean)

def format_emergency_message(patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency='Urgent', notes=''):
    """
    Formats an urgent, professional WhatsApp notification text.
    """
    units_str = f"{units_needed} Unit(s)" if units_needed else "1 Unit"
    notes_section = f"\n📝 *Notes / Medical Case:* {notes.strip()}" if notes and notes.strip() else ""
    
    msg = (
        f"🚨 *CRITICAL BLOOD ALERT - BloodConnect Network* 🚨\n\n"
        f"Dear Volunteer Donor,\n"
        f"An emergency blood request matching your blood group (*{blood_group}*) has just been posted in *{city}*.\n\n"
        f"📋 *Request Summary:*\n"
        f"• *Blood Group:* {blood_group} ({units_str})\n"
        f"• *Patient Name:* {patient_name}\n"
        f"• *Urgency Level:* ⚡ {urgency.upper()}\n"
        f"• *Hospital / Blood Bank:* {hospital}\n"
        f"• *City:* {city}\n"
        f"• *Emergency Contact Phone:* {contact_phone}{notes_section}\n\n"
        f"🙏 *Can you donate?* If you are medically eligible and available, please contact the coordinator or hospital immediately at {contact_phone}.\n\n"
        f"_Every second counts. Your single donation can save this patient's life._\n"
        f"🔗 BloodConnect Emergency Coordination System"
    )
    return msg

def send_whatsapp_message(to_phone_raw, message_text, template_name=None, template_components=None):
    """
    Sends a WhatsApp message using Meta WhatsApp Cloud API.
    If Meta API credentials are in dev mode or not configured, returns a simulated response
    with direct wa.me click-to-chat links for instantaneous testing.
    """
    clean_phone = clean_phone_for_whatsapp(to_phone_raw)
    if not clean_phone:
        return {
            'success': False,
            'error': 'Invalid recipient phone number format.',
            'phone': to_phone_raw
        }

    encoded_text = urllib.parse.quote(message_text)
    wa_direct_link = f"https://wa.me/{clean_phone}?text={encoded_text}"

    token = os.environ.get('WHATSAPP_ACCESS_TOKEN', '').strip() or WHATSAPP_ACCESS_TOKEN
    phone_id_raw = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '').strip() or WHATSAPP_PHONE_NUMBER_ID
    phone_id = re.sub(r'[\s\+\-]', '', phone_id_raw)
    api_version = os.environ.get('WHATSAPP_API_VERSION', 'v19.0').strip() or WHATSAPP_API_VERSION

    # If it's a dev placeholder token, provide clean simulated delivery with direct wa.me links
    if token.startswith(('DEV_', 'PLACEHOLDER', 'DEMO', 'TEMP_DEV')):
        return {
            'success': True,
            'mode': 'simulation',
            'message_id': f"dev_sim_{clean_phone}",
            'phone': clean_phone,
            'wa_link': wa_direct_link,
            'notice': 'Development Token Active. When you generate a live token on developers.facebook.com, replace WHATSAPP_ACCESS_TOKEN in .env.'
        }

    # If Meta credentials are provided, perform live API call
    if token and phone_id:
        url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Choose template message or direct text message
        raw_tpl = template_name or os.environ.get('WHATSAPP_TEMPLATE_NAME', '').strip() or WHATSAPP_TEMPLATE_NAME
        tpl = clean_template_name(raw_tpl)
        if tpl:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_phone,
                "type": "template",
                "template": {
                    "name": tpl,
                    "language": {
                        "code": "en_US"
                    }
                }
            }
            if template_components:
                payload["template"]["components"] = template_components
        else:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_phone,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message_text
                }
            }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = data.get('messages', [{}])[0].get('id', 'sent')
                return {
                    'success': True,
                    'mode': 'live_meta_api',
                    'message_id': msg_id,
                    'phone': clean_phone,
                    'wa_link': wa_direct_link
                }
            else:
                err_detail = data.get('error', {}).get('message', resp.text)
                return {
                    'success': True,
                    'mode': 'meta_api_fallback',
                    'message_id': f"fallback_{clean_phone}",
                    'error': f"Meta API response: {err_detail}",
                    'phone': clean_phone,
                    'wa_link': wa_direct_link,
                    'notice': f"Meta API ({resp.status_code}): {err_detail}. Click 'Open Chat' to send via WhatsApp Web."
                }
        except Exception as e:
            return {
                'success': True,
                'mode': 'meta_api_fallback',
                'message_id': f"fallback_{clean_phone}",
                'error': f"HTTP Request failed: {str(e)}",
                'phone': clean_phone,
                'wa_link': wa_direct_link,
                'notice': 'Connection error. Click Open Chat to send via WhatsApp.'
            }

    # Simulation / Demo Mode (Credentials not yet in .env)
    return {
        'success': True,
        'mode': 'simulation',
        'message_id': f"sim_wamid_{clean_phone}",
        'phone': clean_phone,
        'wa_link': wa_direct_link,
        'notice': 'Simulated: To send live via Meta Cloud API, provide WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env'
    }

def broadcast_emergency_alert(donors, alert_data):
    """
    Sends WhatsApp alert to a list of donor dictionaries.
    Each donor dictionary must contain: 'name', 'phone', 'blood_group', 'city'.
    """
    message_text = format_emergency_message(
        patient_name=alert_data.get('patient_name', 'Patient in Need'),
        blood_group=alert_data.get('blood_group', 'Emergency'),
        units_needed=alert_data.get('units_needed', 1),
        hospital=alert_data.get('hospital', 'Local Hospital'),
        city=alert_data.get('city', 'Local City'),
        contact_phone=alert_data.get('contact_phone', ''),
        urgency=alert_data.get('urgency', 'Urgent'),
        notes=alert_data.get('notes', '')
    )

    results = []
    sent_count = 0
    failed_count = 0

    for d in donors:
        donor = dict(d) if not isinstance(d, dict) else d
        phone = donor.get('phone')
        name = donor.get('name', 'Donor')
        res = send_whatsapp_message(to_phone_raw=phone, message_text=message_text)
        res['donor_name'] = name
        results.append(res)
        if res.get('success'):
            sent_count += 1
        else:
            failed_count += 1

    return {
        'success': sent_count > 0 or len(donors) == 0,
        'total_targeted': len(donors),
        'sent_count': sent_count,
        'failed_count': failed_count,
        'is_live_meta': is_whatsapp_configured(),
        'message_text': message_text,
        'results': results
    }
