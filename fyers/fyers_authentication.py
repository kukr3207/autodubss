from fyers_api import fyersModel
from fyers_api import accessToken
import requests

def fyersOAuth(app_id, app_secret):
    # app_id = "QWB75QC1N0"#"VY1T8XB90T"  #app_id is given by fyers
    # app_secret = "UTCZD84SXH"#"V2FW23GWDW"  #app_secret is given by fyers
    print(app_secret,app_id)
    app_session = accessToken.SessionModel(app_id, app_secret)
    response = app_session.auth()
    print(response)
    authorization_code = response['data']['authorization_code']

    app_session.set_token(authorization_code)
    url = app_session.generate_token()

    return requests.get(url).text

#https://api.fyers.in/api/v2/generate-authcode?client_id=FM0FG083QB-102&redirect_uri=https://squareoffbots.com/fyers/redirect2382&response_type=code&state=sample_state&scope=openid&nonce=sample_nonce
