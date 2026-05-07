import bcrypt
import os
from dotenv import load_dotenv, set_key, dotenv_values
from getpass import getpass

from ..system.storage import StorageManager

storage_manager = StorageManager()

ENV_PATH = str(storage_manager.BASE_DIR / ".env")

def hash_password(password: str) -> bytes:
    """
    Hash a password using bcrypt.
    
    Args:
        password (str): The plaintext password to hash.
    
    Returns:
        bytes: The hashed password.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

def verify_password(password: str, hashed: bytes) -> bool:
    """
    Verify a password against a hashed value.
    
    Args:
        password (str): The plaintext password to verify.
        hashed (bytes): The hashed password to compare against.
    
    Returns:
        bool: True if the password is correct, False otherwise.
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def get_new_password():
    """
    Prompt the user to enter a new password and confirm it. If the passwords match, hash it and store in .env.
    """
    new_password = getpass("Enter new password: ")
    if new_password != getpass("Confirm new password: "):
        print("Passwords do not match. Aborting.")
        return
    
    new_hash = hash_password(new_password)

    # Store hash in .env
    set_key(ENV_PATH, "PIKITE_PASSWORD_HASH", new_hash.decode('utf-8'))

    load_dotenv(ENV_PATH, override=True)  # Reload .env to get new hash
    print("Password updated successfully.")

def reset_password():
    """Reset the password by verifying the current password and then allowing the user to set a new one."""
    load_dotenv(ENV_PATH, override=True)
    current_hash = os.getenv('PIKITE_PASSWORD_HASH')

    if not current_hash:
        confirm = input("No password set. Set new password? (y/n): ")
        if confirm.lower() == 'y':
            get_new_password()
        return

    # Verify current password before allowing reset
    entered_password = getpass("Enter current password: ")
    if not verify_password(entered_password, current_hash.encode('utf-8')):
        print("Incorrect password. Aborting.")
        return
    
    get_new_password()