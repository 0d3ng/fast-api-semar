import random
import string


def generate_random_alphanumeric_hexa(length=6):
    characters = string.ascii_letters + string.digits + 'abcdef'
    return (''.join(random.choice(characters) for _ in range(length))).lower()