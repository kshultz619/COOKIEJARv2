import asana
import pandas as pd
from asana import ApiClient, Configuration
from asana.rest import ApiException

# Get token via input
token = input('Please input your user token:\n')
configuration = Configuration()
configuration.access_token = token

# Initialize ApiClient
client = ApiClient(configuration)

# Use your actual project ID
project_id = '1208621578201454'  # Replace with your actual project ID

# Access the Tasks API
tasks_api = asana.TasksApi(client)

# Prepare to collect task data
task_data = []

try:
    # Get all tasks for the project and convert the generator to a list
    opts = {}
    tasks = list(tasks_api.get_tasks_for_project(project_id, opts))  # Convert to list

    print(f'Total tasks retrieved: {len(tasks)}')

    # Iterate over each task and retrieve custom fields
    for task in tasks:
        task_id = task['gid']  # Get task ID
        task_name = task['name']  # Get task name

        # Retrieve full task details including custom fields
        task_details = tasks_api.get_task(task_id, opts={})  # Added opts argument

        # Extract custom field names and values dynamically
        custom_fields = task_details.get('custom_fields', [])
        print(f"Custom fields for task '{task_name}':")

        task_info = {'Task Name': task_name}
        for field in custom_fields:
            field_name = field['name']  # Get the name of the custom field
            field_value = field.get('text_value') or field.get('number_value') or 'N/A'  # Get the value of the custom field
            task_info[field_name] = field_value  # Store the name and value in task_info dict

        task_data.append(task_info)

    # Create a DataFrame from the collected task data
    df = pd.DataFrame(task_data)

    # Print the DataFrame
    print(df)

except ApiException as e:
    print(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
except Exception as ex:
    print(f"An error occurred: {ex}")
