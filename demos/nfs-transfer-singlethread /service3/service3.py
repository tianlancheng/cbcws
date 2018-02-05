# -*- coding=utf-8 -*-

import redis
import time
import os

from PIL import Image,ImageFilter 


pool = redis.ConnectionPool(host='localhost',port=6379,db=0)
rcon = redis.StrictRedis(connection_pool=self.pool)

def listen_task(self):
    while True:
        task = rcon.blpop('service3:queue', 0)[1]
        if task=='stop':
            break
        deal_data(task)

def deal_data(img_path):
    filename=os.path.basename(img_path)
    outfile='/nfs-data/result/'+filename
    outfile = os.path.splitext(outfile)[0] + ".jpg"
    filter(img_path,outfile)
    print filename,'{:.3f}'.format(time.time())

def filter(img_path,outfile):
    try:
        img=Image.open(img_path)
        imgfilted = img.filter(ImageFilter.SHARPEN)  
        imgfilted.save(outfile)
    except IOError:
      print "cannot filter", img_path
 

if __name__ == '__main__':
    socket_service()