# -*- coding=utf-8 -*-

import socket
import os
import sys
import struct
import time


def socket_client(i):
    filepath = 'a.png'
    if os.path.isfile(filepath):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 7001))
        except socket.error as msg:
            print msg
            sys.exit(1)
  
        # 定义定义文件信息。128s表示文件名为128bytes长，l表示一个int或log文件类型，在此为文件大小
        fileinfo_size = struct.calcsize('128sl')
        # 定义文件头信息，包含文件名和文件大小
        filename='{:.3f}'.format(time.time())+'_'+str(i)+'.png'
        fhead = struct.pack('128sl', filename,
                            os.stat(filepath).st_size)
        s.send(fhead)
        print filename

        fp = open(filepath, 'rb')
        while 1:
            data = fp.read(1024)
            if not data:
                break
            s.send(data)
        s.close()



if __name__ == '__main__':
    i=1
    while(i<=100):
        socket_client(i)
        i=i+1