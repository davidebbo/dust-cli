import json
import os
import requests
import readline
from dotenv import load_dotenv

load_dotenv()

dust_token = os.getenv("DUST_TOKEN")
wld = os.getenv("WLD")
space_id = os.getenv("SPACE_ID")
dsId = os.getenv("DSID")
dust_url = os.getenv("DUST_URL")

conversationId = None


def get_auth_headers():
    return {
        "Authorization": f"Bearer {dust_token}",
        "Content-Type": "application/json",
    }


def upload_file(file_path, file_name):
    # Read the file content
    with open(file_path, "r") as file:
        file_content = file.read()

    url = f"{dust_url}/api/v1/w/{wld}/spaces/{space_id}/data_sources/{dsId}/documents/{file_name}"
    headers = get_auth_headers()
    data = {
        "title": file_name,
        "mime_type": "text/plain",
        "text": file_content,
        "source_url": f"https://www.archives.gov/files/research/jfk/releases/2025/0318/{file_name}.pdf",
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        print(f"Successfully uploaded {file_name}")
    except requests.exceptions.RequestException as e:
        print(f"Error uploading {file_name}: {e}")


def list_agents():
    url = f"{dust_url}/api/v1/w/{wld}/assistant/agent_configurations"
    headers = get_auth_headers()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        agents = response.json()
        print("Available agents:")
        for agent in agents["agentConfigurations"]:
            print(f"{agent['sId']}: {agent['name']}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching agents: {e}")


def get_agent_details(agent_id):
    url = f"{dust_url}/api/v1/w/{wld}/assistant/agent_configurations/{agent_id}"
    headers = get_auth_headers()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        agent_details = response.json()
        print(f"Details for agent {agent_id}:")
        # Assuming the response JSON is the agent configuration object itself
        # You might want to pretty-print it or extract specific fields
        import json

        print(json.dumps(agent_details, indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for agent {agent_id}: {e}")


def create_new_conversation(agent_id, user_prompt):
    global conversationId
    url = f"{dust_url}/api/v1/w/{wld}/assistant/conversations"
    headers = get_auth_headers()
    data = {
        "message": {
            "content": user_prompt,
            "mentions": [{"configurationId": agent_id}],
            "context": {
                "username": "dust-cli-user",  # Or any other identifier
                "timezone": "Europe/Paris",  # Or dynamically get timezone
            },
        },
        "blocking": True,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()

        agent_reply = None
        if response_data.get("conversation") and response_data["conversation"].get(
            "content"
        ):
            for message_group in response_data["conversation"]["content"]:
                for message in message_group:
                    if message.get("type") == "agent_message" and "content" in message:
                        agent_reply = message["content"]
                        break
                if agent_reply:
                    break

        if agent_reply:
            print(f"Agent ({agent_id}): {agent_reply}")
            conversationId = response_data["conversation"]["sId"]
        else:
            print("No agent reply found in the response.")
            # print("Full response for debugging:")
            # import json
            # print(json.dumps(response_data, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"Error asking agent {agent_id}: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")
    except json.JSONDecodeError:
        print("Error decoding JSON response from server.")


def add_to_conversation(agent_id, user_prompt):
    global conversationId
    url = f"{dust_url}/api/v1/w/{wld}/assistant/conversations/{conversationId}/messages"
    headers = get_auth_headers()
    data = {
        "content": user_prompt,
        "mentions": [{"configurationId": agent_id}],
        "context": {
            "username": "dust-cli-user",  # Or any other identifier
            "timezone": "Europe/Paris",  # Or dynamically get timezone
        },
        "blocking": True,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()

        agent_reply = None
        if response_data.get("agentMessages"):
            for message in response_data["agentMessages"]:
                if message.get("type") == "agent_message" and "content" in message:
                    agent_reply = message["content"]
                    break
                if agent_reply:
                    break

        if agent_reply:
            print(f"Agent ({agent_id}): {agent_reply}")
        else:
            print("No agent reply found in the response.")
            # print("Full response for debugging:")
            # import json
            # print(json.dumps(response_data, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"Error asking agent {agent_id}: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")
    except json.JSONDecodeError:
        print("Error decoding JSON response from server.")


def prompt_agent(agent_id, user_prompt):
    global conversationId
    if conversationId is None:
        create_new_conversation(agent_id, user_prompt)
    else:
        add_to_conversation(agent_id, user_prompt)


def main():
    global conversationId
    while True:
        try:
            command_input = input("dust-cli> ").strip()
            command_parts = command_input.split()
            command = command_parts[0] if command_parts else ""

            # If it starts with @agentname, treat it as an agent command
            if command.startswith("@"):
                agent_id = command[1:]
                user_prompt = " ".join(command_parts[1:])
                create_new_conversation(agent_id, user_prompt)
                continue
            if command.startswith("\\"):
                command = command[1:]  # Remove the leading backslash
                if command == "exit":
                    break
                elif command == "agents":
                    list_agents()
                elif command == "agent":
                    if len(command_parts) > 1:
                        agent_id = command_parts[1]
                        get_agent_details(agent_id)
                    else:
                        print("Usage: get-agent <agent_id>")
                else:
                    print(f"Unknown command: {command}")
            elif command == "":
                continue  # Handle empty input
            else:
                if conversationId is None:
                    print(
                        "No conversation started. Use @agentname <prompt> to start a conversation."
                    )
                else:
                    user_prompt = command_input
                    prompt_agent(agent_id, user_prompt)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:  # Handle Ctrl+D
            print("\nExiting...")
            break


if __name__ == "__main__":
    main()
