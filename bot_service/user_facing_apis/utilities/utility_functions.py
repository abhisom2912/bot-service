import json
import smtplib
from email.message import EmailMessage
 
def send_mail(receiver_mail):
    # creates SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    
    # start TLS for security
    server.starttls()
    
    # Authentication
    server.login("ashuvswild@gmail.com", "qvpzibicttxpaaqf")

    # Composing the mail
    msg = EmailMessage()
    msg.set_content('Your data has been uploaded successfully on our server. You can now start asking your questions.')

    msg['Subject'] = 'Scarlett'
    msg['From'] = "ashuvswild@gmail.com"
    msg['To'] = receiver_mail
    
    # Send mail
    server.send_message(msg)
    
    # terminating the session
    server.quit()

def untuplify_dict_keys(mapping):
    string_keys = {json.dumps(k): v for k, v in mapping.items()}
    return string_keys

def tuplify_dict_keys(string):
    mapping = string
    return {tuple(json.loads(k)): v for k, v in mapping.items()}