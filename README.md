# **Transfers from Legacy Platform into Amazon Connect**

 
## **Solution Overview**
Customers migrating from an existing on premises platform or CCaaS solution may need to transfer calls from that legacy platform to Amazon Connect while maintaining context.  Maintaining context when transferring calls between platforms ensures that customers aren’t having to re-enter information that has been captured in the legacy platform.
Maintaining context when transferring calls between platforms reduces customer effort and improves customer experience by not making customers start over when the call is transferred between platforms. 
The recommended pattern to accomplish this with Amazon Connect is a technique known as rolling DNIS where a pool of phone numbers are claimed within Amazon Connect that can be used as a unique identifier for these transfers. Customers can use either direct dial(DID) or toll-free numbers(TFN).  TFN offer carrier resiliency, but do have a slightly higher cost.  DID numbers are tied to a single carrier and limited on the number of concurrent calls they can support. 
The data captured in the legacy platform will be stored in an intermediary data store such as Amazon DynamoDB and then retrieved by AWS Lambda in an Amazon Connect flow.  
This pattern has several advantages in that it works globally, at any scale, and for transfers that occur during interactive voice response(IVR) treatment or agent-initiated transfers.  It can also be used for transfers from Amazon Connect to an external system.
The example here will focus on the IVR transfer but the same concepts apply to agent transfers by having the CTI client of the sending agent query the rolling DNIS solution in the same manner as the IVR example here.
 
![image](img/arch.png)
 
## **How it works:**

1. The customer dials into the legacy platform and interacts with the IVR entering the information required by the IVR to route the call(i.e. customer#, account#, claim#, etc.).
2. When the customer reaches a point in the IVR flow where the call needs to be routed to Amazon Connect the legacy platform calls an AWS Lambda function which checks out a phone number from the pool of available numbers and updates the Amazon DynamoDB table with the associated customer data that has been collected. If no number is available the Lambda function will release any number checked out longer than two minutes.
3. The legacy platform transfers the call to Amazon Connect via the reserved phone number
4. The Amazon Connect flow invokes a Lambda function that performs a look up in the DynamoDB table based on the number dialed and updates the contact attribute(s) with the data returned.  The number then is released back into the pool to be reused.
5. Based on the attribute values defined by the customer data the call is routed to the appropriate queue in Amazon Connect. The call is delivered to an Amazon Connect agent with all of the customer data is available to that agent as contact attributes within their Agent Workspace or custom CCP.  The data can be used to invoke a step-by-step guide or be passed to a third-party application.




 ## **Solution walk through:**  Build a rolling DNIS solution to transfer calls into Amazon Connect

The steps below will guide you through the process of deploying the rolling DNIS solution.  Section 1 will deploy the CloudFormation stack.  Section 2 will will configure Amazon Connect and Section 3 walks you through testing the solution. 


## **Prerequisites**

1. Have an AWS account
2. Have an understanding of Amazon Connect, Lambda, DynamoDB and AWS Identity and Access Management (IAM)
3. Have permissions to deploy CloudFormation stacks, create IAM policies, create CloudWatch logs, create and modify API gateways,  create and modify DynamoDB tables, create and modify Lambda functions, associate Lambda functions with your Connect instance, claim phone numbers in Amazon Connect, create and modify Amazon Connect flows. 
4. Have an existing Amazon Connect instance or create a new one for inbound and outbound calls, and claim two new phone numbers. The Get started with Amazon Connect documentation (the first two steps) provides valuable background knowledge for this process.




## **Section 1:  Deploy AWS CloudFormation template**

1. Clone the repo
2. Unzip the folder on your local machine and note the location.
3.  Navigate to the CloudFormation dashboard within the AWS console and create a CloudFormation stack using the file named “apiGatewayWithLambda.yaml.” 
4. Provide a Stack name
5. Create the stack.
6.  After the stack is successfully launched, copy the following output. It could take a few minutes for the stack to launch the solution. 
    [!Important] **ApiUrl** – This is the API Gateway URL you will use to test the solution. You can find this in the Output tab for the stack.
7. Navigate to AWS Lambda in the AWS console
8. Create a new function
9. Name it rollingDnisShim, change Runtime to Python 3.12 and choose create function.
10. Remove all existing text from the code window
11. Browse to the folder where you extracted the zip file and the ivrTest subfolder
12. Open rollingDnishShim_py.py in your text editor and copy the contents
13. Paste the contents into the code window and click on **Deploy**
14.  Click on configuration and Environment variables.
15. Click edit and Add environment variable.
16. Enter **apigw** as the key and pass the ApiUrl value you copied in step 6. 
17. Save your changes. 

## Section 2:  Configure Amazon Connect

1. Browse to Amazon Connect in the AWS Console
2. Click on the instance you want to use.  If you have not yet created your instance please follow the steps in the  Get started with Amazon Connect documentation.
3. Choose flows on the left hand hand column and scroll down until you find AWS Lambda
4. From the drop down choose **rollingDnis_py** and click **+Add Lambda Function**  you can search in the drop down if you have a large number of Lambda functions
5. Repeat step 4 choosing **rollingDnisShim** to associate our test function.
6. Log into the Amazon Connect instance with an Admin user.
7. Navigate to flows again and choose create flow.
8. Click on the triangle to the right of save and select **Import (beta)** browse to the location where you extracted the cloned repo and into the resource subfolder choosing the rollingDnisReceive.json file and click import.
9. In the flow editor click on the set working queue block and choose the queue you would like calls being transferred from the legacy platform to be placed in and save the change.
    Note: You can also set this dynamically based on contact attributes, but we will be keeping this simple for the purposes of this example.]{header = "Informational"} 
