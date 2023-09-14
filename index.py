from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import concurrent.futures
import time
import json
app = Flask(__name__)
import socket
import pandas as pd
# API endpoint information

#Endpoint for Lambda function Warmup
ENDPOINT = "https://klufe6go3b.execute-api.us-east-1.amazonaws.com"
FUNCTION_PATH = "/default/testF1"

#Endpoint for AWS EC2 connection using AWS Lambda
ENDPOINT_AWS="https://80y3ay8lyb.execute-api.us-east-1.amazonaws.com"
FUNCTION_PATH_AWS="/default/AWSEC2"


# Warm-up API end point
@app.route('/warmup', methods=['GET', 'POST'])
def lambda_warmup():
    if request.method == 'POST':
        global ser
        global time_for_warm
        global warmm
        global num_resources
        global cost_warmup
        time_for_warmup=[]
        if request.form['service']=='lambda':
            warmm=[]
            num_resources = int(request.form['resources'])
            ser='lambda'
            print(num_resources)
            def invoke_lambda_function(_):
                try:
                    start = time.time()
                    response = requests.post(ENDPOINT + FUNCTION_PATH)
                    response.raise_for_status()
                    print(f"Invoked Lambda function: {response.status_code}")
                    print("Elapsed Time:", time.time() - start)
                    time_for_warmup.append(time.time() - start)
                    warmm.append(response)
                except Exception as e:
                    print(f"Error invoking Lambda function: {e}")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(invoke_lambda_function, range(num_resources))
            #warmm.append('Lambda warming up initiated.')
            #return render_template('next_page.html', warming_up=True)
            print(time_for_warmup)
            time_for_warm=sum(time_for_warmup)
            print(time_for_warm)
            
            cost_warmup=str((time_for_warm/60)*0.0134)
            
            return {"result": "ok"}
        else:
            num_resources = int(request.form['resources'])
            body=json.dumps({"num_resources":num_resources})
            headers = {'Content-Type': 'application/json'}
            warmm=[]
            ser='ec2'
            print(num_resources)
            def launch_ec2():
                try:
                    start = time.time()
                    response = requests.post(ENDPOINT_AWS + FUNCTION_PATH_AWS,headers=headers, data=body, verify=False)
                    #response.raise_for_status()
                    time.sleep(10)
                    data=response.json()
                    if response.status_code == 200:
                        warmm.append(data)
                    else:
                        return "Error invoking EC2"
                    print("Elapsed Time:", time.time() - start)
                    time_for_warmup.append(time.time() - start)
                    print(f"Invoked EC2")
                except Exception as e:
                    print(f"Error invoking EC2 function: {e}")
            
            print(time_for_warmup)
            launch_ec2()
            time_for_warm=sum(time_for_warmup)
            print(time_for_warm)
            
            cost_warmup=str((time_for_warm/3600)*num_resources*0.012)
            
            return {"result": "ok"}
        
        
    else:
        return render_template('index.html')

# API endpoint for checking whether resources are warmedup or not
@app.route('/resources_ready', methods=['GET', 'POST'])
def resources_ready():
    if request.method == 'GET':
        if ser=="ec2":
            if num_resources==len(warmm[0]):
                print(warmm)
                print(num_resources)
                return jsonify({"warm": True})
            else:
                print(warmm)
                print(num_resources)
                return jsonify({"warm": False})
        else:
            if num_resources==len(warmm):
                print(warmm)
                print(num_resources)
                return jsonify({"warm": True})
            else:
                print(warmm)
                print(num_resources)
                return jsonify({"warm": False})
        
    else:
        return render_template('index.html')

# API endpoint to get warmup cost
@app.route('/get_warmup_cost', methods=['GET', 'POST'])     
def get_warmup_cost():
    if request.method == 'GET':
        return {"billable_time": time_for_warm,"cost":cost_warmup}
    else:
        return render_template('index.html')
        
