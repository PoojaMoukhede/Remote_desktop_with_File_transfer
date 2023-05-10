import datetime
import random
import string

def generate_password():
    password_length = 6
    password_characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(password_characters) for i in range(password_length))
    current_time = datetime.datetime.now()

    # Set the expiration time to 1 hour from now
    expiration_time = current_time + datetime.timedelta(hours=1)
    return password, expiration_time
password, expiration_time = generate_password()

print("Password:", password)
print("Expiration Time:", expiration_time)