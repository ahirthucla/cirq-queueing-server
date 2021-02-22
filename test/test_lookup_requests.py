import requests
import sys

root = sys.argv[1]

print(requests.get(root + "lookup", params={"job_id":sys.argv[2:]}).text) 
print(requests.get(root + "lookup", params={"student_id":sys.argv[2:]}).text) 
