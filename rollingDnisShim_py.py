import json
import logging
import urllib3
import os
# #####################################################
# #######################################################################
# # Created by Doug McNall as a Proof of Concept.
# #######################################################################
#  
# MIT No Attribution
# 
# Copyright 2024 Amazon Web Services
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# #######################################################################
# Initialize logger and set log level
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
# #######################################################################
# # See if the Event is from Connect or API Gateway.
# #######################################################################
    print("+++ Start of LAMBDA Function +++")
    print(">>> Received event:" + json.dumps(event, indent=4, default=str))

    # Coming from Connect or External.
    if 'Details'  in event:
        myEvent = event["Details"]["Parameters"]
    else:
        myEvent = event

    passdata = myEvent['passdata']

    print (">>>>>>> Lambda Passdata  ="+passdata)

    http = urllib3.PoolManager()
    
    myApiGw = os.environ.get('')
    
    print (myApiGw)
    
    # The API gateway from the Cloudformation needs to be added
    # as an environmental variable of apigw
    myUrl = 'https://need-an-api-gateway-variable'

    if os.environ.get('apigw') is None:
        print("API Gateway (apigw) environmental variable is required")
        return {"status":"failed", "reason": "API Gateway (apigw) environmental variable is required"}
    else:        
        myUrl = os.environ.get('apigw')

    myPayload = {   "function":"sendcall",
                        "passdata":passdata
                }

    myPayloadJson = json.dumps(myPayload)

    headers = {'Content-type': 'application/json'}
    response = http.request('POST', myUrl,headers=headers,body=myPayloadJson,encode_multipart=False)

    myResponse = response.data.decode('utf-8')

    print (">>>> Lambda Response Data ")
    print (myResponse)

    retMsg = json.loads(myResponse)

    return retMsg



