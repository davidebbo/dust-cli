import argparse
import os
import requests
from dotenv import load_dotenv

load_dotenv()

dust_token = os.getenv("DUST_TOKEN")
wld = os.getenv("WLD")
space_id = os.getenv("SPACE_ID")
dsId = os.getenv("DSID")


def get_existing_dust_files():
    url = f"https://dust.tt/api/v1/w/{wld}/spaces/{space_id}/data_sources/{dsId}/documents"
    response = requests.get(url, headers={"Authorization": f"Bearer {dust_token}"})

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

    url = f"https://dust.tt/api/v1/w/{wld}/spaces/{space_id}/data_sources/{dsId}/documents/{file_name}"
    headers = {
        "Authorization": f"Bearer {dust_token}",
        "Content-Type": "application/json",
    }
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
    url = f"https://dust.tt/api/v1/w/{wld}/assistant/agent_configurations"

    headers = {
        "Authorization": f"Bearer {dust_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        agents = response.json()
        print("Available agents:")
        for agent in agents['agentConfigurations']:
            print(f"Agent ID: {agent['sId']}, Name: {agent['instructions']}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching agents: {e}")


def get_markdown_files(folder_path):
    markdown_files = []

    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory.")
        return markdown_files

    # Walk through all files in the directory
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                markdown_files.append(file_path)

    # Sort files alphabetically for consistent ordering
    markdown_files.sort()

    return markdown_files


def upload_all_files(args):
    markdown_files = get_markdown_files(args.inputfolder)
    existing_files = get_existing_dust_files()
    for file_path in markdown_files:
        file_name_with_extension = os.path.basename(file_path)
        file_name, _ = os.path.splitext(file_name_with_extension)
        if file_name not in existing_files:
            upload_file(file_path, file_name)
        else:
            print(f"{file_name} already exists in Dust.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # parser.add_argument(
    #     "inputfolder",
    #     type=str,
    #     help="Folder containing markdown files to upload",
    # )

    # args = parser.parse_args()

    list_agents()

    # upload_all_files(args)


if __name__ == "__main__":
    main()
