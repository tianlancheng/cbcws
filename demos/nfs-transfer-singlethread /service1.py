# -*- coding=utf-8 -*-
import redis
import time
import os

from PIL import Image

import logging
LOG_FORMAT = "%(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

pool = redis.ConnectionPool(host='192.168.0.104',port=6379,decode_responses=True)
rcon = redis.Redis(connection_pool=pool)

def listen_task():
    logging.info('waiting task...')
    while True:
        task = rcon.blpop('service1:queue', 0)[1]
        if task=='stop':
            break
        deal_data(task)

def deal_data(img_path):
    try:
        t1=time.time()
        filename=os.path.basename(img_path)
        outfile='/nfs-data/service1/'+filename
        outfile = os.path.splitext(outfile)[0] + ".jpg"
        convert(img_path,outfile)
        rcon.lpush('service2:queue', outfile)
        logging.info('{} {:.3f} {:.3f}'.format(filename,time.time(),time.time()-t1))
    except Exception,e:
        logging.info(e)
    

def convert(img_path,outfile):
    Image.open(img_path).save(outfile)
 

if __name__ == '__main__':
    listen_task()