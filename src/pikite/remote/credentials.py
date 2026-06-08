import bcrypt
import os
from dotenv import load_dotenv, set_key
from getpass import getpass

from pikite.system.storage import StorageManager

storage_manager = StorageManager()

ENV_PATH = str(storage_manager.USER_ROOT / ".env")

def get_current_password_hash():
    load_dotenv(ENV_PATH, override=True)
    current_hash = os.getenv('PIKITE_PASSWORD_HASH')
    return current_hash

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

def get_new_password_hash():
    """
    Prompt the user to enter a new password and confirm it. If the passwords match, hash it and store in .env.
    """
    new_password = getpass("Enter new password: ")
    if new_password != getpass("Confirm new password: "):
        raise ValueError("Passwords do not match. Aborting.")
    
    return hash_password(new_password)

def set_password():
    """Reset the password by verifying the current password and then allowing the user to set a new one."""
    current_hash = get_current_password_hash()

    if current_hash is None:
        confirm = input("No password set. Set new password? (y/n): ")
        if confirm.lower() == 'n':
            raise SystemExit("User aborted the password reset.")
        elif confirm.lower() != 'y':
            raise ValueError("Invalid response given for confirmation prompt. Expected 'y' or 'n'.")
        else:
            new_password_hash = get_new_password_hash()
    else:
        # Verify current password before allowing reset
        entered_password = getpass("Enter current password: ")
        if not verify_password(entered_password, current_hash.encode('utf-8')):
            raise ValueError("Incorrect password. Aborting.")
        
        new_password_hash = get_new_password_hash()

    # Store hash in .env
    set_key(ENV_PATH, "PIKITE_PASSWORD_HASH", new_password_hash.decode('utf-8'))

    load_dotenv(ENV_PATH, override=True)  # Reload .env to get new hash
    print("Password updated successfully.")