#API endpoint to get resources endpoints information
@app.route('/get_endpoints', methods=['GET', 'POST'])     
def get_endpoints():
    if request.method == 'GET':
        dns_list=[]
        r={}
        if ser=="ec2":
            for i in warmm:
                for j in i:
                    if 'PublicDnsName' in j:
                        dns_list.append("http://"+str(j['PublicDnsName'])+"/")
            for i in range(len(dns_list)):
                r[f"resource {i}"] = dns_list[i]
            return r
        else:
            x="There are no endpoints for Lambda."
            return x
 
#API to analyse 
@app.route('/analyse', methods=['GET', 'POST'])
def analyse():
    if request.method == 'POST':
        global h,d,t,p
        global sorted_responses
        global sum_of_pl
        h=int(request.form['history'])
        d=int(request.form['shots'])
        t=str(request.form['bs'])
        p=int(request.form['profit_loss'])
        body=json.dumps({"minhistory":h, "shots":d , "bs": t, "profit_loss_days":p})
        da={"minhistory":h, "shots":d , "bs": t, "profit_loss":p}
        global responses
        global time_for_analsys
        global cost_analsys
        global val_95
        global val_99
        global avg_95
        global avg_99
        global total_billable_time
        global total_cost
        responses=[]
        if ser=="lambda":
            start = time.time()
            def invoke_lambda_function(_):
                try:
                    response = requests.post(ENDPOINT + FUNCTION_PATH,data=body, verify=False)
                    print(response.json())
                    return response.json()
                except Exception as e:
                    print(f"Error invoking Lambda function: {e}")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                responses = list(executor.map(invoke_lambda_function, range(num_resources)))
            time_for_analsys=time.time()-start
            cost_analsys=str((time_for_analsys/60)*0.0134)
            render_template('next_page.html')
            
            
        if ser=="ec2":
            url=[]
            ips=[]
            start = time.time()
            headers = {'Content-Type': 'application/json'}
            for i in warmm:
                for j in i:
                    if 'PublicIpAddress' in j:
                        ips.append(j['PublicIpAddress'])
                        url.append("http://"+j['PublicIpAddress']+":80")
            print(url)
            for i in ips:
                if checkconnection(i)==1:
                    print("connected")
                    time.sleep(10)
                    connect="http://"+i+":80"
                    response = requests.post(connect, headers=headers, json=da, verify=False, timeout=50)
                    responses.append(response.json())
            time_for_analsys=time.time()-start
            cost_analsys=str((time_for_analsys/3600)*num_resources*0.012)
            render_template('next_page.html')
            
        #sorting responses for  get_sig_vars9599 & get_sig_profit_loss api endpoints
        data_list = [response["data"] for response in responses]
        flattened_data = [item for sublist in data_list for item in sublist]
        sorted_responses = sorted(flattened_data, key=lambda x: x['date'])
        
        print(sorted_responses)
        
        val_95=[]
        val_99=[]
        
        
        # Calculating Averages for the avg api endpoints 
        for j in flattened_data:
            val_95.append(j["95%"])
            val_99.append(j["99%"])
        avg_95=sum(val_95)/len(val_95)
        avg_99=sum(val_99)/len(val_99)
        
        # Calculating total profit
        pl_values=[]
        for j in flattened_data:
            pl_values.append(j["Profit/Loss"])
        sum_of_pl=sum(pl_values)
        
        
        #Calculating total costs
        total_billable_time=time_for_warm+time_for_analsys
        cw=cost_warmup
        total_cost=float(cw)+float(cost_analsys)
        
        #Storing Audit Data to data.json via AWS Lambda function
        headers = {'Content-Type': 'application/json'}
        data={"ser": ser, "num_resources": num_resources, "h": h, "d": d,"t": t,"p": p,"sum_of_pl": sum_of_pl,"avg_95": avg_95,"avg_99": avg_99,"total_billable_time": total_billable_time,"total_cost": total_cost}
        body=json.dumps(data)
        response=requests.post("https://l7abtptey4.execute-api.us-east-1.amazonaws.com/default/new_function", headers=headers, data=body, verify=False)
        
        
        return {"result": "ok"}
        
    else:
        return render_template('next_page.html')

