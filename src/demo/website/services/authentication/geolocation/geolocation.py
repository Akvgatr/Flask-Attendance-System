import requests
from haversine_distance import haversine

def geo_verification(lat_teacher,lon_teacher,lat_student,lon_student):
    ip_address = requests.get('http://api.ipify.org').text
    response = requests.get(f'http://ip-api.com/json/{ip_address}?/fields=192511').json()

    if not response.get('proxy'):
        distance = haversine(lat_teacher, lon_teacher, lat_student, lon_student)
        if distance <= 15 : print("Within Premises")
        else: raise PermissionError("Not within Premises")