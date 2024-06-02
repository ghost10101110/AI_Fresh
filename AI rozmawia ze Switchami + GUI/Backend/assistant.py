import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class NetworkAssistant:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def make_decision(self, user_input, chat_history):
            
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
        {
            "type": "function",
            "function": {
                "name": "configure_devices",
                "description": """
                configure devices
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
                        "configuration_cmd": {
                            "type": "array",
                            "items": {"type:": "string"},
                            "description": """
                                Configuration command to be executed on the 
                                devices. This should be a valid Cisco NX-OS 
                                show command.
                                """,
                        },
                    },
                    "required": ["device_ips", "configuration_cmd"],
                },
            },
        },
    ]

        content = f"""
        I’m an AI assistant for network engineers, designed to make your job easier by interacting directly with network devices through specific function calls. Here’s how I operate:

        Function Specificity: Use each function exactly for its intended purpose. For example, use get_info_from_devices to retrieve status and information with "show" commands. This function is not for configuring or changing device settings.

        Information Completeness: Don't guess if you don’t have enough info to execute a function. If you need a switch name or IP address and it’s missing, ask for it: "Please provide the switch name or IP address to proceed." Use the switch name as the primary identifier if it's provided.

        Action Restrictions: If there's no dedicated function for a requested action, or if it's beyond my capabilities (like configuring a device), explain the limitation politely: "I'm sorry, but configuring devices directly is beyond my current capabilities. My functions are limited to executing 'show' commands to gather information."

        Guidance and Clarity: Be clear about what functions I can perform and what information I need. If a request is incomplete, provide a brief description of the missing details. For example, if asked to log in or check a switch, I'll interpret it as a status query or device check request.

        Adherence to Scope: Stick to what I’m designed to do. Don’t perform functions or provide assistance beyond my scope, no matter the request.

        Additionally, I can log into switches and perform checks or verifications. If you need me to check or verify something, I'll find and execute the right function. When using show commands, I’ll automatically know and use the correct command without asking you which one.

        My goal is to help network engineers be more efficient while ensuring safety, accuracy, and adherence to procedures. If unsure, I’ll seek clarity or more information rather than guessing. If a command isn't specified, I'll suggest one and use it. If I need to comment, I'll keep it brief unless you ask for more detail.
                
        I SHOULD ALWAYS CONSIDER CHAT HISTORY:'''
        {chat_history}
        '''
        
        FUNCTION CALLING RULES:'''
        If user requests to check someting on the switches it means you should use get_info_from_devices
        If user request to configure somwthing on the switches it means you should use configure_devices
        '''
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            tools=tools,
            messages=[
                {"role": "system", "content": content},
                {"role": "user", "content": user_input},
            ],
        )

        ai_response = response.choices[0].message.content
        tool_calls = response.choices[0].message.tool_calls

        if tool_calls:
            function_name = tool_calls[0].function.name
            arguments = json.loads(tool_calls[0].function.arguments)
            arguments["function_name"] = function_name
            arguments["chat_history"] = chat_history
            follow_up_response = self.function_run(user_input, **arguments)
            follow_up_content = follow_up_response.choices[0].message.content
            return follow_up_content
        else:
            return ai_response

    def function_run(self, user_input, **arguments):
        function_map = {
            "get_info_from_devices": self.get_info_from_devices,
            "configure_devices": self.configure_devices,
        }
        function_name = arguments.get("function_name")
        chat_history = arguments.get("chat_history")
        if function_name in function_map:
            func_to_call = function_map[function_name]
            response_from_fc = func_to_call(**arguments)
            system_prompt = f"""I am an AI assistant specializing in Cisco networking. 
            I receive statuses that indicate whether configurations on switches have 
            been successful. I interpret these statuses and respond accordingly. 
            Each status update includes a response code and the type of operation, 
            such as 'cli_conf' for configurations or 'cli_show' for show commands. 
            My responsibility is to interpret these updates and provide a clear, 
            human-like response based on the question, system message, 
            and output status.
                    
                    ALWAYS TAKE UNSER CONSIDERATION CHAT HISTORY:
                    {chat_history}
                    """
            follow_up_query = {
                "model": "gpt-3.5-turbo",
                f"messages": [
                    {"role": "system", "content": system_prompt,},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": str(response_from_fc)},
                ],
            }
            follow_up_response = self.client.chat.completions.create(**follow_up_query)
            return follow_up_response
        else:
            return f"Function {function_name} is not recognized or not implemented."

    def configure_devices(self, **kwargs):
        switchuser = os.getenv("CISCO_USER")
        switchpassword = os.getenv("CISCO_PASSWD")

        device_ips = kwargs.get("device_ips")
        configuration_cmd = kwargs.get("configuration_cmd")
        
        command_string = " ; ".join(configuration_cmd)

        if isinstance(device_ips, list) and device_ips:
            device_ip = device_ips[0]
        elif isinstance(device_ips, str):
            device_ip = device_ips
        else:
            raise ValueError("device_ips must be a list with at least one element or a string.")

        url = f"https://{device_ip}/ins"
        myheaders = {"content-type": "application/json"}

        payload = {
            "ins_api": {
                "version": "1.0",
                "type": "cli_conf",
                "chunk": "0",
                "sid": "1",
                "input": command_string,
                "output_format": "json",
                "rollback": "rollback-on-error"
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
            return response.json()
        else:
            return {
                "error": "Failed to execute command",
                "status_code": response.status_code,
                "details": response.text,
            }

    def get_info_from_devices(self, **kwargs):
        switchuser = os.getenv("CISCO_USER")
        switchpassword = os.getenv("CISCO_PASSWD")

        device_ips = kwargs.get("device_ips")
        show_cmd = kwargs.get("show_cmd")

        if isinstance(device_ips, list) and device_ips:
            device_ip = device_ips[0]
        elif isinstance(device_ips, str):
            device_ip = device_ips
        else:
            raise ValueError("device_ips must be a list with at least one element or a string.")

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
            return response.json()
        else:
            return {
                "error": "Failed to execute command",
                "status_code": response.status_code,
                "details": response.text,
            }

# Example usage
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    assistant = NetworkAssistant(api_key=api_key)
    user_input = "hej, czy mozesz zalogowac sie na switcha: sbx-nxos-mgmt.cisco.com i sprawdzić czy vlan 13 jest skonfigurowany?"
    response = assistant.make_decision(user_input)
    print(response)
