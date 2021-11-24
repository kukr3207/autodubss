import requests
import json
# import url 

url = 'https://api.fyers.in/api/v1/token'
requestParams = {
"fyers_id":"XT02517",
"password":"Elonmask@2",
"pan_dob":"BSXPT4853L",
"appId":"QWB75QC1N0",
"create_cookie":False}
response = requests.post(url, json = requestParams )
print(response)
# data = json.loads(response.text)["Url"]
# source = data.find("access_token=") + len("access_token=")

# https://api.fyers.in/api/v2/generate-authcode?client_id=1TXIG39I4T-100&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2FfyersAuthenticationCallback&response_type=code&state=None
# http://localhost:8000/fyersAuthenticationCallback?s=ok&code=200&auth_code=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJpYXQiOjE2Mzc3NzEyMzcsImV4cCI6MTYzNzc3MTUzNywibmJmIjoxNjM3NzcwNjM3LCJhdWQiOiJbXCJ4OjBcIiwgXCJ4OjFcIiwgXCJ4OjJcIiwgXCJkOjFcIiwgXCJkOjJcIiwgXCJ4OjFcIiwgXCJ4OjBcIl0iLCJzdWIiOiJhdXRoX2NvZGUiLCJkaXNwbGF5X25hbWUiOiJYVDAyNTE3Iiwibm9uY2UiOiIiLCJhcHBfaWQiOiIxVFhJRzM5STRUIiwidXVpZCI6IjA5YzJjYjIxMmRjODRlMjhhNzViODJmNWZiZjkwZGYxIiwiaXBBZGRyIjoiMTAzLjIzMi4xMzEuMjQ2Iiwic2NvcGUiOiIifQ.e7zv0Xul0Dj71i78CqJ-jdIeUKv3sxT_5eR_0iC-tRo&state=None