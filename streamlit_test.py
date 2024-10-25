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
            task_details = tasks_api.get_task(task_id, opts={})

            custom_fields = task_details.get('custom_fields', [])
            task_info = {'Task Name': task_name}
            crude_purity = None  # Initialize crude purity field

            for field in custom_fields:
                field_name = field['name']  # Get the name of the custom field

                # Handle number, text, and dropdown fields
                if field['type'] == 'enum':
                    field_value = field.get('enum_value', {}).get('name', 'N/A')
                else:
                    field_value = field.get('text_value') or field.get('number_value') or 'N/A'

                if field_name == 'Crude Purity (%)' and field.get('number_value') is not None:
                    crude_purity = field.get('number_value')

                task_info[field_name] = field_value

            if crude_purity is not None:
                task_info['Crude Purity (%)'] = crude_purity
                task_data.append(task_info)

        # Create a DataFrame from the collected task data
        df = pd.DataFrame(task_data)

        # Display the DataFrame in Streamlit
        st.write(df)

        # Function to create and display SPC chart for a given field with its own filter
        def create_spc_chart(df, field_name):
            st.write(f'SPC Chart for {field_name}')

            # Create a dropdown to filter by 'Material Number', with an option to show all data
            unique_materials = ['All'] + df['Material Number'].dropna().unique().tolist()
            selected_material = st.selectbox(f'Select Material Number to filter {field_name} by:', unique_materials, key=field_name)

            # Filter the DataFrame based on the selected 'Material Number', or show all if 'All' is selected
            if selected_material != 'All':
                filtered_df = df[df['Material Number'] == selected_material]
            else:
                filtered_df = df

            if field_name in filtered_df.columns:
                # Extract selected field data
                selected_data = filtered_df[field_name].astype(float)

                # Calculate mean, UCL, and LCL for selected field
                mean = selected_data.mean()
                std_dev = selected_data.std()
                UCL = mean + 3 * std_dev  # Upper control limit (mean + 3*std)
                LCL = mean - 3 * std_dev  # Lower control limit (mean - 3*std)

                # Create the SPC chart using matplotlib
                fig, ax = plt.subplots()

                # Loop through the data and color the points based on their values
                for i, value in enumerate(selected_data):
                    if LCL <= value <= UCL:
                        ax.plot(i, value, marker='o', color='green')  # Within ±3 std.dev
                    else:
                        ax.plot(i, value, marker='o', color='red')  # Outside ±3 std.dev

                # Plot control lines and limits
                ax.axhline(mean, color='green', linestyle='--', label='Mean')
                ax.axhline(UCL, color='red', linestyle='--', label='Upper Control Limit (UCL)')
                ax.axhline(LCL, color='red', linestyle='--', label='Lower Control Limit (LCL)')

                ax.set_title(f'SPC Chart for {field_name}')
                ax.set_xlabel('Sample Number')
                ax.set_ylabel(field_name)
                ax.legend()

                # Display the plot in Streamlit
                st.pyplot(fig)

        # Pre-defined SPC charts for specific fields, each with its own filter
        create_spc_chart(df, 'Crude Purity (%)')
        create_spc_chart(df, 'Crude Yield (OD)')
        create_spc_chart(df, 'Final Purity (%)')
        create_spc_chart(df, 'Final Yield (µMol)')

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
