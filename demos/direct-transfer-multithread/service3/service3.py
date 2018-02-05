# -*- coding=utf-8 -*-

import socket
import threading
import time
import sys
import os
import struct

from PIL import Image,ImageFilter 


def socket_service():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 7003))
        s.listen(10)
    except socket.error as msg:
        print msg
        sys.exit(1)
    print 'Waiting connection...'

    while 1:
        conn, addr = s.accept()
        msg=conn.recv(1024)
        if msg == 'stop':
            conn.close()
            time.sleep(2)
            break
        t = threading.Thread(target=deal_data, args=(conn, addr))
        t.start()

def deal_data(conn, addr):
    #conn.settimeout(500)

    fileinfo_size = struct.calcsize('128sl')
    buf = conn.recv(fileinfo_size)
    if buf:
        filename, filesize = struct.unpack('128sl', buf)
        fn = filename.strip('\00')
        new_filename = os.path.join('./data', fn)

        recvd_size = 0  # 定义已接收文件的大小
        fp = open(new_filename, 'wb')

        while not recvd_size == filesize:
            if filesize - recvd_size > 1024:
                data = conn.recv(1024)
                recvd_size += len(data)
            else:
                data = conn.recv(filesize - recvd_size)
                recvd_size = filesize
            fp.write(data)
        fp.close()
    conn.close()
    filter(new_filename)
    print fn,'{:.3f}'.format(time.time())



def filter(img_path):
    try:
        img=Image.open(img_path)
        imgfilted = img.filter(ImageFilter.SHARPEN)  
        imgfilted.save(img_path)
    except IOError:
      print "cannot filter", img_path
 

if __name__ == '__main__':
    socket_service()