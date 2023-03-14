# Copyright (c) 2022, n ithead@ambibuzz.com and contributors

##  bench execute ampower.ephemera.doctype.checkin_service.checkin

import frappe
import json
from frappe.model.document import Document
from haversine import haversine, Unit

mandatory_field_list = ["location", "employee", "log_type", "time", "face_detected", "face_detection_status", "face_detection_comment"]

# function that accepts latitude and longitude of two points and returns the distance between two points
@frappe.whitelist()
def haversine_distance(current_location, reference_location):
    return haversine(current_location, reference_location)*1000 # return the distance in meters

def api_return(status_code, msg):
    return status_code, msg

# Function to check weather the employee exists or not
def validate_emp(employee):
    result = frappe.get_all('Employee', filters = {"employee":employee}, fields=["employee"])
    # result will be empty when no filter matches in the doctype
    if len(result) > 0:
        return '200'
    else:
        return '403'

# Function to validate the device id     
def validate_location(location):
    try:
        eval(location) # check if the lat, log is comma separated
        return '200'
    except:
        return '403'

# funtion to validate the log type
def validate_log_type(log_type):
    if log_type=='IN' or log_type=='OUT':
        return '200'
    else:
        return '403'
        
# checking madatory field for employee checkin
def mandatory_field_check(json_data, mandatory_field_list = mandatory_field_list):
    missing_fields = []
    for key in mandatory_field_list:
        if key in json_data and json_data.get(key):
            continue
        else:
            print("Key Missing " + key)
            missing_fields.append(key)
    return missing_fields




# Entry Point for mobile application
@frappe.whitelist()
def checkin(employee_checkin_json=None):
    if frappe.request and frappe.request.form:
        employee_checkin_json = frappe.request.form
        
    elif frappe.request and frappe.request.data:
        employee_checkin_json = json.loads(frappe.request.data)
        # mandatory_field_check(employee_checkin_json["data"])
        # return employee_checkin_json
    else:
        employee_checkin_json = {
            "data": {
                    "employee": "HR-EMP-00001",
                    "log_type": "OUT",
                    # "device_id": "35.7194371,74.0718163",
                    "device_id": "15.490930,73.827850",
                    "face_detected": "/files/new_imagee56235",
                    "face_detection_status": 1,
                    "face_detection_comment" : "success"
                }
        }

    # employee_checkin_json = employee_checkin_json.get("data",{})
    # missing_fieldsapi_return = mandatory_field_check(employee_checkin_json)
    
    ## API returns form [RAjat]
    # if len(missing_fields) > 0:
    #     msg = "Fields Missing : "
    #     for element in missing_fields:
    #         msg += element
    #     api_return("417", msg)
    
    # if validate_emp(employee_checkin_json["employee"]) != "200":
    #     api_return("404", "Employee Does not Exists")

    # if validate_location(employee_checkin_json["device_id"]) != "200":
    #     api_return("404", "Location Invalid")

    # if validate_log_type(employee_checkin_json["log_type"]) != "200":
    #     msg = str(employee_checkin_json["log_type"]) + " Log Type is Invalid" 
    #     api_return("404", msg)
    
    ##  Check for the missing feilds
    # if len(missing_fields) > 0:
    #     msg = "Fields Missing : "
    #     for element in missing_fields:
    #         msg += element
    #     return {"417", msg}

    ## Get and validate the employee 
    employee = employee_checkin_json["data"]["employee"]
    if validate_emp(employee) != '200':
        return {"404": "employee does not exist"}


    # Get and validate the device id or current location
    device_id = employee_checkin_json["data"]["device_id"]  
    if validate_location(device_id) != '200':
        return {"404": "Invalid location/device id"}
    current_location = eval(device_id)  # convert device id string to tuple (lat, log)

    # Validate the log type
    log_type = employee_checkin_json["data"]["log_type"]
    if validate_log_type(log_type) != '200':
        return {"404":"Invalid Log Type"}
    
    # Get the employee details from Employee doctype [employee name]
    res_emp = frappe.get_all("Employee", filters = {"employee":employee}, fields = ['*'])
    

    # Get the Location list document (Child table of Checkin configuration), employee is passed as filter
    matched=False
    location_list  = frappe.get_all("Location List", filters = {
        "parent": employee_checkin_json["data"]["employee"],"is_active":1}, 
        fields = ["location", "is_active", "range", "latitudelongitude"])
    is_location_match1 = is_location_match(location_list,device_id)
    matched = is_location_match1.get("flag")
    
    
    # Getting location list from department 
    if res_emp[0].get("department")  and (matched is False or len(location_list)==0):
        location_list  = frappe.get_all("Location List", filters = {
            "parent":res_emp[0].get("department"),"is_active":1}, 
            fields = ["location", "is_active", "range", "latitudelongitude"])
        is_location_match1 = is_location_match(location_list,device_id)
        matched = is_location_match1.get("flag")

    location_comment = is_location_match1.get("location_comment")
    location_status = is_location_match1.get("location_status")
    flag = is_location_match1.get("flag")
    

   
    # Create the checkin doc in frappe
    doc = frappe.new_doc("Employee Checkin")
    doc.employee = employee_checkin_json.get('data').get('employee') # from the incoming JSON
    doc.employee_link = employee_checkin_json.get('data').get('employee') # from the incoming JSON
    doc.employee_name = res_emp[0]["employee_name"] # from Employee Doctype
    doc.log_type = employee_checkin_json.get('data').get('log_type') # from the incomming JSON
    doc.time = employee_checkin_json.get('data').get('time') # Same
    doc.device_id = device_id   # from the incomming JSON
    doc.location_status = location_status # Updated by the code
    doc.location_comment = location_comment # Updated by the code
    doc.face_detected = employee_checkin_json.get('data').get('face_detected') # from the incomming JSON
    doc.face_detection_status = employee_checkin_json.get('data').get('face_detection_status') # # from the incomming JSON
    doc.face_detection_comment = employee_checkin_json.get('data').get('face_detection_comment') # from incomming JSON
    doc.insert()
    return doc


