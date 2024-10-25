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

        # List of custom fields for which we want to generate SPC charts
        spc_fields = ['Crude Purity (%)', 'Crude Yield (OD)', 'Final Purity (%)', 'Final Yield (µMol)']  # Add other custom field names

        # Iterate over each task and retrieve custom fields
        for task in tasks:
            task_id = task['gid']  # Get task ID
            task_name = task['name']  # Get task name

            # Retrieve full task details including custom fields
            task_details = tasks_api.get_task(task_id, opts={})  # Added opts argument

            custom_fields = task_details.get('custom_fields', [])
            task_info = {'Task Name': task_name}
            crude_purity = None  # Initialize crude purity field

            for field in custom_fields:
                field_name = field['name']  # Get the name of the custom field

                # Handle different types of fields
                if field['type'] == 'enum':
                    # Handle dropdown (enum) fields
                    field_value = field.get('enum_value', {}).get('name', 'N/A')
                else:
                    # Handle text and number fields
                    field_value = field.get('text_value') or field.get('number_value') or 'N/A'

                task_info[field_name] = field_value  # Store the name and value in task_info dict

            # Append task info to task_data
            task_data.append(task_info)

        if not task_data:
            st.warning('No tasks found with the relevant data.')

        # Create a DataFrame from the collected task data
        df = pd.DataFrame(task_data)

        # Display the DataFrame in Streamlit
        st.write(df)

        if not df.empty:
            for field_name in spc_fields:
                if field_name in df.columns:
                    # Extract data for the SPC chart for this custom field
                    field_values = df[field_name].replace('N/A', pd.NA).dropna().astype(float)

                    # Calculate mean, UCL, and LCL
                    mean = field_values.mean()
                    std_dev = field_values.std()
                    UCL = mean + 3 * std_dev  # Upper control limit (mean + 3*std)
                    LCL = mean - 3 * std_dev  # Lower control limit (mean - 3*std)

                    # Create the SPC chart using matplotlib
                    fig, ax = plt.subplots()

                    ax.plot(field_values, marker='o', linestyle='-', color='b', label=field_name)
                    ax.axhline(mean, color='green', linestyle='--', label='Mean')
                    ax.axhline(UCL, color='red', linestyle='--', label='Upper Control Limit (UCL)')
                    ax.axhline(LCL, color='red', linestyle='--', label='Lower Control Limit (LCL)')

                    ax.set_title(f'SPC Chart for {field_name}')
                    ax.set_xlabel('Sample Number')
                    ax.set_ylabel(field_name)
                    ax.legend()

                    # Display the plot in Streamlit
                    st.pyplot(fig)
                else:
                    st.warning(f'{field_name} not found in the task data.')

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
