# Copyright (c) 2022, Ambibuzz Technologies LLP  and contributors

import frappe
import json
from haversine import haversine


# Entry Point for mobile application
@frappe.whitelist()
def checkin(employee_checkin_json = None):

    # Checking the valid request method
    if frappe.request and frappe.request.method == 'POST' and frappe.request.data:
        employee_checkin_json = json.loads(frappe.request.data)
    else:
        return {'404': 'Method not Allowed or Invalid Request'}

    # Get and validate the employee
    employee = employee_checkin_json['data']['employee']
    # Get the employee details from Employee doctype [employee name]
    res_emp = validate_emp(employee)
    if res_emp is None:
        return {'404': 'employee does not exist'}
        
    # Get and validate the device id or current location
    # convert device id string to tuple (lat, log)
    device_id = validate_location(employee_checkin_json['data']['device_id'])
    if device_id is None:
        return {'404': 'Invalid location/device id'}

    # Validate the log type
    log_type = employee_checkin_json['data']['log_type']
    if validate_log_type(log_type) is None:
        return {'404': 'Invalid Log Type'}

    # Get the Location list from Employee
    matched = False
    employee_location_list = frappe.get_all('Location List', filters={'parent': employee_checkin_json['data']['employee'], 'is_active': 1}, fields=['location', 'is_active', 'range' , 'latitudelongitude'])

    # Get the Location list from Department
    department_location_list = []
    if res_emp.get('department'):
        department_location_list = frappe.get_all('Location List', filters={'parent': res_emp.get('department'), 'is_active': 1}, fields=['location', 'is_active', 'range', 'latitudelongitude'])

    # Concat the employee location and department location
    location_list = employee_location_list + department_location_list

    # checking location matched or not
    is_location_matched = is_location_match(location_list, device_id)
    location_comment = is_location_matched.get('location_comment')
    location_status = is_location_matched.get('location_status')

    # Create the checkin doc in frappe
    doc = frappe.new_doc('Employee Checkin')

    # get employee data employee checkin
    doc.employee = employee_checkin_json.get('data').get('employee')
    doc.employee_link = employee_checkin_json.get('data').get('employee')

    # get employee name
    doc.employee_name = res_emp['employee_name']
    doc.log_type = employee_checkin_json.get('data').get('log_type')
    doc.time = employee_checkin_json.get('data').get('time')
    doc.device_id = str(device_id)

    # Updated by the code
    doc.location_status = location_status
    doc.location_comment = location_comment
    doc.face_detected = employee_checkin_json.get('data').get('face_detected')
    doc.face_detection_status = employee_checkin_json.get('data').get('face_detection_status')
    doc.face_detection_comment = employee_checkin_json.get('data').get('face_detection_comment')
    doc.insert()
    return doc

# function that accepts latitude and longitude of two points and returns the distance between two points
def measure_distance(current_location, reference_location):
    # return the distance in meters
    return haversine(current_location, reference_location) * 1000

# Function to check whether the employee exists or not
def validate_emp(employee):
    # if employee found in db return employee id or null
    res_emp = frappe.get_value('Employee', {'status': "Active" , "employee": employee } , ['department','employee_name'])
    if res_emp is None:
        return None
    return {'department': res_emp[0], 'employee_name': res_emp[1]}

# Function to validate the device id
def validate_location(location):
    location_split = location.split(",") # check if the lat, log is comma separated
    if len(location_split) == 2:
        return (float(location_split[0]),float(location_split[1]))   # convert string to float 
    else:
        return None

# funtion to validate the log type
def validate_log_type(log_type):
    return (log_type if log_type == 'IN' or log_type == 'OUT' else None)

def is_location_match(location_list, device_id):
    flag = False
    closest_dis = 0
    location_status = 0
    
    location_comment = ''
    if location_list:
        # Calculate the distance between two locations note that there are various locations in the location list doctype
        for location in location_list:
            latlong_location = validate_location(location.get('latitudelongitude'))
            if latlong_location is None:
                continue
            # Get distance between the two points
            distance = measure_distance(device_id, latlong_location)
            loc_range = int(location.get('range'))
            difference = distance - loc_range
            # Storing the closet location difference
            if closest_dis < difference:
                closest_dis = difference
            if distance < loc_range:
                location_comment = 'In-range for ' + location.get('location')
                location_status = 1
                flag = True
                break
    else:
        # When no data is in location list
        location_comment = 'No location in Location list '
        location_status = 1
        flag = True

    # When Location is not matched
    if flag is False:
        location_comment = 'Out of range, Difference with the closest location is ' + str(closest_dis) + ' meters'
        location_status = 0
    return {'location_status': location_status, 'location_comment': location_comment}
