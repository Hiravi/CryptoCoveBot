import logging

# Configure logging (adjust based on your needs)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

# Define handlers for logging to file
file_handler = logging.FileHandler('cove_bot.log')
file_handler.setLevel(logging.INFO)  # Set the desired level for file logging

# Add the handlers to the root logger
logging.getLogger().addHandler(file_handler)

# Define custom loggers for different parts of your application
app_logger = logging.getLogger('app')
app_logger.addHandler(file_handler)  # Add file handler to app logger

db_logger = logging.getLogger('db')
db_logger.addHandler(file_handler)  # Add file handler to db logger

handler_logger = logging.getLogger('handler')
handler_logger.addHandler(file_handler)  # Add file handler to handler logger

connector_logger = logging.getLogger('connector')
connector_logger.addHandler(file_handler)  # Add file handler to connector logger
