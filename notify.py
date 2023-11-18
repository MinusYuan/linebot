from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from sendgrid.helpers.mail import Cc, Bcc, To
import pandas as pd
import mimetypes
import base64
import os

class EMail:
    def __init__(self, api_key):
        self.sg = SendGridAPIClient(api_key)
        self.subject_prefix = "[NovaWide Tech]"

    def send(self, to_emails, cc_emails, subject, message, attachments=[], bcc_emails=[]):
        def encoded_file(fn):
            print(f"encoded_file: {fn}")
            if isinstance(fn, pd.DataFrame):
                ctype = 'text/csv'
                data = fn.to_csv(index=False).encode()
            else:
                ctype, encoding = mimetypes.guess_type(file)
                with open(fn, 'rb') as f:
                    data = f.read()
            return ctype, base64.b64encode(data).decode()

        if isinstance(attachments, str):
            attachments = [attachments]

        def to_mail_list(mails, func=None):
            if isinstance(mails, str):
                return [func(m) if func else m for m in mails.split(',')]
            elif isinstance(mails, list) and mails and isinstance(mails[0], str):
                return [func(m) if func else m for m in mails]
            return mails

        contents = Mail(
            from_email='no-reply@novawidetech.com',
            to_emails=to_mail_list(to_emails),
            subject=f"{self.subject_prefix} {subject}",
            html_content=message
        )
        # CC/BCC List
        if cc_emails:
            contents.cc = to_mail_list(cc_emails)
        if bcc_emails:
            contents.bcc = to_mail_list(bcc_emails)

        # Attachments
        if attachments:
            att_lst = []
            for file in attachments:
                ctype, encoded = encoded_file(file)
                # print(f"Ctype: {ctype}, encoded: {encoded}")

                att = Attachment(FileContent(encoded),
                             FileName(file),
                             FileType(ctype),
                             Disposition('attachment'))
                att_lst.append(att)

            contents.attachment = att_lst
        self.sg.send(contents)
        for file in attachments:
            os.remove(file)