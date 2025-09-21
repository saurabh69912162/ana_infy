from openai import OpenAI
import json
from itertools import islice
from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
# from database import init_db, insert_request, get_all_requests, toggle_ticket_status

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key="")

# Load examples from JSON file
with open('training_data/mini_.json', 'r') as file:
    examples = json.load(file)

# Function to classify user input
def classify_input(user_input):
    # Prepare the prompt with examples
    prompt = """
    You are an AI orchestrator. Based on the user input, decide the category, severity, urgency, and agent name. Use the examples provided to guide your decision. Do not answer any other questions.
    and return the response in a json format strictly with the keys category, severity, urgency, and agent.
    Examples:
    """
    for category, subtickets in islice(examples.items(),1):
        for subcategory, data in subtickets.items():
            for prompt_data in data['prompts']:
                prompt += f"User Input: {prompt_data['text']}\nCategory: {category}\nSeverity: {prompt_data['severity']}\nUrgency: {prompt_data['urgency']}\nAgent: {prompt_data['agent']}\n---\n"

    # Add the user input to the prompt
    prompt += f"User Input: {user_input}\n"

    # Call the OpenAI API with function calling
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a classifier agent.and I am sharing sample dataset how and what to classify, do not answer any other questions. apartf from this. data is  - "+prompt},
            {"role": "user", "content": user_input}
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "classify_ticket",
                    "description": "Classify IT issue and return details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "severity": {"type": "string"},
                            "urgency": {"type": "string"},
                            "agent": {"type": "string"}
                        },
                        "required": ["category", "severity", "urgency", "agent"]
                    }
                }
            }
        ],
        tool_choice={"type":"function","function":{"name":"classify_ticket"}}
    )
    print('response',response)
    arguments = response.choices[0].message.tool_calls[0].function.arguments
    classification = json.loads(arguments)
    return classification

# Function to handle Access & Authentication issues
def access_and_authentication(classification, user_input):
    if not classification:
        return "Error: Unable to classify the issue."

    # Extract severity and urgency from classification
    severity = classification.get('severity')
    urgency = classification.get('urgency')

    # Prepare the prompt for the AI agent
    prompt = f"""
    You are an expert in Access & Authentication issues. Based on the severity and urgency, provide a brief solution for the following issue, Do not answer any other questions.:
    User Input: {user_input}
    Severity: {severity}
    Urgency: {urgency}
    """

    # Call the AI agent to generate a solution
    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=["---"],
        temperature=0.5
    )

    # Extract the solution from the response
    solution = response.choices[0].text.strip()

    # If severity is Immediate, indicate assignment to a human
    if severity == "Immediate":
        solution += "\nThis issue has been assigned to a human agent for immediate attention."

    return solution

# Function to handle Networking & Connectivity issues
def networking_connectivity(classification, user_input):
    severity = classification.get('severity')
    urgency = classification.get('urgency')

    prompt = f"""
    You are an expert in Networking & Connectivity issues. Based on the severity and urgency, provide a brief solution for the following issue, Do not answer any other questions.:
    User Input: {user_input}
    Severity: {severity}
    Urgency: {urgency}
    """

    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=["---"],
        temperature=0.5
    )

    solution = response.choices[0].text.strip()
    if severity == "Immediate":
        solution += "\nThis issue has been assigned to a human agent for immediate attention."

    return solution

# Function to handle Hardware / Device Issues
def hardware_device_issues(classification, user_input):
    severity = classification.get('severity')
    urgency = classification.get('urgency')

    prompt = f"""
    You are an expert in Hardware / Device Issues. Based on the severity and urgency, provide a brief solution for the following issue, Do not answer any other questions.:
    User Input: {user_input}
    Severity: {severity}
    Urgency: {urgency}
    """

    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=["---"],
        temperature=0.5
    )

    solution = response.choices[0].text.strip()
    if severity == "Immediate":
        solution += "\nThis issue has been assigned to a human agent for immediate attention."

    return solution

# Function to handle Software / Applications issues
def software_applications(classification, user_input):
    severity = classification.get('severity')
    urgency = classification.get('urgency')

    prompt = f"""
    You are an expert in Software / Applications issues. Based on the severity and urgency, provide a brief solution for the following issue, Do not answer any other questions.:
    User Input: {user_input}
    Severity: {severity}
    Urgency: {urgency}
    """

    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=["---"],
        temperature=0.5
    )

    solution = response.choices[0].text.strip()
    if severity == "Immediate":
        solution += "\nThis issue has been assigned to a human agent for immediate attention."

    return solution

# Function to handle Collaboration & Productivity Tools issues
def collaboration_productivity_tools(classification, user_input):
    severity = classification.get('severity')
    urgency = classification.get('urgency')

    prompt = f"""
    You are an expert in Collaboration & Productivity Tools issues. Based on the severity and urgency, provide a brief solution for the following issue, Do not answer any other questions.:
    User Input: {user_input}
    Severity: {severity}
    Urgency: {urgency}
    """

    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=["---"],
        temperature=0.5
    )

    solution = response.choices[0].text.strip()
    if severity == "Immediate":
        solution += "\nThis issue has been assigned to a human agent for immediate attention."

    return solution

# Function to handle Security & Compliance issues
def security_compliance(classification, user_input):
    severity = classification.get('severity')
    urgency = classification.get('urgency')

    prompt = f"""
    You are an expert in Security & Compliance issues. Based on the severity and urgency, provide a brief solution for the following issue, Do not answer any other questions.:
    User Input: {user_input}
    Severity: {severity}
    Urgency: {urgency}
    """

    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=["---"],
        temperature=0.5
    )

    solution = response.choices[0].text.strip()
    if severity == "Immediate":
        solution += "\nThis issue has been assigned to a human agent for immediate attention."

    return solution

# Example usage
if __name__ == "__main__":
    user_input = "I forgot my AD password and cannot log in."
    classification = classify_input(user_input)
    if classification and classification.get('category') == 'Access & Authentication':
        solution = access_and_authentication(classification, user_input)
        print(solution)