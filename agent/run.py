# -*- coding: utf-8 -*-
from flask import Flask
from flask import request
from flask import jsonify
import json
import psutil
import socket
import docker
import datetime,time
from concurrent import futures

app = Flask(__name__)
app.config['serverUrl']='http://192.168.33.10:5000/agent/register'
app.config['myport']=5001

dockerClient=docker.DockerClient(base_url='unix://var/run/docker.sock', version='1.35')

def ns(endTime,startTime):
	t1= datetime.datetime.strptime(startTime.split('.')[0],"%Y-%m-%dT%H:%M:%S")
	t2= datetime.datetime.strptime(endTime.split('.')[0],"%Y-%m-%dT%H:%M:%S")  
	seconds1 = (t2 - t1).seconds
	end1=len(startTime)-1
	end2=len(endTime)-1
	seconds2=float('0.'+endTime[20:end2])-float('0.'+startTime[20:end1])
	return (seconds1+seconds2)*1000000000

host=None
containers=None
def set_host(future):
    host=future.result()

def set_containers(future):
	containers.append(future.result())

def get_host_info():
	memory=psutil.virtual_memory()
	host={	
		"host_name":socket.gethostname(),
		"cpu_count": psutil.cpu_count(),
		"cpu_percent": psutil.cpu_percent(interval=1),
		"memory_total": memory.total,
		"memory_used": memory.used,
		"memory_free": memory.free,
		"memory_percent": memory.percent
		}
	return host

def get_container_info(container_obj):
	container={
		"id": container_obj.short_id,
		"name": container_obj.name,
		"state": container_obj.status,
		"image": container_obj.image.tags,
		"labels": container_obj.labels,
		"memory_usage": None,
		"memory_limit": None,
		"cpu_percent": None,
		"online_cpus": None,
		"service_name": container_obj.labels.get('com.docker.swarm.service.name')
	}
	if container['state'] == 'running':
		stats=container_obj.stats(stream=False)
		precpu_usage_total=stats['precpu_stats']['cpu_usage']['total_usage']
		cpu_usage_total=stats['cpu_stats']['cpu_usage']['total_usage']
		preread_time=stats['preread']
		read_time=stats['read']
		cpu_percent=(cpu_usage_total-precpu_usage_total)/ns(read_time,preread_time)

		container['memory_usage']=stats['memory_stats']['usage']
		container['memory_limit']=stats['memory_stats']['limit']
		container['cpu_percent']=cpu_percent
		container['online_cpus']=stats['cpu_stats']['online_cpus']

	return container


@app.route('/resource',methods=['GET'])
def get_resource():
	try:
		host=None
		containers=[]
		
		containet_list = dockerClient.containers.list(all=1)
		workers=len(containet_list)+1
		with futures.ThreadPoolExecutor(workers) as executor:
			task1=executor.submit(get_host_info)
			future_tasks={executor.submit(get_container_info,item) for item in containet_list}
			host=task1.result()
			containers=[f.result() for f in future_tasks]

		return jsonify(status=200, msg='success', data={"host":host,"containers":containers}), 200
	except Exception as e:
		app.logger.error(e)
	return jsonify(status=400, msg='error', data=None), 400

def register_to_server():
	print('register_to_server')
	import requests
	data={
		"host_name": socket.gethostname(),
		"port": app.config['myport']
	}
	try:
		r=requests.post(app.config['serverUrl'], data = json.dumps(data))
		if r.status_code == 200:
			return True
		else:
			print(r.json())
	except:
		return False
	return False



if __name__ == '__main__':
	if register_to_server():
		app.run(host='0.0.0.0',port=app.config['myport'],debug=False,threaded=True)
	else:
		print('register to server error')

