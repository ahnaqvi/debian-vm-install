import smtplib
from email.message import EmailMessage
from email import policy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import dkim

def send_mail(sender_email_address, receivers_email_address_list, 
            receiver_smtp_server, dkim_private_key_path, subject, message_body):
    '''
Sign and send a simple email.  Example call: send_mail("sender@sender.com",
                                                [recv1@a.com, recv2@a.com]
                                                "smtp.a.com:25", 
                                                /path/to/dkim_key, 
                                                "Example Subject",
                                                "Example Body")
Notice that all the receivers need to be on the same domain. 
'''
    receivers = receivers_email_address_list
    message = MIMEMultipart("alternative")
    message.attach(MIMEText(message_body, "plain"))
    message['Subject'] = subject
    message['From'] =  sender_email_address # 'no_reply@mail.ahnaqvi.com'
    message['To'] = ",".join(receivers)
    dkim_selector="mail"
    with open(dkim_private_key_path, mode='r') as fd:
        dkim_private_key = fd.read() # To get der format from pem format, use base64 decode on the key

    headers = [b"To", b"From", b"Subject"]
    sender_domain = receivers[0].split("@")[-1]
    signature = dkim.sign(
                message=message.as_bytes(),
                selector=str(dkim_selector).encode(),
                domain=sender_domain.encode(),
                privkey=dkim_private_key.encode(),
                include_headers=headers,
    )


    message["DKIM-Signature"] = signature[len("DKIM-Signature: ") :].decode()

    smtp_server = smtplib.SMTP( receiver_smtp_server, port=25) 
    smtp_server.send_message(message)
    smtp_server.quit()

'''
Example:
-----------------

message_content = """From: No Reply <no_reply@mail.ahnaqvi.com>
To: Person <abdulhainaqvi@gmail.com>
Subject: Test Email

This is a test e-mail message.
"""
receivers = ['abdulhainaqvi@gmail.com']
sender = 'no_reply@mail.ahnaqvi.com'
subject = 'Testing'
receiver_smtp_server = 'alt4.gmail-smtp-in.l.google.com'
------------------

send_mail( sender, receivers, receiver_smtp_server, "/key/file", subject, message_content)

'''