def is_location_match(location_list,device_id,):
    if len(location_list) > 0:
        # Calculate the distance between two locations note that there are various locations in the location list doctype
        for i in range(0, len(location_list)):
            distance = haversine_distance(eval(device_id), eval(location_list[i]['latitudelongitude']))  # Get distance between the two points
            location_list[i]['distance'] = str(int(distance)) + ' meters' # append distance feild in location_list
    
    flag = False
    min = 0
    location_status = 0
    location_comment = ""
    if len(location_list) > 0: 
        for i in range(0, len(location_list)):
            loc_range = [int(s) for s in location_list[i]['range'].split() if s.isdigit()] # get the range from result
            distance = [int(s) for s in location_list[i]['distance'].split() if s.isdigit()] # get the distance from result
            difference = distance[0] - loc_range[0]

            # store the minimum difference of various locations in 'loacation list child table' with current loction
            if min < difference:
                min  = difference
            
            # Check if the any loction in the location list is within range       
            if distance[0]<loc_range[0]:
                print('within range for ',location_list[i]['location'], location_list[i]['latitudelongitude'])
                location_comment = "In-range for "+location_list[i]['location']
                location_status = 1
                flag = True
                break
            
    print('Minimum = ', min)
    print('Flag  = ',flag)

    # When no data is in location list
    print(location_list)
    if len(location_list) == 0:
        location_comment = "No location in Location list "
        location_status = 1
        flag = True 
        # return "200", "Updated without Location List"
    
    if flag==False:
        # location_comment = "Out of range, Difference with the closest location is " + str(min) + " meters" 
        location_comment = "Out of range"
        location_status = 0

    return {
        "flag":flag,
        "location_status":location_status,
        "location_comment":location_comment
    }

