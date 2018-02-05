# -*- coding=utf-8 -*-

import redis
import time
import os

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont,ImageEnhance

pool = redis.ConnectionPool(host='localhost',port=6379,db=0)
rcon = redis.StrictRedis(connection_pool=self.pool)

def listen_task(self):
    while True:
        task = rcon.blpop('service2:queue', 0)[1]
        if task=='stop':
            break
        deal_data(task)


def deal_data(img_path):
    filename=os.path.basename(img_path)
    outfile='/nfs-data/service3/'+filename
    outfile = os.path.splitext(outfile)[0] + ".jpg"
    text_watermark(img_path,outfile)
    rcon.lpush('service3:queue', outfile)
    print filename,'{:.3f}'.format(time.time())

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


if __name__ == '__main__':
    socket_service()