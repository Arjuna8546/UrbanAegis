import random
import string
import time

def generate_unique_id(length=12):
    """
    Generate a unique ID with specified length using only uppercase letters and numbers.
    The ID format is: TIMESTAMP(6) + RANDOM(6) to ensure uniqueness
    """
    # Get current timestamp and convert to base36
    timestamp = int(time.time() * 1000)
    timestamp_part = format(timestamp, '036d')[-6:]  # Take last 6 digits
    
    # Generate random part (remaining 6 characters)
    characters = string.ascii_uppercase + string.digits  # A-Z and 0-9
    random_part = ''.join(random.choices(characters, k=length-6))
    
    # Combine timestamp and random parts
    unique_id = timestamp_part + random_part
    
    return unique_id

def is_valid_id(id_string):
    """
    Validate if the given ID string matches the required format:
    - 12 characters long
    - Only uppercase letters and numbers
    """
    if len(id_string) != 12:
        return False
    
    return all(c in string.ascii_uppercase + string.digits for c in id_string)
