# -*- coding: utf-8 -*-
from flask import Flask
from flask import request
from flask import jsonify
import json
import docker
import config
from flask_pymongo import PyMongo
from base import require_args,require_json

app = Flask(__name__)

dockerClient=docker.DockerClient(base_url='unix://var/run/docker.sock', version='1.35')
app.config.from_object(config)
mongo = PyMongo(app)


@app.route('/service',methods=['POST'])
@require_json('image')
def add_service():
	data = json.loads(request.get_data())
	image=data['image']
	command=data.get('command')
	kwargs=data.get('kwargs')
	service=dockerClient.services.create(image, command=command, **kwargs)
	return jsonify(status=200, msg='add service success', data={'id':service.short_id,'name':service.name}), 200

@app.route('/service/<id>',methods=['PUT'])
def update_service(id):
	data = json.loads(request.get_data())
	try:
		service=dockerClient.services.get(id)
	except:
		return jsonify(status=400, msg='does not exist', data=None), 400
	kwargs=data.get('kwargs')
	mode_obj=kwargs.pop('mode')
	mode=docker.types.ServiceMode(mode_obj['mode'],mode_obj['replicas'])
	kwargs['mode']=mode
	res=service.update(**kwargs)
	return jsonify(status=200, msg='update service success', data=None), 200

@app.route('/service/<id>',methods=['DELETE'])
def delete_service(id):
	try:
		service=dockerClient.services.get(id)
		if not service:
			return jsonify(status=400, msg='does not exist', data=None), 400
		if service.remove():
			return jsonify(status=200, msg='delete service success', data=None), 200
	except Exception as e:
		print e
	return jsonify(status=400, msg='delete service error', data=None), 400

@app.route('/services',methods=['GET'])
def get_services():
	try:
		kwargs=request.values
		service_list=dockerClient.services.list(**kwargs)
		services=[]
		for service in service_list:
			item={
				"id":service.short_id,
				"name":service.name
			}
			services.append(item)
		return jsonify(status=200, msg='get services success', data=services), 200
	except Exception as e:
		print e
	return jsonify(status=400, msg='get services error', data=None), 400


@app.route('/agent/register',methods=['POST'])
def agent_register():
	try:
		ip=request.remote_addr
		print 'register:'+ip
		data = json.loads(request.get_data())
		host_set=mongo.db.host_set
		
		host=host_set.find_one({'ip':ip})
		if not host:
			host={}
		host['ip']=ip
		host['host_name']=data.get('host_name')
		host['port']=data.get('port')
		host['state']='active'
		id=host_set.save(host)

		new=host_set.find_one({'_id':id})
		new['_id']=str(new['_id'])
		return jsonify(status=200, msg='add success', data=new), 200
	except Exception as e:
		print e
	return jsonify(status=400, msg='add error', data=None), 400


if __name__ == '__main__':
	app.run(host='0.0.0.0',port=5000,debug=False,threaded=True)