#Function for checking EC2 connection         
def checkconnection(ip):
    retries = 10
    retry_delay=10
    retry_count = 0
    while retry_count <= retries:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(10)
        result = sock.connect_ex((ip,80))
        if result == 0:
            print ("Instance is UP & accessible on port 80")
            return 1
        else:
            print ("instance is still down retrying . . . ")
            return (checkconnection(ip))


#API endpoint for getting first 20 values for var95 & var99 on the basis of date 
@app.route('/get_sig_vars9599', methods=['GET', 'POST'])
def get_sig_vars9599():
    if request.method == 'GET':
        if sorted_responses is None:
            return "Data has been reset, please run the analysis again."
        
            # Select the first 20 dictionaries
        first_20_by_date = sorted_responses[:20]
        
        response_data = {"var95": [], "var99": []}

        for i in first_20_by_date:
            response_data["var95"].append(i["95%"])
            response_data["var99"].append(i["99%"])

        return response_data
        
#API endpoint for average values for var95 & var99          
@app.route('/get_avg_vars9599', methods=['GET', 'POST'])     
def get_avg_vars9599():
    if request.method == 'GET':
        if avg_95 is None and avg_99 is None:
            return "Data has been reset, please run the analysis again."
        return {"var95": avg_95 , "var99": avg_99}
    else:
        return render_template('index.html')
        
#API endpoint for getting last 20 values for Profit/Loss on the basis of date
@app.route('/get_sig_profit_loss', methods=['GET', 'POST'])     
def get_sig_profit_loss():
    if request.method == 'GET':
        if sorted_responses is None:
            return "Data has been reset, please run the analysis again."
        response_data = {"profit_loss": []}
        last_20_by_date=sorted_responses[-20:]
        for i in last_20_by_date:
            response_data["profit_loss"].append(i["Profit/Loss"])
        return response_data
    else:
        render_template('index.html')

#API endpoint for getting total profit        
@app.route('/get_tot_profit_loss', methods=['GET', 'POST'])
def get_tot_profit_loss():
    if request.method == 'GET':
        if sum_of_pl is None:
            return "Data has been reset, please run the analysis again."
        return {"profit_loss": sum_of_pl}
    else:
        return render_template('index.html')

#API endpoint for getting a chart based on the responses  
@app.route('/get_chart_url', methods=['GET', 'POST'])
def get_chart_url():
    if request.method == 'GET':
        var95 = []
        var99 = []
        dates=[]
        global chart
        if responses is None:
            return "Data has been reset, please run the analysis again."
        data_list = [response["data"] for response in responses]
        flattened_data = [item for sublist in data_list for item in sublist]
        for j in flattened_data:
            var95.append(j["95%"])
            var99.append(j["99%"])
            dates.append(j["date"])
        var95_avg = sum(var95) / len(var95)
        var99_avg = sum(var99) / len(var99)

        var95_avgd = [var95_avg] * len(var95)
        var99_avgd = [var99_avg] * len(var99)
		
        note = list(zip(dates, var95_avgd, var99_avgd))
		
        str_d = '|'.join(dates)
        str_95 = ','.join([str(i) for i in var95])
        str_avg95 = ','.join([str(var95_avg) for i in range(len(dates))])
        str_99 = ','.join([str(i) for i in var99])
        str_avg99 = ','.join([str(var99_avg) for i in range(len(dates))])
        labels = "95%RiskValue|99%RiskValue|Average95%|Average99%"
		
        chart = f"https://image-charts.com/chart?cht=lc&chs=999x499&chd=a:{str_95}|{str_99}|{str_avg95}|{str_avg99}&chxt=x,y&chdl={labels}&chxl=0:|{str_d}&chxs=0,min90&chco=1984C5,C23728,A7D5ED,E1A692&chls=3|3|3,5,3|3,5,3"
        
        return {"url":chart}

 
