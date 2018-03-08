# -*- coding=utf-8 -*-
import redis
import time
import os

from PIL import Image

import logging
LOG_FORMAT = "%(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

pool = redis.ConnectionPool(host='192.168.33.10',port=6379,decode_responses=True)
rcon = redis.Redis(connection_pool=pool)

def listen_task():
    logging.info('waiting task...')
    signal=rcon.get('service1-nts')
    while signal!='stop':
        try:
            task = rcon.brpop('service1:queue', 0)[1]
            deal_data(task)
            signal=rcon.get('service1-nts')
        except Exception,e:
            logging.info(e)
    rcon.set('service1-nts','start')

def deal_data(img_path):
    
        t1=time.time()
        filename=os.path.basename(img_path)
        outfile='/nfs-data/service1/'+filename
        outfile = os.path.splitext(outfile)[0] + ".jpg"
        convert(img_path,outfile)
        rcon.lpush('service2:queue', outfile)
        logging.info('{} {:.3f} {:.3f}'.format(filename,time.time(),time.time()-t1))
    
    
def convert(img_path,outfile):
    Image.open(img_path).save(outfile)
 

if __name__ == '__main__':
    listen_task()