import json
import mimetypes
from pathlib import Path
import requests
import readline
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

dust_token = os.getenv("DUST_TOKEN", "")
wld = os.getenv("WLD", "")
dust_url = os.getenv("DUST_URL", "https://dust.tt")

conversationId = None
fileId = None


def get_standard_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {dust_token}",
        "Content-Type": "application/json",
    }


def get_auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {dust_token}"}


def get_file_upload_url(file_path: str, content_type: str) -> Optional[str]:
    path = Path(file_path)
    
    if not path.exists():
        print(f"File not found: {file_path}")
        return None
        
    try:
        file_size = path.stat().st_size
    except OSError as e:
        print(f"Error accessing file {file_path}: {e}")
        return None

    url = f"{dust_url}/api/v1/w/{wld}/files"
    headers = get_standard_headers()
    data = {
        "contentType": content_type,
        "fileName": path.name,
        "fileSize": file_size,
        "useCase": "conversation",
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["file"]["uploadUrl"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting upload URL for {file_path}: {e}")
        return None


def upload_file(file_path: str, upload_url: str, content_type: str) -> Optional[str]:
    path = Path(file_path)
    try:
        with path.open("rb") as file:
            files = {"file": (path.name, file, content_type)}
            headers = get_auth_headers()
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status()
            print(f"File {file_path} uploaded successfully.")
            return response.json()["file"]["sId"]
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file {file_path}: {e}")
        return None


def upload_and_attach_file(file_path: str) -> None:
    # Figure out the content type from the extension
    content_type = mimetypes.guess_type(Path(file_path).name)[0]

    # Get a URL that the file can be uploaded to
    upload_url = get_file_upload_url(file_path, content_type)
    
    # Upload the file to that URL
    global fileId
    fileId = upload_file(file_path, upload_url, content_type)


def list_agents() -> None:
    url = f"{dust_url}/api/v1/w/{wld}/assistant/agent_configurations"
    headers = get_standard_headers()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        agents = response.json()
        print("Available agents:")
        for agent in agents["agentConfigurations"]:
            print(f"{agent['sId']}: {agent['name']}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching agents: {e}")


def get_agent_details(agent_id: str) -> None:
    url = f"{dust_url}/api/v1/w/{wld}/assistant/agent_configurations/{agent_id}"
    headers = get_standard_headers()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        agent_details = response.json()
        print(f"Details for agent {agent_id}:")
        print(json.dumps(agent_details, indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for agent {agent_id}: {e}")


def create_new_conversation(agent_id: str, user_prompt: str) -> None:
    global conversationId
    global fileId

    url = f"{dust_url}/api/v1/w/{wld}/assistant/conversations"
    headers = get_standard_headers()
    data: Dict[str, Any] = {
        "message": {
            "content": user_prompt,
            "mentions": [{"configurationId": agent_id}],
            "context": {
                "username": "dust-cli-user",
                "timezone": "Europe/Paris",
            },
        },
        "blocking": True,
    }

    if fileId is not None:
        data["contentFragments"] = [{"title": "Some attached file", "fileId": fileId}]

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

    except requests.exceptions.RequestException as e:
        print(f"Error asking agent {agent_id}: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")
    except json.JSONDecodeError:
        print("Error decoding JSON response from server.")


def add_to_conversation(agent_id: str, user_prompt: str) -> None:
    global conversationId
    url = f"{dust_url}/api/v1/w/{wld}/assistant/conversations/{conversationId}/messages"
    headers = get_standard_headers()
    data = {
        "content": user_prompt,
        "mentions": [{"configurationId": agent_id}],
        "context": {
            "username": "dust-cli-user",
            "timezone": "Europe/Paris",
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

    except requests.exceptions.RequestException as e:
        print(f"Error asking agent {agent_id}: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")
    except json.JSONDecodeError:
        print("Error decoding JSON response from server.")


def prompt_agent(agent_id: str, user_prompt: str) -> None:
    global conversationId
    if conversationId is None:
        create_new_conversation(agent_id, user_prompt)
    else:
        add_to_conversation(agent_id, user_prompt)


def main() -> None:
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
                elif command == "upload":
                    if len(command_parts) > 1:
                        file_path = command_parts[1]
                        upload_and_attach_file(file_path)
                    else:
                        print("Usage: upload <file_path>")
                else:
                    print(f"Unknown command: {command}")
            elif command == "":
                continue
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
