from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
import smtplib
from email.message import EmailMessage

from models import ContactUs

misc_router = APIRouter()

@misc_router.post("/contactus", response_description="Contact us", status_code=status.HTTP_201_CREATED)
def create_protocol(request: Request, data: ContactUs = Body(...)):
    data = jsonable_encoder(data)
    new_form_entry = request.app.database["contactus"].insert_one(data)
    # creates SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    
    # start TLS for security
    server.starttls()
    
    # Authentication
    server.login("scarlettai.official@gmail.com", "uqjbuvftimpwezgv")

    # Composing the mail
    msg = EmailMessage()
    msg.set_content('A new query has come via the contact us form. Please check.')

    msg['Subject'] = "Scarlett - New Form Entry"
    msg['From'] = "scarlettai.official@gmail.com"
    msg['To'] = "abhisom2912@gmail.com, vatsal.gupta.1306@gmail.com"
    
    # Send mail
    server.send_message(msg)
    
    # terminating the session
    server.quit()
    return new_form_entry.inserted_id


