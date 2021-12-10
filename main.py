import email
import imaplib
import logging
import smtplib
import sys
import time
from email import utils as emailutils
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from wand.api import library
from wand.image import Image

import pdf_tiff_cfg


def reply_email(original, newattached):
    reply_txt = ""
    reply_html = ""
    for part in original.walk():
        if part.get_content_type() == "text/plain":
            reply_txt = email.message_from_string(part.get_payload()).as_string()
        if part.get_content_type() == "text/html":
            reply_html = email.message_from_string(part.get_payload()).as_string()

    new = MIMEMultipart("mixed")
    body = MIMEMultipart("alternative")
    body.attach(MIMEText("Файлы преобразованы", "plain"))
    body.attach(MIMEText("<html>Файлы преобразованы</html>", "html"))
    new.attach(body)
    reply = MIMEMultipart("alternative")
    reply.attach(MIMEText(reply_txt, 'plain'))
    reply.attach(MIMEText(reply_html, 'html'))
    new.attach(reply)
    for attach in newattached:
        attached = MIMEApplication(newattach[attach], _subtype="tiff")
        attached.add_header('Content-Disposition', 'attachment', filename=attach[:-4] + ".tiff")
        new.attach(attached)

    new["Message-ID"] = emailutils.make_msgid()
    new["In-Reply-To"] = original["Message-ID"]
    new["References"] = original["Message-ID"]
    new["Subject"] = "Re: " + original["Subject"]
    new["To"] = original["Reply-To"] or original["From"]
    new["From"] = pdf_tiff_cfg.emailaddress
    try:
        s = smtplib.SMTP(pdf_tiff_cfg.mailserver, 587)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(pdf_tiff_cfg.emailaddress, pdf_tiff_cfg.mailpassword)
        s.sendmail(pdf_tiff_cfg.emailaddress, [new["To"]], new.as_string().encode('utf-8'))
        logging.info("Письмо с ответом отправлено")
        s.quit()
    except:
        logging.error("Не удалось соединиться с сервером SMTP")
        sys.exit(1)


if __name__ == '__main__':
    FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    logger = logging.getLogger("pdf-tiff")
    while True:
        conn = imaplib.IMAP4_SSL(pdf_tiff_cfg.mailserver)
        try:
            (retcode, capabilities) = conn.login(pdf_tiff_cfg.maillogin, pdf_tiff_cfg.mailpassword)
            logging.info("Соединение с сервером IMAP " + pdf_tiff_cfg.mailserver + " успешно")
        except:
            logging.error("Не удалось соединиться с сервером IMAP")
            sys.exit(1)
        conn.select()
        typ, data = conn.search(None, 'UNSEEN')
        if len(data[0].split()) > 0:
            logging.info("Найдены новые письма")
            for num in data[0].split():
                pdf = False
                newattach = {}
                typ, data = conn.fetch(num, '(RFC822)')
                mailbody = email.message_from_bytes(data[0][1])
                for payload in mailbody.walk():
                    if payload.get_content_type().find("pdf") > 0:
                        pdf = True
                        logging.info("Получено сообщение от " + mailbody["From"] + " c файлом " + payload.get_filename())
                        file = payload.get_payload(decode=True)
                        with Image(blob=file, resolution=pdf_tiff_cfg.resolution) as img:
                            img.type = pdf_tiff_cfg.imgtype
                            img.compression = pdf_tiff_cfg.imgcompression
                            # Manually iterate over all page, and turn off alpha channel.
                            library.MagickResetIterator(img.wand)
                            for idx in range(library.MagickGetNumberImages(img.wand)):
                                library.MagickSetIteratorIndex(img.wand, idx)
                                img.alpha_channel = 'off'
                            newattach[payload.get_filename()] = img.make_blob('tiff')
                            logging.info("Файл " + payload.get_filename() + " преобразован")
                if pdf:
                    reply_email(mailbody, newattach)
        else:
            logging.info("Новых писем нет")
        conn.close()
        logging.info("Ожидаем 3 минуты")
        time.sleep(180)
