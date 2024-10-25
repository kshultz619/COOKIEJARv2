import asana
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
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
            crude_purity = None  # Initialize crude purity field

            # Debug: Print the available custom field names
            st.write(f"Custom fields for task {task_name}: {[field['name'] for field in custom_fields]}")

            for field in custom_fields:
                field_name = field['name']  # Get the name of the custom field
                if field_name == 'Crude Purity (%)':
                    # Check if it's a number field
                    field_value = field.get('number_value')
                    if field_value is not None:
                        crude_purity = field_value
                else:
                    # Handle other custom fields
                    field_value = field.get('text_value') or field.get('number_value') or 'N/A'

                task_info[field_name] = field_value  # Store the name and value in task_info dict

            # Append only tasks with crude purity data
            if crude_purity is not None:
                task_info['Crude Purity (%)'] = crude_purity
                task_data.append(task_info)

        if not task_data:
            st.warning('No tasks with Crude Purity data found.')

        # Create a DataFrame from the collected task data
        df = pd.DataFrame(task_data)

        # Display the DataFrame in Streamlit
        st.write(df)

        if not df.empty:
            # Extract crude purity data for SPC chart
            crude_purity_values = df['Crude Purity (%)'].astype(float)

            # Calculate mean, UCL, and LCL
            mean = crude_purity_values.mean()
            std_dev = crude_purity_values.std()
            UCL = mean + 3 * std_dev  # Upper control limit (mean + 3*std)
            LCL = mean - 3 * std_dev  # Lower control limit (mean - 3*std)

            # Create the SPC chart using matplotlib
            fig, ax = plt.subplots()

            ax.plot(crude_purity_values, marker='o', linestyle='-', color='b', label='Crude Purity (%)')
            ax.axhline(mean, color='green', linestyle='--', label='Mean')
            ax.axhline(UCL, color='red', linestyle='--', label='Upper Control Limit (UCL)')
            ax.axhline(LCL, color='red', linestyle='--', label='Lower Control Limit (LCL)')

            ax.set_title('SPC Chart for Crude Purity (%)')
            ax.set_xlabel('Sample Number')
            ax.set_ylabel('Crude Purity')
            ax.legend()

            # Display the plot in Streamlit
            st.pyplot(fig)

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
