import json
import logging
from datetime import datetime, timedelta
from  dateutil import parser
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr
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
#
# #######################################################################
# #######################################################################
# # See if the Event is from Connect or API Gateway.
# #######################################################################
# Initialize logger and set log level
logger = logging.getLogger()
logger.setLevel(logging.INFO)
  
dynamodb = boto3.resource('dynamodb') # may require parameters if not using default AWS environment vars

g_retryCount = 0;

def lambda_handler(event, context):
# #######################################################################
# # See if the Event is from Connect or API Gateway.
# #######################################################################
  print("+++ Start of LAMBDA Function +++")
  print(">>> Received event:" + json.dumps(event, indent=4))
  
  # Coming from Connect or External.
  if 'Details'  in event:
    myEvent = event["Details"]["Parameters"]
  else:
    myEvent = event
  
# Start assumming a failure then modify if found.
#    retVal = {'status': 'success','retcode':retStatus,'retmessage':retMsg}
#    print ("Return Value = "+json.dumps(retVal))
  
# Check for what type of function are we doing
  funcType = myEvent['function']
  passData = ''
  retVal = {'status':'failed', 'reason':'Valid functions are getcall and sendcall'}
  
  myEnviron = "development"
  
  # Set the pool of numbers.
  if 'environ' in myEvent:
    myEnviron = myEvent['environ']
  
  if funcType.lower() == 'sendcall':
  # Requires data and and returns a DNIS
  # If out of dnis, returns 0
    # passdata is key words seperated by | ex: ani|+12345678901|valid|true
    passData = myEvent['passdata']
    retVal = sendData(passData,myEnviron)
    
  if funcType.lower() == 'getcall':
  # Requires a DNIS and returns data
    passDNIS = myEvent['dnis']
    # Adding leading +, if not present.
    if  passDNIS[0] != '+':
      passDNIS = "+"+passDNIS
      
    retVal = getData(passDNIS)
  
  if funcType.lower() == 'clear':
    retVal = clearExpired(myEnviron)
    
  print(">>> retVal event ="+json.dumps(retVal, indent=4))
  
  return retVal
  
def sendData(pData,myTarget):
# #######################################################################
# # Input: Call Data to save and target environment.
# # Return: Number used for DNIS translation route.
# # Note: If no number available, returns failed.
# #######################################################################
  
  print ("Sending Data >>>> ")
  
  global g_retryCount
  
  myTable = dynamodb.Table('rollingDnisTable')

  now = datetime.now()
  dtExpire =now + timedelta(minutes=2) # Set expire 2 minutes from now
  
  # Retrieve the first not in-use number.
  myKey = Key('inuse').eq('false');
  myEnviron = Key('target').eq(myTarget);
  retFields='dnis,target,inuse,expiredatetime'
  
  sDnis = ''
  sTarget = ''
  
  # Default Status
  retVal = {'status':'failed', 'reason':'No Numbers Available'}
  
  gotDnis = 'false'
  
  resID = str(uuid.uuid4()) # Unique ID to validate a record lock.
  
  # Loop through the available numbers to grab the first one.
  while (gotDnis=='false'):
    # Grab the first available number.
    response = myTable.scan(
      FilterExpression=myKey & myEnviron,
      ProjectionExpression=retFields
      )
    print (">>>> Returned Data ="+json.dumps(response, indent=4, sort_keys=True, default=str))
  
    if response["Count"] > 0: # We have a record.
      print (">>>>> DynamoDB JSON ="+json.dumps(response["Items"][0], indent=4, sort_keys=True, default=str))
      sDnis = response["Items"][0]["dnis"]
      sTarget = response["Items"][0]["target"]
      
      # Update the number with data and reserve it.
      routeRec = {'dnis':sDnis,'passdata':pData,'inuse':'true','target':sTarget,'reserveid':resID,'expiredatetime': dtExpire.strftime("%m/%d/%Y %H:%M:%S")}
  
      print ("Updating Routing info to "+json.dumps(routeRec, indent=4, sort_keys=True, default=str))
      updResponse = myTable.put_item(Item=routeRec)
      print ("Put Response >>>  ")
      print (updResponse)
      print ("<<<")
      
      # Retrieve the number and make sure it has this reserve number.
      myKey = Key('dnis').eq(sDnis);
      retFields='ani,target,inuse,reserveid,expiredatetime'
    
      sTarget= ''
      sInUse= ''
      
      responseChk = myTable.scan(
        FilterExpression=myKey,
        ProjectionExpression=retFields
        )
  
      if responseChk["Count"] > 0: # We have a number. Should be 0 or 1.
        print (">>>>> DynamoDB JSON ="+json.dumps(responseChk["Items"][0], indent=4, sort_keys=True, default=str))
  
        chkResID = responseChk["Items"][0]["reserveid"] # Grab the returned response for comparision.
        if chkResID == resID: # We have a match!
          gotDnis = 'true' # Exit loop. GUID's match. If this fails, keep looping.
          retVal = {'status':'Success', 'dnis':sDnis}
  
    else: # No numbers available
      gotDnis = 'true' # Exit loop. No more trys.
      retVal = {'status':'failed', 'reason':'No Numbers Available'}

      # Attempt to clear numbers that did not get marked ready and try 1 more time
      clearExpired(myTarget)
      if g_retryCount < 2: # first attempt. Try ag%ain
        retVal = sendData(pData,myTarget)
  
  return retVal
  