10. Click on the **Invoke AWS Lambda function block** and choose **rollingDnis_py** from the drop down and save the change.
11. Save and Publish your rollingDnisReceive flow.
12. Navigate to flows and choose create flow.
13. Click on the triangle to the right of save and select **Import (beta)** browse to the location where you extracted the cloned repo and into the ivrTest subfolder choosing the rollingDnisSend.json file and click import.
14. Click on the **Invoke AWS Lambda function block** and choose **rollingDnisShim** from the drop down and save the change.
15. Save and Publish your rollingDnisSend flow.
16. Navigate to phone numbers and choose claim a phone number.   
17. Choose voice, Toll free, your country, select a number from the list and associate it to your **rollingDnisSend** flow and save.
> **Note:** *You can choose either TFN or DID numbers for steps 17 and 18.  For this example to keep it simple we are choosing TFN for the number you are going to call and DID for the number being used for the transfer.*

18. Choose claim a number again, choose voice, DID, your country, a specific prefix if you would like, select a number from the list and associate it to your **rollingDnisReceive** flow and save. 
19. In the AWS console navigate to DynamoDB, Tables, and the rollingDNISTable.
20. Choose explore table items.
21. Choose create table item and click on JSON view.
> **Important:** *If **View DynamoDB JSON** is toggled ON → Confirm that it is toggled OFF before proceeding to the next step.*

22. Replace what is in the box with **{ "dnis": "+15555555204", "inuse": "false", "target": "development" }**
23. Update **+15555555204** to the phone number you mapped to the rollingDNISreceive flow in step 18. 
24. Click **create item**.



## Section 3: Testing

1. Place an inbound call to the TF number you claimed in section 2 step 17
2. You will be prompted to enter a five digit account number.  Pick any five digit number
3. You will hear a message in a male voice that the account lookup has failed and you will be transferred.
4. You will then hear a message in a female voice reading back the account number and the reason for the call.
5. This demonstrates that the information entered(account number) is being passed successfully.
6. You can also pull up the contact in Contact Search and validate that the account number and customer phone number are correctly set as contact attributes.  

> **Tip:** *Update the Contact Status filter to include both In Progress and Completed contacts so you see the call in progress.*


## Conclusion

This AWS sample deploys a solution which enables you to transfer data between two contact center platforms using AWS Lambda, Amazon API Gateway, Amazon DynamoDB and Amazon Connect flows making it easier for customers to migrate to Amazon Connect. 
