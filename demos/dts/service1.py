# -*- coding=utf-8 -*-

import socket
import threading
import time
import sys
import os
import struct
import logging

from PIL import Image

import logging
LOG_FORMAT = "%(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

def socket_service():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 7001))
        s.listen(10)
    except socket.error as msg:
        logging.info(msg)
        sys.exit(1)
    logging.info('Waiting connection...')

    while 1:
        conn, addr = s.accept()
        buf = conn.recv(struct.calcsize('128sl'))
        if buf:
            filename, filesize = struct.unpack('128sl', buf)
            if filename == 'stop':
                conn.close()
                time.sleep(2)
                break
            deal_data(conn,filename, filesize)
        else:
            conn.close()
        # time.sleep(0.1)

def deal_data(conn,filename, filesize):
    #conn.settimeout(500)
    try:
        t1=time.time()
        fn = filename.strip('\00')
        mkdir('mydata1')
        new_filename = os.path.join('./mydata1', fn)

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
        res=convert(new_filename)
        try:
            sendfile(res)
        except:
            logging('Error,retry send')
            time.sleep(0.5)
            sendfile(res)
        logging.info('{} {:.3f} {:.3f}'.format(filename,time.time(),time.time()-t1))
    except Exception,e:
        logging.info(e)


def sendfile(filepath):
    if os.path.isfile(filepath):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('service2-dts', 7002))
    

        # 定义定义文件信息。128s表示文件名为128bytes长，l表示一个int或log文件类型，在此为文件大小
        fileinfo_size = struct.calcsize('128sl')
        # 定义文件头信息，包含文件名和文件大小
        fhead = struct.pack('128sl', os.path.basename(filepath),
                            os.stat(filepath).st_size)
        s.send(fhead)

        fp = open(filepath, 'rb')
        while 1:
            data = fp.read(1024)
            if not data:
                break
                s.send(data)

        s.close()


def convert(img_path):
  outfile = os.path.splitext(img_path)[0] + ".jpg"
  if img_path != outfile:
      Image.open(img_path).save(outfile)
  return outfile
 
def mkdir(path):
    import os
    path=path.strip()
    path=path.rstrip("\\")
    isExists=os.path.exists(path)
    if not isExists:
        os.makedirs(path) 
        return True
    else:
        return False

if __name__ == '__main__':
    socket_service()