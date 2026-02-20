import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)