# -*- coding=utf-8 -*-
import redis
import time
import os

from PIL import Image

pool = redis.ConnectionPool(host='localhost',port=6379,db=0)
rcon = redis.StrictRedis(connection_pool=self.pool)

def listen_task(self):
    while True:
        task = rcon.blpop('service1:queue', 0)[1]
        if task=='stop':
            break
        deal_data(task)

def deal_data(img_path):
    filename=os.path.basename(img_path)
    outfile='/nfs-data/service2/'+filename
    outfile = os.path.splitext(outfile)[0] + ".jpg"
    convert(img_path,outfile)
    rcon.lpush('service2:queue', outfile)
    print filename,'{:.3f}'.format(time.time())
    

def convert(img_path,outfile):
    try:
      Image.open(img_path).save(outfile)
    except IOError:
      print "cannot convert", img_path  
 

if __name__ == '__main__':
    listen_task()