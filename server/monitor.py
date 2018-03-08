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
import os
import socket
import struct

import redis
pool = redis.ConnectionPool(host='192.168.33.10',port=6379,db=0)
rcon = redis.StrictRedis(connection_pool=pool)

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

def ns(endTime,startTime):
	t1= datetime.datetime.strptime(startTime.split('.')[0],"%Y-%m-%dT%H:%M:%S")
	t2= datetime.datetime.strptime(endTime.split('.')[0],"%Y-%m-%dT%H:%M:%S")  
	seconds1 = (t2 - t1).seconds
	end1=len(startTime)-1
	end2=len(endTime)-1
	seconds2=float('0.'+endTime[20:end2])-float('0.'+startTime[20:end1])
	return (seconds1+seconds2)*1000000000

def update_containers(host_ip,containers):
	update_time=datetime.datetime.now()
	if containers:
		for container in containers:
			
			item=container_set.find_one({'host_ip':host_ip,'id':container['id']})
			container['cpu_percent']=0.0
			if item:
				if item['cpu_usuage_total'] and container['cpu_usuage_total']:
					container['_id']=item['_id']
					precpu_usage_total=item['cpu_usuage_total']
					preread=item['read']
					cpu_usage_total=container['cpu_usuage_total']
					read=container['read']
					container['cpu_percent']=(cpu_usage_total-precpu_usage_total)/ns(read,preread)
			container['host_ip']=host_ip
			container['update_time']=update_time
			container['labels']=json.dumps(container['labels'])
			container_set.save(container)

	container_set.remove({'host_ip':host_ip,'update_time':{'$lt':update_time}})


def get_resource(host):
	try:
		r=requests.get('http://'+host['ip']+':'+str(host['port'])+'/resource')	
		r=r.json()
		# print(host['host_name'],len(r['data']['containers']))
	except Exception as e:
		print(e)
		print('can not connect to: '+host['ip'])
		# remove_host(host)
		return host['ip']
	try:			
		if r['status'] == 200:
			data=r['data']
			update_host(host,data.get('host'))
			update_containers(host['ip'],data.get('containers'))
		else:
			print('Error:can not get resource: '+host['ip']+' '+r['msg'])
			host['state'] = 'unactive'
			host_set.save(host)
			container_set.remove({'host_id':host['ip']})
	except Exception as e:
		print('Error:',e)
	return host['ip']

def stop_service(service_name):
	if(service_name.startswith('service1')):
		port=7001
	elif(service_name.startswith('service2')):
		port=7002
	else:
		port=7003
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('localhost', port))
	fileinfo_size = struct.calcsize('128sl')
	filename='stop'
	fhead = struct.pack('128sl', filename.encode('utf-8'),11)
	s.send(fhead)
	res=s.recv(1024).decode('utf-8')
	s.close()
	return res


def scale_out(service,host_ips):
	service_name=service.name
	labels=service.attrs['Spec']['Labels']
	resources=service.attrs['Spec']['TaskTemplate']['Resources']['Limits']
	if resources['NanoCPUs']>=500000000:
		print('service num reaches maximum')
		return False
	step_size_cpu=labels.get('step_size_cpu')
	if not step_size_cpu:
		step_size_cpu=100000000
	# step_size_mem=labels.get('step_size_mem')
	# if not step_size_mem:
	# 	step_size_mem=67108864
	flag=1
	for ip in host_ips:
		host=host_set.find_one({'ip':ip})
		remain_cpu=(1-host['cpu_percent']/100)-step_size_cpu/1000000000
		if remain_cpu<0.2: #or host['memory_free']-step_size_mem<134217728:				
			flag=0
			break
	if not flag:
		print('no enough resource to scale-out')
		return False

	# new_mem_limit=resources['MemoryBytes']
	new_cpu_limit=resources['NanoCPUs']+step_size_cpu
	# print('stop:'+stop_service(service_name))
	rcon.set(service_name, 'stop')
	if rcon.get(service_name)!='start':
		time.sleep(1)
	print('stop end')
	# if memory_percent>0.9:
	# 	new_mem_limit=old_men_limit+step_size_mem
	# new_resource=docker.types.Resources(cpu_limit=new_cpu_limit,mem_limit=new_mem_limit)
	# res=service.update(resources=new_resource)

	cmd='docker service update --limit-cpu '+str(new_cpu_limit/1000000000)+' '+service_name
	print(cmd)
	p=os.popen('docker service update --limit-cpu '+str(new_cpu_limit/1000000000)+' '+service_name)

	# os.system(cmd)
	# print(p.read())
	print('scale-out to '+str(new_cpu_limit))
	return True

def scale_up(service,num):
	service_name=service.name
	labels=service.attrs['Spec']['Labels']
	resources=service.attrs['Spec']['TaskTemplate']['Resources']['Limits']
	max_num=labels.get('max_num')
	if max_num:
		max_num=int(max_num)
		if num>max_num:
			print('service num reaches maximum')
			return False
	flag=0
	hosts=host_set.find()
	for host in hosts:
		remain_cpu=(1-host['cpu_percent']/100)-resources['NanoCPUs']/1000000000
		if remain_cpu>0.2: #and (host['memory_free']-resources['MemoryBytes'])>134217728:
			flag=1
			break
	if not flag:
		print('no enough resource to scale-up')
		return False
	p=os.popen('docker service scale '+service_name+'='+str(num))
	# print(p.read())
	# new_mode=docker.types.ServiceMode('replicated',n)
	# res=service.update(mode=new_mode)
	# m=container_set.find({'service_name':service_name}).count()
	print('scale-up to '+str(num))
	return True

def scale():
	try:
		filters={
			'label':'autoscale'
		}
		scale_service=None
		cpu_max=0
		m=0
		service_list=dockerClient.services.list(filters=filters)
		for service in service_list:
			
			labels=service.attrs['Spec']['Labels']
			policy=labels['autoscale']
			containers=container_set.find({'service_name':service.name})
			
			cpu_percnets=0
			# mem_percnets=0
			n=0
			host_ips=set()
			for container in containers:
				if container['state']!='exited':
					host_ips.add(container['host_ip'])
					cpu_percnets=cpu_percnets+container['cpu_percent']
					# mem_percnets=mem_percnets+container['memory_usage']/container['memory_limit']
					n=n+1
			print(service.name,n)
			if n==0:
				continue
			cpu_avg_percent1=cpu_percnets/n
			# mem_avg_percent=mem_percnets/n
			resources=service.attrs['Spec']['TaskTemplate']['Resources']['Limits']
			cpu_avg_percent=cpu_avg_percent1/(resources['NanoCPUs']/1000000000)
			print('cpu_avg:',cpu_avg_percent1,cpu_avg_percent)
			print('cpu_limit:',resources['NanoCPUs'])
			# print('mem_avg:',mem_avg_percent)
			if cpu_avg_percent>cpu_max:
				cpu_max=cpu_avg_percent
				scale_service=service
				m=n+1

		if cpu_max>0.9:
			if policy == 'scale-out':
				print('start scale-out '+scale_service.name)
				scale_out(scale_service,host_ips)

			elif policy == 'scale-up':
				print('start scale-up '+scale_service.name)
				scale_up(scale_service,m)

			elif policy == 'scale-out-up':
				print('start scale-out-up '+scale_service.name)
				res=scale_out(scale_service,host_ips)
				if not res:
					scale_up(scale_service,m)

	except Exception as e:
		print('Error:',e)


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
	print()
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