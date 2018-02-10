# -*- coding=utf-8 -*-

import redis
import time
import os
import shutil

import logging
LOG_FORMAT = "%(message)s"

pool = redis.ConnectionPool(host='192.168.33.10',port=6379,db=0)
rcon = redis.StrictRedis(connection_pool=pool)


def send(i):
    filepath = 'a.png'
    if os.path.isfile(filepath):
        filename='{:.3f}'.format(time.time())+'_'+str(i)+'.png'
        
        out_file='/nfs-data/input/'+filename
        shutil.copyfile(filepath, out_file)
        rcon.lpush('service1:queue', out_file)
        logging.info(filename)

if __name__ == '__main__':
    num=int(sys.argv[1])
    t=float(sys.argv[2])
    logging.info('num={},t={}'.format(num,t))
    i=1
    while(i<=num):
        send(i)
        i=i+1
        time.sleep(t)