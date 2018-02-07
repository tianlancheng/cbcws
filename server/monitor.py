# -*- coding: utf-8 -*-
from threading import Timer
import requests
import time
import datetime
from pymongo import MongoClient
from concurrent import futures
from concurrent.futures import wait
import json
import docker

dockerClient=docker.DockerClient(base_url='unix://var/run/docker.sock', version='1.35')

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

	container_set.remove({'host_ip':host_ip,'update_time':{'$lt':update_time}})


def get_resource(host):
	try:
		r=requests.get('http://'+host['ip']+':'+str(host['port'])+'/resource')	
		r=r.json()
		print(host['host_name'],len(r['data']['containers']))
	except Exception as e:
		print(e)
		print('can not connect to: '+host['ip'])
		remove_host(host)
		return host['ip']
	try:			
		if r['status'] == 200:
			data=r['data']
			update_host(host,data.get('host'))
			update_containers(host['ip'],data.get('containers'))
		else:
			print('can not get resource: '+host['ip']+' '+r['msg'])
			host['state'] = 'unactive'
			host_set.save(host)
			container_set.remove({'host_id':host['ip']})
	except Exception as e:
		print(e)
	return host['ip']

def scale_out(service_name,labels,host_ips,resouces):
	step_size_cpu=labels.get('step_size_cpu')
	if not step_size_cpu:
		step_size_cpu=100000000
	step_size_mem=labels.get('step_size_mem')
	if not step_size_mem:
		step_size_mem=67108864
	flag=1
	for ip in host_ips:
		host=host_set.find_one({'host_ip':ip})
		remain_cpu=(1-host['cpu_percent']/100)-step_size_cpu/1000000000
		if remain_cpu<0.2 or host['memory_free']-step_size_mem<134217728:				
			flag=0
			break
	if not flag:
		print('no enough resource to scale-out')
		return False

	new_cpu_limit=resources['NanoCPUs']
	new_mem_limit=resources['MemoryBytes']
	if cpu_percent>0.9:					
		new_cpu_limit=old_cpu_limit+step_size_cpu
	if memory_percent>0.9			
		new_mem_limit=old_men_limit+step_size_mem
	new_resource=docker.types.Resources(cpu_limit=new_cpu_limit,mem_limit=new_mem_limit)
	res=service.update(resources=new_resource)
	print('scale-out':res)
	return res

def scale_up(service_name,labels,resources,n):
	max_num=labels.get('max_num')
	if n>=max_num:
		print('service num reaches maximum')
		return False
	flag=0
	hosts=host_set.find()
	for host in hosts:
		remain_cpu=(1-host['cpu_percent']/100)-resources['NanoCPUs']/1000000000
		if remain_cpu>0.2 and host['memory_free']-resources['MemoryBytes']>134217728:
			flag=1
			break
	if not flag:
		print('no enough resource to scale-out')
		return False
	n=n+1
	new_mode=docker.types.ServiceMode('replicated',n)
	res=service.update(mode=new_mode)
	# m=container_set.find({'service_name':service_name}).count()
	print('scale-up':res)
	return res

def scale():
	try:
		filters={
			'label':'autoscale'
		}
		service_list=dockerClient.services.list(filters=filters)
		for service in service_list:
			labels=service.attrs['Spec']['Labels']
			policy=labels['autoscale']
			containers=container_set.find({'service_name':service.name})
			cpu_percnets=0
			mem_usages=0
			mem_limits=0
			n=0
			host_ips=set()
			for container in containers:
				if container['state']=='running':
					host_ips.add(container['host_ip'])
					cpu_percnets=cpu_percnets+container['cpu_percent']
					mem_limits=container['memory_limit']
					mem_usages=container['mem_usage']
					n=n+1
			if n==0:
				continue
			cpu_avg_percent=cpu_percnets/n
			mem_percent=mem_usages/memory_limits
			resources=service.attrs['Spec']['TaskTemplate']['Resources']['Limits']
			cpu_avg_percent=cpu_avg_percent/(resources['NanoCPUs']/1000000000)
			print('cpu_avg:',cpu_avg_percent)
			print('mem_avg:',memory_percent)

			if cpu_percent>0.9 or memory_percent>0.9:
				if policy == 'scale-out':
					print('start scale-out')
					scale_out(service.name,labels,host_ips,resources)

				elif policy == 'scale-up':
					print('start scale-up')
					scale_up(service.name,labels,resources,n)

				elif policy == 'scale-out-up':
					print('start scale-out-up')
					res=scale_out(service.name,labels,host_ips,resources)
					if not res:
						scale_up(service.name,labels,resources,n)
				time.sleep(1)

	except Exception as e:
		print(e)


def cycle():
	t1=time.time()
	hosts=host_set.find()
	hosts=list(hosts[:])
	if hosts:
		workers=len(hosts)
		with futures.ThreadPoolExecutor(workers) as executor:
			future_tasks={executor.submit(get_resource,host) for host in hosts}
			results = wait(future_tasks)
		scale()
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