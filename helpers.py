import os
import shutil
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import configparser
from db import conn
config = configparser.ConfigParser()
config.read('config.ini')

def send_mail(subject='',toMailid=None,attachmentPath=None):
    try:
        sender_email = config['mail']['username']
        toMailid = 'ranjith@indsysholdings.com'
        
        cursor = conn.cursor()
        # Check if test_mode is enabled
        cursor.execute("SELECT test_mode, to_emailids, cc_emailids FROM test_mode WHERE id=1")
        test_mode_data = cursor.fetchone()
        cc_emails = []
        if test_mode_data and test_mode_data[0] == 1:
            to_emails = test_mode_data[1].split(',')
            cc_emails = test_mode_data[2].split(',')
        else:
            to_emails = [toMailid]
            
        conn.close()
        
        all_recipients = to_emails + cc_emails
        
        subject = subject
        message = """<p>Hi </p>

                    <p>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;Please, find the Curved artwork attached in the mail.</p>

                    <p>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Kindly check and provide acknowledgment or feedback if any, within 8 hours * to avoid any further delay</p>

                    <p>Thanks and Regards,</p>

                    <p>Design Team</p>

                    <p>INDSYS Holdings India Private Limited</p>"""

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        
        for pdf_file_path in Path(attachmentPath).rglob('*.pdf'):
            with open(pdf_file_path, "rb") as attachment:
                pdfFilename =  os.path.basename(pdf_file_path).split('/')[-1]
                pdfFileBasename = os.path.splitext(pdf_file_path)[0]
                part = MIMEApplication(attachment.read(), Name="your_file.pdf")
                part['Content-Disposition'] = f'attachment; filename="{pdfFilename}"'
                msg.attach(part)

        msg.attach(MIMEText(message, 'html'))

        smtp_server = config['mail']['smtp']
        smtp_port = config['mail']['port']  # 587 for TLS, 465 for SSL

        # Establish a secure connection to the server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

        email_password = config['mail']['password']
        server.login(sender_email, email_password)
        print('Mail is sending...')
        server.sendmail(sender_email, all_recipients, msg.as_string())
        print('sent successfully...')
        server.quit()
        print({"status": "success", "msg": "customer approval mail send successfully"})
        return {"status": "success", "msg": "customer approval mail send successfully"}
    except Exception as e:
        error_message = {"status": "failed", "msg": "Mail sending failed : " + str(format(e)).replace("'", '"').strip()}
        print(error_message)
        return error_message
     

def delete_folder_contents_only(folder_path):
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                os.remove(file_path)  # Delete the file
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                shutil.rmtree(dir_path)  # Delete the folder and its contents
                print(f"Deleted folder: {dir_path}")
            except Exception as e:
                print(f"Error deleting folder {dir_path}: {e}")
    
        
def delete_folder_and_files(folder_path):
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                os.remove(file_path)  # Delete the file
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                shutil.rmtree(dir_path)  # Delete the folder and its contents
                print(f"Deleted folder: {dir_path}")
            except Exception as e:
                print(f"Error deleting folder {dir_path}: {e}")
    try:
        shutil.rmtree(folder_path)
        print(f"Deleted main folder: {folder_path}")
    except Exception as e:
        print(f"Error deleting main folder {folder_path}: {e}")
