import asana
import pandas as pd
import streamlit as st
from asana import ApiClient, Configuration
from asana.rest import ApiException

# Streamlit UI for input
st.title('Welcome to Kevin\'s Cake Factory!')

# Get token via Streamlit input
token = st.text_input('Input your user Asana token:\nIf you do not know what this is, please do not proceed.')

if token:
    # Initialize Asana API Client
    configuration = Configuration()
    configuration.access_token = token
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

        st.write(f'Total PrOs retrieved: {len(tasks)}')

        # Iterate over each task and retrieve custom fields
        for task in tasks:
            task_id = task['gid']  # Get task ID
            task_name = task['name']  # Get task name

            # Retrieve full task details including custom fields
            task_details = tasks_api.get_task(task_id, opts={})  # Added opts argument

            custom_fields = task_details.get('custom_fields', [])
            task_info = {'Task Name': task_name}
            for field in custom_fields:
                field_name = field['name']  # Get the name of the custom field
                # Check if it's a dropdown field
                if field['type'] == 'enum':
                    # For dropdown (enum) fields, get the selected option name
                    field_value = field.get('enum_value', {}).get('name', 'N/A')
                else:
                    # Handle other field types (text, number)
                    field_value = field.get('text_value') or field.get('number_value') or 'N/A'

                task_info[field_name] = field_value  # Store the name and value in task_info dict

            task_data.append(task_info)

        # Create a DataFrame from the collected task data
        df = pd.DataFrame(task_data)

        # Display the DataFrame in Streamlit
        st.write(df)

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