#API endpoint to get total billable time and cost
@app.route('/get_time_cost', methods=['GET', 'POST'])
def get_time_cost():
    if request.method == 'GET':
        if total_billable_time is not None and total_cost is not None:
            return {"time": total_billable_time, "cost": total_cost}
        else:
            return "Data has been reset, please run the analysis again."
    else:
        return render_template('index.html')    

#API endpoint for getting Audit data   
@app.route('/get_audit', methods=['GET', 'POST'])
def get_audit():
    
    if request.method == 'GET':
        global r_audit
        res_get=requests.post("https://1mf62k117b.execute-api.us-east-1.amazonaws.com/default/testfunction")
        r_audit=res_get.json()
        print(r_audit)
        return r_audit
    else:
        return render_template('index.html')

#API endpoint for resetting the stored values            
@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'GET':
        global ser,time_for_warm,warmm,num_resources,h,d,t,p,sum_of_pl,avg_95,avg_99,total_billable_time,total_cost,cost_warmup,time_for_analsys,sorted_responses,responses,cost_analsys,r_audit
        ser=None
        time_for_warm=None
        warmm=[]
        num_resources=None
        h=None
        d=None
        t=None
        p=None
        sum_of_pl=None
        avg_95=None
        avg_99=None
        total_billable_time=None
        total_cost=None
        cost_warmup=None
        sorted_responses=None
        responses=None
        time_for_analsys=None
        cost_analsys=None
        r_audit=None
        return {"result": "ok"}
    else:
        return render_template('index.html')    

#API endpoint for terminating all the running resources
@app.route('/terminate', methods=['GET', 'POST'])
def terminate():
    if request.method == 'GET':
        global terminated
        headers = {'Content-Type': 'application/json'}
        instances_running=[]
        print(warmm)
        if ser=='ec2':
            for i in warmm:
                for j in i:
                    if 'InstanceId' in j:
                        instances_running.append(j['InstanceId'])
                    else:
                        return {"terminated": "true"}
        if ser=='lambda':
            terminated="ok"
            return {"result":"ok"}
        instances_running=str(instances_running)
        body=json.dumps({"instances":instances_running})
        print(instances_running)
        print(body)
        response=requests.post("https://yqmngudaui.execute-api.us-east-1.amazonaws.com/default/terminateFunction", headers=headers, data=body, verify=False)
        r=response.json()
        if "ResponseMetadata" in r:
            terminated="ok"
            return {"result":"ok"}
        
    else:
        return render_template('index.html')    

#API endpoint for checking the resources has been terminated or not        
@app.route('/resources_terminated', methods=['GET', 'POST'])
def resources_terminated():
    if request.method == 'GET':
        if terminated=="ok":
            return {"terminated": "true"}
        else:
            return {"terminated": "false"}
    else:
        return render_template('index.html')

#API endpoint to redirecting to the webpage        
@app.route('/results', methods=['GET', 'POST'])
def results():
    if request.method == 'GET':
        return render_template('page3.html')
    else:
        return render_template('index.html')
        
#API endpoint to redirecting to the webpage  
@app.route('/next', methods=['GET', 'POST'])
def next():
    if request.method == 'GET':
        return render_template('next_page.html')
    else:
        return render_template('index.html')
        
        
#API endpoint to redirecting to the webpage  
@app.route('/disp', methods=['GET', 'POST'])
def disp():
    if request.method == 'GET':
        if chart is None: 
            return "Data has been reset, please run the analysis again"
        else:
            print(chart)
            return render_template('chart_template.html', chart_url=chart)
    else:
        return render_template('index.html')
        
@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    app.run()


