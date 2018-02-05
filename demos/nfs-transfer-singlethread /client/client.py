# -*- coding=utf-8 -*-

import redis
import time
import os
import shutil

pool = redis.ConnectionPool(host='localhost',port=6379,db=0)
rcon = redis.StrictRedis(connection_pool=self.pool)


def send(i):
    filepath = 'a.png'
    if os.path.isfile(filepath):
        filename='{:.3f}'.format(time.time())+'_'+str(i)+'.png'
        
        out_file='/nfs-data/service1/'+filename
        shutil.copyfile(filepath, out_file)
        rcon.lpush('service1:queue', outfile)

if __name__ == '__main__':
    i=1
    while(i<=100):
        send(i)
        i=i+1