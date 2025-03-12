import os
import logging

# Configurações de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("notifier")

# Variáveis de Ambiente
DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
COMPANY_NAME = os.getenv("COMPANY_NAME")
PLATFORM_LINK = os.getenv("PLATFORM_LINK")
USE_SANDBOX = os.getenv("USE_SANDBOX", "true").lower() == "true"
