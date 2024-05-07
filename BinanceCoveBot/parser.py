import re
import yaml
from cove_signal import Signal
from logging_config import logging

logger = logging.getLogger(__name__)


def compile_regex(config, category):
    try:
        target_word = "|".join(map(re.escape, config["keywords"][category]))
        regex_pattern = config["regex"][category].format(target_word=target_word)
        return re.compile(regex_pattern, re.IGNORECASE)
    except (KeyError, ValueError) as e:
        logging.error(f"Error compiling regex for category {category}: {e}")
        return None


def extract_numbers(string):
    # Use regex to find all the numbers in the input string
    numbers = re.findall(r'\d+\.\d+|\d+', string)

    # Check if there are any numbers found
    if not numbers:
        return None

    # Convert the numbers from strings to floats
    try:
        numbers = [float(num) for num in numbers]
    except ValueError as e:
        logging.error(f"Error converting numbers: {e}")
        return None

    return numbers


def parse_message(message):
    logging.info("Parsing message...")

    # Load data from yaml file
    try:
        with open("config.yaml", "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
    except FileNotFoundError as e:
        logging.error(f"Error opening config file: {e}")
        return None

    # Compile regular expressions for each category
    order_type_regex = compile_regex(config, "order_type")
    between_regex = compile_regex(config, "between")
    targets_regex = compile_regex(config, "targets")
    stop_loss_regex = compile_regex(config, "stop_loss")
    leverage_regex = compile_regex(config, "leverage")
    currency_name_regex = re.compile(config["regex"]["currency_name"], re.IGNORECASE)

    # Use compiled regular expressions
    order_type_match = order_type_regex.search(message)
    order_type = order_type_match.group() if order_type_match else None
    order_type = 'SELL' if order_type and 'sell' in order_type.lower() else 'BUY'

    between_match = between_regex.search(message)
    between = extract_numbers(between_match.group()) if between_match else None

    targets_match = targets_regex.search(message)
    targets = extract_numbers(targets_match.group()) if targets_match else None

    stop_loss_match = stop_loss_regex.search(message)
    stop_loss = float(extract_numbers(stop_loss_match.group())[0]) if stop_loss_match else None

    leverage_match = leverage_regex.search(message)
    leverage = leverage_match.group() if leverage_match else None

    currency_name_match = currency_name_regex.search(message)
    currency_name = currency_name_match.group() if currency_name_match else None

    # Handle leverage and max leverage
    leverage_numbers = re.findall(r'\d+', leverage) if leverage else None
    leverage_numbers = [int(num) for num in leverage_numbers] if leverage_numbers else None
    max_leverage = max(leverage_numbers) if leverage_numbers else None
    if max_leverage is None:
        result_leverage = 1
    else:
        result_leverage = max_leverage if max_leverage and max_leverage <= 5 else 5

    return Signal(
        order_type=order_type,
        between=between,
        targets=targets,
        stop_loss=stop_loss,
        leverage=result_leverage,
        currency_name=currency_name
    )
