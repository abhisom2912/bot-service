from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
import smtplib
from email.message import EmailMessage

from models import ContactUs

misc_router = APIRouter()

# API to take basic information from interested parties and sending it to the desired email addresses
@misc_router.post("/contactus", response_description="Contact us", status_code=status.HTTP_201_CREATED)
def create_protocol(request: Request, data: ContactUs = Body(...)):
    data = jsonable_encoder(data)
    new_form_entry = request.app.database["contactus"].insert_one(data)

    # creates SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    
    # start TLS for security
    server.starttls()
    
    # authentication
    server.login("YOUR_COMPANY_EMAIL_ADDRESS", "YOUR_AUTHENTICATION_KEY") # change the email address to your company's email address

    # composing an intimation mail
    msg = EmailMessage()
    msg.set_content('A new query has come via the contact us form. \nUser message:' + data["message"] + '\nUser email address:' + data["email"])

    msg['Subject'] = "Scarlett - New Form Entry"
    msg['From'] = "YOUR_COMPANY_EMAIL_ADDRESS"
    msg['To'] = "EMAIL_ADDRESS_1, EMAIL_ADDRESS_2" # email addresses of people to whom the email needs to be sent
    
    # send mail
    server.send_message(msg)
    
    # terminating the session
    server.quit()
    return new_form_entry.inserted_id


