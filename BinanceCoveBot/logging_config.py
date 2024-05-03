import logging

# Configure logging (adjust based on your needs)
logging.basicConfig(
    filename='cove_bot.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

# Define custom loggers for different parts of your application (optional)
app_logger = logging.getLogger('app')
db_logger = logging.getLogger('db')
handler_logger = logging.getLogger('handler')
connector_logger = logging.getLogger('connector')