from twilio.rest import Client
import logging
from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, USE_SANDBOX
from domain.exam_utils import build_message_for_exams

logger = logging.getLogger("notifier")

def send_notification(to_number, client_name, exam_list):
    """
    - Monta a mensagem bullet.
    - Envia via Twilio (Sandbox ou Produção).
    - Trata o erro 63038 (limite diário em testes).
    """
    if not to_number.startswith("whatsapp:"):
        to_number = "whatsapp:+55" + to_number

    msg_body = build_message_for_exams(client_name, exam_list)

    # Se mockado
    if TWILIO_ACCOUNT_SID == "TWILIO_ACCOUNT_SID":
        logger.info(f"(Simulação) Mensagem para {client_name} ({to_number}):\n{msg_body}")
        return True

    from_number = "whatsapp:+14155238886" if USE_SANDBOX else TWILIO_FROM_NUMBER
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        message = twilio_client.messages.create(
            from_=from_number,
            body=msg_body,
            to=to_number
        )
        logger.info(f"Mensagem enviada para {client_name} ({to_number}). SID={message.sid}")
        return True
    except Exception as e:
        err_str = str(e)
        if "63038" in err_str:
            logger.warning(f"Limite diário atingido para {client_name} ({to_number}).")
            return False
        else:
            logger.error(f"Erro ao enviar p/ {client_name} ({to_number}): {e}")
            return False