def getData(pDNIS):
# #######################################################################
# # Input: DNIS to retrieve data from.
# # Return: Data in DNIS
# #######################################################################
  print (">>>>>>> getData ="+pDNIS)
  
  myTable = dynamodb.Table('rollingDnisTable')
  
  myKey = Key('dnis').eq(pDNIS);
  retFields='dnis,passdata,target,inuse,reserveid'
  
  passData =  ""
  sTarget= ''
  sInUse= ''
  sResID = ''
  
  response = myTable.scan(
    FilterExpression=myKey,
    ProjectionExpression=retFields
    )
  print (">>>> Returned Parameter Data ="+json.dumps(response, indent=4, sort_keys=True, default=str))
    
  # default message
  retMsg = {"status":"Failed","message":"DNIS not present."}
  
  if response["Count"] > 0: # We have passed data. Should be 0 for no data or 1 for data.
    print (">>>>> DynamoDB JSON ="+json.dumps(response["Items"][0], indent=4, sort_keys=True, default=str))
    passData = response["Items"][0]["passdata"]
    sTarget = response["Items"][0]["target"]
    sInUse = response["Items"][0]["inuse"]
    sResID = response["Items"][0]["reserveid"]
    
    passArray = Convert(passData.split('|') ) # This will split the data out of passdata and add as a named value pair.
    tmpData = {"status":"Success","inuse":sInUse,"target":sTarget,"reserveid":sResID}
    
    retMsg = tmpData|passArray
    
    # Release the number by setting the inuse to false.
    routeRec = {'dnis':pDNIS,'passdata':passData,'inuse':'false','target':sTarget,"reserveid":sResID}
    print ("Updating Routing info to "+json.dumps(routeRec, indent=4, sort_keys=True, default=str))
    updResponse = myTable.put_item(Item=routeRec)
    print ("Put Response >>>  ")
    print (updResponse)
    print ("<<<")
      
  return retMsg
  
def clearExpired(myTarget):
# #######################################################################
# # Input:Nothing
# # Return:Nothing
# # Note: Clear all expired number (set inuse = false)
# #######################################################################
  
  print ("clearExpired Data >>>> ")
  
  myTable = dynamodb.Table('rollingDnisTable')

  global g_retryCount
  
  now = datetime.now()

  # Retrieve the in use numbers
  myKey = Key('inuse').eq('true');
  myEnviron = Key('target').eq(myTarget);
  retFields='dnis,target,inuse,expiredatetime'
  
  sDnis = ''
  sTarget = ''
  
  # Default Status
  retVal = {'status':'success', 'reason':'Numbers were released.'}
  
  # Grab the first available number.
  response = myTable.scan(
    FilterExpression=myKey & myEnviron,
    ProjectionExpression=retFields
    )

  if response["Count"] > 0: # We have a record.
    myNumbers = response["Items"]
    g_retryCount += 1 # Update global retry so we only do this one time.
    
    # go throuh each in-use number and see if they are ready for release.
    for myItem in myNumbers:

      myDtExpire = parser.parse(myItem["expiredatetime"]) # Convert to a datetime field

      if now > myDtExpire: # Has gone past the expired time
        sDnis = myItem["dnis"]
        sTarget = myItem["target"]
  
        # Remove the reservation and data from the number.
        routeRec = {'dnis':sDnis,'passdata':'','inuse':'false','target':sTarget,'reserveid':'','expiredatetime': myDtExpire.strftime("%m/%d/%Y %H:%M:%S")}
  
        print ("Updating reservation info to "+json.dumps(routeRec, indent=4, sort_keys=True, default = str))
        updResponse = myTable.put_item(Item=routeRec)
        print ("Put Response >>>  ")
        print (updResponse)
        print ("<<<")
  else: # No numbers available
    gotDnis = 'true' # Exit loop. No more trys.
    retVal = {'status':'failed', 'reason':'No Numbers To Update'}
  
  return retVal
  
def Convert(lst):
# #######################################################################
# # Input: A list of key, value pairs
# # Return: a Dictionary of the pairs.
# #######################################################################
  res_dct = {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}
  return res_dct
