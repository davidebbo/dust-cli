import argparse
import os
import requests
from dotenv import load_dotenv

load_dotenv()

dust_token = os.getenv("DUST_TOKEN")
wld = os.getenv("WLD")
space_id = os.getenv("SPACE_ID")
dsId = os.getenv("DSID")
dust_url = os.getenv("DUST_URL")


def _get_auth_headers():
    return {
        "Authorization": f"Bearer {dust_token}",
        "Content-Type": "application/json",
    }


def get_existing_dust_files():
    url = f"{dust_url}/api/v1/w/{wld}/spaces/{space_id}/data_sources/{dsId}/documents"
    response = requests.get(url, headers={"Authorization": f"Bearer {dust_token}"})  # Note: get_existing_dust_files only needs Authorization

    # Response looks like this:
    # {
    #     "documents": [
    #       {
    #         "document_id": "doc1",
    #         etc...
    #       },
    #       {
    #         "document_id": "doc2"
    #       }
    #     ]
    # }

    # Put the document_id for all the docs into a set
    return set(doc["document_id"] for doc in response.json()["documents"])


def upload_file(file_path, file_name):
    # Read the file content
    with open(file_path, "r") as file:
        file_content = file.read()

    url = f"{dust_url}/api/v1/w/{wld}/spaces/{space_id}/data_sources/{dsId}/documents/{file_name}"
    headers = _get_auth_headers()
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
    headers = _get_auth_headers()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        agents = response.json()
        print("Available agents:")
        for agent in agents['agentConfigurations']:
            print(f"{agent['sId']}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching agents: {e}")


def get_agent_details(agent_id):
    url = f"{dust_url}/api/v1/w/{wld}/assistant/agent_configurations/{agent_id}"
    headers = _get_auth_headers()

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


def main():
    while True:
        try:
            command_input = input("dust-cli> ").strip()
            command_parts = command_input.lower().split()
            command = command_parts[0] if command_parts else ""

            if command == "exit":
                break
            elif command == "list-agents":
                list_agents()
            elif command == "get-agent":
                if len(command_parts) > 1:
                    agent_id = command_parts[1]
                    get_agent_details(agent_id)
                else:
                    print("Usage: get-agent <agent_id>")
            elif command == "":
                continue  # Handle empty input
            else:
                print(f"Unknown command: {command}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:  # Handle Ctrl+D
            print("\nExiting...")
            break


if __name__ == "__main__":
    main()
