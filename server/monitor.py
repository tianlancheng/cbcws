# -*- coding: utf-8 -*-
from threading import Timer
import requests
import time
import datetime
from pymongo import MongoClient
from concurrent import futures
from concurrent.futures import wait
import json

client = MongoClient('localhost', 27017)
db = client.cbcws
host_set = db.host_set
container_set = db.container_set

def remove_host(host):
	if host['state'] == 'active':
		host['state'] = 'unactive'
		host_set.save(host)
	else:
		host_set.remove(host)
		container_set.remove({'host_id':host_ip})

def update_host(host,host_info):
	update_time=datetime.datetime.now()
	if host_info:
		host['state']='active'
		host['host_name']=host_info.get('host_name')
		host['cpu_count']=host_info.get('cpu_count')
		host['cpu_percent']=host_info.get('cpu_percent')
		host['memory_free']=host_info.get('memory_free')
		host['memory_total']=host_info.get('memory_total')
		host['memory_used']=host_info.get('memory_used')
		host['memory_percent']=host_info.get('memory_percent')
		host['update_time']=update_time
		host_set.save(host)

def update_containers(host_ip,containers):
	update_time=datetime.datetime.now()
	if containers:
		for container in containers:
			
			item=container_set.find_one({'host_ip':host_ip,'id':container['id']})
			if item:
				container['_id']=item['_id']
			container['host_ip']=host_ip
			container['update_time']=update_time
			container['labels']=json.dumps(container['labels'])
			container_set.save(container)

	container_set.remove({'update_time':{'$lt':update_time}})


def get_resource(host):
	try:
		r=requests.get('http://'+host['ip']+':'+str(host['port'])+'/resource')		
	except Exception as e:
		print(e)
		print('can not connect to: '+host['ip'])
		remove_host(host)
	try:			
		if r.status_code == 200:
			r=r.json()
			data=r['data']
			update_host(host,data.get('host'))
			update_containers(host['ip'],data.get('containers'))
		else:
			print('can not get resource: '+host['ip'])
			host['state'] = 'unactive'
			host_set.save(host)
			container_set.remove({'host_id':host['ip']})
	except Exception as e:
		print(e)
	return host['ip']

def cycle():
	t1=time.time()
	hosts=host_set.find()
	hosts=list(hosts[:])
	if hosts:
		workers=len(hosts)
		with futures.ThreadPoolExecutor(workers) as executor:
			future_tasks={executor.submit(get_resource,host) for host in hosts}
			results = wait(future_tasks)
	print(time.time()-t1)
	print
	t = Timer(1,cycle)
	t.start()

if __name__ == '__main__':
	cycle()




# import aiohttp
# import asyncio
# import json

# async def get_resource(host):
# 	async with aiohttp.ClientSession() as session:
# 		async with session.get('http://'+host['ip']+':'+str(host['port'])+'/resource') as response:
# 			try:
# 				res = await response.read()
# 				res=json.loads(res.decode())
# 				if res['status'] == 200:
# 					data=res['data']
# 					update_host(host,data.get('host'))
# 					update_containers(host['ip'],data.get('containers'))
# 				else:
# 					print('can not get resource: '+host['ip'])
# 					host['state'] = 'unactive'
# 					host_set.save(host)
# 			except Exception as e:
# 				print(e)
# 				print('can not connect to: '+host['ip'])
# 				remove_host(host)