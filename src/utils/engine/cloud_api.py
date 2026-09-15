import os
import time
import json
import requests


def login_api():
        attempts = 0
        while attempts < 5:
            try:
                status = False
                session_key = ''
                access_token = ''
                 # Prepare data and headers for token request
                token_url = "https://auth-staging.netradyne.com/authserver/api/v1/oauth/token"
                token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
                token_data = {
                    "client_id": "idms",
                    "grant_type": "password",
                    "username": "device-test-automation",
                    "password": "devicetestautomation"
                }
                token_response = requests.post(token_url, headers=token_headers, data=token_data)
                login_response = token_response.json()
                print(login_response)
                if 'access_token' in login_response:
                    access_token = login_response["access_token"]
                    session_url = "https://auth-staging.netradyne.com/authserver/api/v1/session"
                    session_headers = {"Authorization": f"bearer {access_token}"}
                    session_response1 = requests.post(session_url, headers=session_headers)
                    session_response = session_response1.json()
                else:
                    raise Exception("Access token is not generated")
                if 'session' in session_response and 'session_id' in session_response['session']:
                    session_key = session_response['session']['session_id']
                    if session_key != '':
                        status=True
                        return session_key,status,access_token
                    else:
                        raise Exception("Session key is empty")
                else:
                    raise Exception("Session key is not generated")
            except Exception as e:
                attempts += 1
                print(f"Error in login_api: {e}. Attempt: {attempts}")
                time.sleep(2 ** attempts)

        return None, False, None # default values after failed attempts

def aws_ping_command(user_id, ping_command):
    """
    This function sends a ping command to the AWS API for a specific device.
    It logs in to obtain a session key and access token, then constructs and sends
    the ping request. The function returns the test status and response status.
    Args:
        user_id (str): The user ID to include in the ping request.
        ping_command (str): The ping command to send (e.g., "reboot-phone").
    Returns:
        tuple: A tuple containing the test status ("Pass" or "Fail") and a boolean
               indicating whether the ping command was successful.
    """
    test_status = "Pass"
    response = ''
    response_status = False
    try:
        session_key, status, access_token = login_api()
        if status:
            device_id = os.getenv("DEVICE_ID", "00000000000")
            url = f"https://idms-staging.netradyne.com/restserver/api/v1/devices/{device_id}/ping"
            headers = {
                "session-key": session_key,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            data = {
                "deviceId": device_id,
                "userId": user_id,
                "commands": [ping_command]
            }
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response_content = response.json()
            data = response_content.get("data")
            if response.status_code == 200 and data and data.get("status") == 0:
                response_status = True
            else:
                raise Exception(f"Ping {ping_command} api call response is not received")
        else:
            raise Exception("session key is not generated")
    except Exception as e:
        print(f"Error in aws ping api: {e}")
        test_status = "Fail"
    finally:
        return test_status, response_status
