import codecs
from datetime import datetime
import glob
import html
import quopri
import os.path
import pystache
import sys
import weasyprint
from email.parser import Parser


class UOCMail:
    def __init__(self, filename):
        p = Parser()
        with codecs.open(filename, "r", "latin1") as f:
            value = f.read()
        raw_mail = p.parsestr(value)
        
        self.date = datetime.strptime(raw_mail['Date'], "%a, %d %b %Y %H:%M:%S %z")
        self.subject = raw_mail['Subject']
        self.username = raw_mail['From']
        self.uoc_id = raw_mail['X-Uoc-Id']
        self.uoc_parent_id = raw_mail['X-UOC-PARENT_MAILID']
        
        self.parent = None
        self.children = []

        content_list = []
        for part in raw_mail.walk():
            if part['Content-Transfer-Encoding'] == 'quoted-printable':
                payload = part.get_payload()
                try:
                    payload = str(quopri.decodestring(payload), 'iso-8859-1')
                except:
                    pass
                if part.get_content_type() == 'text/plain':
                    content_list.append("<div class=\"pre\">{}</div>".format(html.unescape(payload)))
                elif part.get_content_type() == 'text/html':
                    content_list.append(payload)
                else:
                    content_list.append("<div class=\"pre\">{}</div>".format(html.unescape(payload)))
        self.content_list = content_list

class UOCForum:
    def __init__(self, name, filepattern):
        mails = {}
        filepattern = os.path.expanduser(filepattern)
        for mail_name in glob.glob(filepattern):
            mail = UOCMail(mail_name)
            mails[mail.uoc_id] = mail

        for mail in mails.values():
            mail.parent = mails.get(mail.uoc_parent_id, None)
            if mail.parent is not None:
                mail.parent.children.append(mail)

        root = [mail for mail in mails.values() if mail.parent is None]
        root = sorted(root, key=lambda x: x.date, reverse=True)
        
        self.name = name
        self.mails = mails
        self.children = root

def main(title, filepattern, outname):
    forum = UOCForum(title, filepattern)
    renderer = pystache.Renderer()
    s = renderer.render_path("main.mustache", forum)
    pdf = weasyprint.HTML(string=s).write_pdf()
    with open(outname, 'wb') as f:
        f.write(pdf)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("E: {} <title> <filepattern> <output file name>".format(sys.argv[0]), file=sys.stderr)
        sys.exit(-1)
    title = sys.argv[1]
    filepattern = sys.argv[2]
    outname = sys.argv[3]
    main(title, filepattern, outname)