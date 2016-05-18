import socket
import fcntl
import struct
import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# import HTMLParser
import emailer
import time
import json
import array

# class TagStripper(HTMLParser.HTMLParser):
#     collected_data = ""
#     def __init__(self):
#         HTMLParser.HTMLParser.__init__(self)

#     def handle_data(self, data):
#         self.collected_data = self.collected_data + data

#     def get_collected_data(self):
#         return self.collected_data

# def send_email(subj, msg):
#     try:
#         sender = config_data["sender"]
#         passwd = config_data["eml_passwd"]
#         receivers = config_data["recipients"]
#         message = MIMEMultipart('alternative')
#         message['Subject'] = subj
#         message['From'] = (config_data["unit"] +
#                            " <no_real_email@nobody.com>")
#         message['To'] = ','.join(receivers)
#         html = msg
#         ts = TagStripper()
#         ts.feed(html)
#         txt = ts.get_collected_data()
#         part1 = MIMEText(txt, 'plain')
#         part2 = MIMEText(html, 'html')
#         message.attach(part1)
#         message.attach(part2)
#         print message.as_string()
#         smtpo = smtplib.SMTP(config_data["smtp_server"])
#         smtpo.ehlo()
#         smtpo.starttls()
#         smtpo.login(sender.split('@', 1)[0], passwd)

#         smtpo.sendmail(sender, receivers, message.as_string())
#         smtpo.quit()
#         #print "Sent email"
#     except Exception, e:
#         print "Failure sending email. %s" % e

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  #SIOCGIFADDR
        struct.pack('256s', ifname[:15]))[20:24])

def all_interfaces():
    max_possible = 128
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    namestr = names.tostring()
    return [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)]

def broadcast_ip():
    global config_data
    with open('/etc/arduino_log.json') as data_file:
        config_data = json.load(data_file)

    if config_data["broadcast_ip"]:
        while config_data["iface"] not in all_interfaces():
            print "`{0}' not found.".format(config_data["iface"])
            time.sleep(15)

        message = """
        <html>
          <head></head>
          <body>
            <img src=\"http://icons.iconarchive.com/icons/alecive/flatwoken/512/Apps-Dialog-Shutdown-icon.png\" height=\"64\" width=\"64\">
            <p>IP:""" + get_ip_address(str(config_data["iface"])) + """
            </p>
          </body>
        </html>
            """
        emailer.send_email(config_data["smtp_server"],
                           config_data["sender"],
                           config_data["eml_passwd"],
                           [config_data["recipients"][0]],
                           "Unit: " + config_data["unit"] + " booted.",
                           message)

    else:
        print("Not sending...")

if __name__ == "__main__":
    broadcast_ip()
