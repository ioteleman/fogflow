from flask import Flask, jsonify, abort, request, make_response
import requests 
import json
import time
import datetime
import threading
import os


app = Flask(__name__, static_url_path = "")

# global variables
brokerURL = ''
outputs = []
timer = None
lock = threading.Lock()
counter = 0 

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route('/admin', methods=['POST'])
def admin():    
    if not request.json:
        abort(400)
    
    configObjs = request.json
    handleConfig(configObjs)    
        
    return jsonify({ 'responseCode': 200 })


@app.route('/notifyContext', methods = ['POST'])
def notifyContext():
    print "=============notify============="
    data=request.get_json()
    print(data)
    if not request.json:
        abort(400)
    	
    objs = readContextElements(request.json)
    print(objs)
    global counter
    counter = counter + 1
    
    print(objs)

    handleNotify(objs)
    
    return jsonify({ 'responseCode': 200 })


def element2Object(element):
    ctxObj = {}
    for key in element:
	ctxObj[key]=element[key] 
    return ctxObj

def object2Element(ctxObj):
    ctxElement = {}

    for key in ctxObj:
        ctxElement[key]=ctxObj[key]
    return ctxElement

def readContextElements(data):
    print data

    ctxObjects = []
    
    for response in data['contextResponses']:
        if response['statusCode']['code'] == 200:
            ctxObj = element2Object(response['contextElement'])
            ctxObjects.append(ctxObj)    
    return ctxObjects

def handleNotify(contextObjs):
    for ctxObj in contextObjs:
        processInputStreamData(ctxObj)

def processInputStreamData(obj):
    print '===============receive context entity===================='
    print obj
    
    global counter    
    counter = counter + 1

def handleConfig(configurations):  
    global brokerURL
    global num_of_outputs  
    for config in configurations:        
        if config['command'] == 'CONNECT_BROKER':
            brokerURL = config['brokerURL']
        if config['command'] == 'SET_OUTPUTS':
            outputs.append({'id': config['id'], 'type': config['type']})
    
def handleTimer():
    global timer

    # publish the counting result
    entity = {}       
    entity['id'] = "urn:ngsi-ld:result.01"
    entity['type'] = "Result"
    entity['counter'] = counter    
    publishResult(entity)
        
    timer = threading.Timer(10, handleTimer)
    timer.start()

def update(resultCtxObj):
    global brokerURL
    if brokerURL == '':
        return

    ctxElement = object2Element(ctxObj)

    id=ctxObj['id']
    ctxObj.pop("id")
    ctxObj.pop("type")    
    headers = {'Accept' : 'application/json', 'Content-Type' : 'application/json'}
    response = requests.patch(brokerURL + '/ngsi-ld/v1/entities/'+ id +'/attrs', data=json.dumps(updateCtxReq), headers=headers)
    return response.status_code
    
def sendDataToBroker(resultCtxObj):
    response=cretaeRequest(resultCtxObj)
    if response != 409:
	print("Entity already has been created trying for update request....")
        response=update(resultCtxObj)
	if response != 204:
	    print 'failed to update context'
	
def publishResult(result):
    resultCtxObj = {}
    print(result)
    resultCtxObj['id']=result['id']
    resultCtxObj['type']=result['type']
    data={}
    data['type']="Property"
    data['value']=result['counter']
    resultCtxObj['count']=data
    
    sendDataToBroker(resultCtxObj)

def cretaeRequest(ctxObj):
    global brokerURL
    if brokerURL == '':
        return
        
    ctxElement = object2Element(ctxObj)
    

    headers = {'Accept' : 'application/json', 'Content-Type' : 'application/json', 'Link':'<{{link}}>; rel="https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"; type="application/ld+json"'}
    response = requests.post(brokerURL + '/ngsi-ld/v1/entities/', data=json.dumps(updateCtxReq), headers=headers)
    if response.status_code != 201:
        return response.status_code

                             
if __name__ == '__main__':
    handleTimer()    
    
    myport = int(os.environ['myport'])
    
    myCfg = os.environ['adminCfg']
    adminCfg = json.loads(myCfg)
    handleConfig(adminCfg)
    
    app.run(host='0.0.0.0', port=myport)
    
    #timer.cancel()
    