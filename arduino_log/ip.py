import socket
import fcntl
import struct
import smtplib
import time
import json
import array

def send_email(subj, msg):
    try:
        sender = config_data["sender"]
        receivers = config_data["recipients"]
        message = "From: " + config_data["unit"]  + " <no_real_email@nobody.com>"
        message += "\nTo: "

        rec_cnt = len(receivers)
        cnt = 1
        for s in receivers:
            message += "<" + s
            message += ">"
            if cnt < rec_cnt:
                message += ", "

        message += "\nSubject: "

        message += subj + "\n\n"
        message += msg + "\n"
        smtpo = smtplib.SMTP(config_data["smtp_server"])
        smtpo.sendmail(sender, receivers, message)
        #print "Sent email"
    except Exception, e:
        print "Failure sending email. %s" % e

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
    with open('/etc/thingspeak.json') as data_file:
        config_data = json.load(data_file)

    while 'wlan0' not in all_interfaces():
        time.sleep(15)

    send_email("Unit: " + config_data["unit"] + " booted.",
               "IP: " + get_ip_address('wlan0'))


if __name__ == "__main__":
    broadcast_ip()
