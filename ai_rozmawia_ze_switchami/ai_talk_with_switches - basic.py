import requests
import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def make_decision(user_input):
    """
    This function sends a request to OpenAI to decide which action to take
    based on the user's input, and then calls the appropriate function.
    """
    print(user_input, "\n")

    content = """
    I am an AI assistant for network engineers, designed to facilitate tasks by interfacing directly with network devices via specific function calls. Your core principles are:

    Function Specificity: Each function should be used precisely for its intended purpose. For instance, the function get_info_from_devices should be used to retrieve device status and information using "show" commands. It is not designed for configuring settings or making changes to devices.

    Information Completeness: If the provided information is insufficient to execute a function call accurately, do not proceed with assumptions. For example, if a device name or IP address is missing in a request to gather device information, respond with: "Please provide the switch name or IP address to proceed." However, if the name of the switch is provided, the IP address is not required and the name should be used as the primary identifier.

    Action Restrictions: If a request involves performing an action for which there is no dedicated function or falls outside of your designated capabilities, such as configuring a device, politely decline the request and explain the limitation. For example: "I'm sorry, but configuring devices directly is beyond my current capabilities. My functions are limited to executing 'show' commands to gather information."

    Guidance and Clarity: Always be clear about what functions you can perform and what information you need to carry them out. This includes providing brief descriptions of required parameters or missing details when requests are incomplete. When asked if you can log into or check on a switch, interpret this as a request to use tools designed for status querying or specific device checks.

    Adherence to Scope: Operate strictly within the defined scope of your capabilities. Avoid executing functions or providing assistance that falls outside of this scope, regardless of the request.

    In addition to these principles, I am capable of logging into switches. If you ask me to check, verify if something exists or is configured, it implies that I need to find and execute the appropriate function. When it comes to using show commands, please do not ask me if I can use a specific command. I will always know which command to use and will use it without further questions to the user.

    My objective is to support network engineers by making their tasks more efficient while ensuring safety, accuracy, and adherence to defined procedures. When in doubt, seek clarity or additional information rather than making uninformed decisions. If a command is not provided, I will suggest a command and use it. If I need to comment on something, I will do so in 1-2 sentences unless asked to provide a longer answer.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_info_from_devices",
                "description": """
                Get information from Cisco switches 
                based on show commands
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_ips": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": """
                                List of device IP addresses or switch name. 
                                If there is more than 1 IP Address or 
                                switchname provided, then it should be 
                                provided in the same string and separated 
                                with ; character.
                                """,
                        },
                        "show_cmd": {
                            "type": "string",
                            "description": """
                                The show command to be executed on the 
                                devices. This should be a valid Cisco NX-OS 
                                show command.
                                """,
                        },
                    },
                    "required": ["device_ips", "show_cmd"],
                },
            },
        },
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        tools=tools,
        messages=[
            {"role": "system", "content": content},
            {"role": "user", "content": user_input},
        ],
    )
    ai_response = response.choices[0].message.content
    tool_calls = response.choices[0].message.tool_calls
    # print("ai_response: ", ai_response, "\n")
    # print("tool_calls: ", tool_calls, "\n")

    if tool_calls:
        function_name = tool_calls[0].function.name
        arguments = json.loads(tool_calls[0].function.arguments)
        # print("Arguments:", arguments, "\n")
        arguments["function_name"] = function_name
        print("Arguments:", arguments, "\n")
        function_run(**arguments)

    else:
        print(ai_response)
    
def function_run(**arguments):

    function_map = {
        "get_info_from_devices": get_info_from_devices,
        # Add other functions here
    }
    function_name = arguments.get("function_name")
    if function_name in function_map:
        func_to_call = function_map[function_name]
        response_from_fc = func_to_call(**arguments)
        follow_up_query = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": """
               You are an AI assistant who is expert in cisco networking
               and you are answering based on provided question and answer.
               """,
                },
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": str(response_from_fc)},
            ],
        }
        follow_up_response = client.chat.completions.create(**follow_up_query)
        answer = follow_up_response.choices[0].message.content
        print("\n###############################")
        print("AI assistant's answer: ", answer)
        print("###############################\n")
    else:
        print(f"Function {function_name} is not recognized or not implemented.")
        
def get_info_from_devices(**kwargs):
    switchuser = os.getenv("CISCO_USER")
    switchpassword = os.getenv("CISCO_PASSWD")

    device_ips = kwargs.get("device_ips")
    show_cmd = kwargs.get("show_cmd")

    if isinstance(device_ips, list) and device_ips:
        device_ip = device_ips[0]
    elif isinstance(device_ips, str):
        device_ip = device_ips
    else:
        raise ValueError(
            """
            device_ips must be a list with 
            at least one element or a string.
            """
        )

    # print(device_ip)

    url = f"https://{device_ip}/ins"
    myheaders = {"content-type": "application/json"}

    payload = {
        "ins_api": {
            "version": "1.0",
            "type": "cli_show_ascii",
            "chunk": "0",
            "sid": "1",
            "input": show_cmd,
            "output_format": "json",
        }
    }

    response = requests.post(
        url,
        data=json.dumps(payload),
        headers=myheaders,
        auth=(switchuser, switchpassword),
        verify=False,
    )

    if response.status_code == 200:
        # print(json.dumps(response.json(), indent=4)) #check ourput given by device
        return response.json()
    else:
        print(f"Failed to execute command. Status code: {response.status_code}")
        print(response.text)
        return {
            "error": "Failed to execute command",
            "status_code": response.status_code,
            "details": response.text,
        }

user_input = """
hej, czy mozesz zalogowac sie na switcha: sbx-nxos-mgmt.cisco.com 
i sprawdzić czy vlan 13 jest skonfigurowany?
"""
make_decision(user_input)