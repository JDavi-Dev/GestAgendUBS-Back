import traceback
import logging

# Cria um registrador com nome exclusivo
logger = logging.getLogger(__name__)

# Configura o logger para registrar mensagens de nível INFO, ERROR e superiores.
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Define um manipulador para especificar onde as mensagens de log devem ser enviadas.
streamHandler = logging.StreamHandler()  # Registrar mensagens no console
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Função que aplica tabulação para as informações da exceção
def log_exception(mensagem: str):
    formatted_tb = traceback.format_exc().replace('\n', '\n\t')
    logger.error(f"{mensagem}:\n\t{formatted_tb}")