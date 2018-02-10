# -*- coding=utf-8 -*-

import socket
import threading
import time
import sys
import os
import struct

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont,ImageEnhance

import logging
LOG_FORMAT = "%(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

def socket_service():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 7003))
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
        mkdir('mydata3')
        new_filename = os.path.join('./mydata3', fn)

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
        text_watermark(new_filename,new_filename)
        logging.info('{} {:.3f} {:.3f}'.format(filename,time.time(),time.time()-t1))
    except Exception,e:
        logging.info(e)


def text_watermark(img_path, out_path, text="logo",angle=23, opacity=0.50):  

    img = Image.open(img_path)
    watermark = Image.new('RGBA', img.size, (255,255,255))
  
    FONT = "Phetsarath_OT.ttf"  
    size = 2  
  
    n_font = ImageFont.truetype(FONT, size)                                      
    n_width, n_height = n_font.getsize(text)  
    text_box = min(watermark.size[0], watermark.size[1])  
    while (n_width+n_height <  text_box):  
        size += 2  
        n_font = ImageFont.truetype(FONT, size=size)  
        n_width, n_height = n_font.getsize(text)                                   
  
    text_width = (watermark.size[0] - n_width) / 2  
    text_height = (watermark.size[1] - n_height) / 2  
    #watermark = watermark.resize((text_width,text_height), Image.ANTIALIAS)  
    draw = ImageDraw.Draw(watermark, 'RGBA')                                       
    draw.text((text_width,text_height),  
                text, font=n_font, fill="#21ACDA")  
    watermark = watermark.rotate(angle, Image.BICUBIC)  
    alpha = watermark.split()[3]  
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)  
    watermark.putalpha(alpha)  
    Image.composite(watermark, img, watermark).save(out_path) 

 
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