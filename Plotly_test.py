import asana
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from asana import ApiClient, Configuration
from asana.rest import ApiException

# Dictionary containing material information
primer_parts = {
    15066464: {'description': 'P5T10', 'length': 40},
    20012515: {'description': 'P5T10', 'length': 40},
    15066466: {'description': 'P7T10', 'length': 35},
    20012516: {'description': 'P7T10', 'length': 35},
    15065092: {'description': 'P5T6', 'length': 36},
    15065093: {'description': 'P7T6', 'length': 31},
    15053684: {'description': 'SBS3', 'length': 32},
    20015402: {'description': 'SBS3', 'length': 32},
    15071282: {'description': 'P5CFR', 'length': 21},
    20021635: {'description': 'P5CFR', 'length': 21},
    15071281: {'description': 'P7CFR', 'length': 22},
    20021636: {'description': 'P7CFR', 'length': 22},
    20028144: {'description': 'P15T6', 'length': 36}
}

# Function to calculate Coupling Efficiency
def coupling_efficiency(length, crude_purity):
    return (crude_purity / 1000) ** (1 / (length - 1))

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
            task_info = {
                'Task Name': task_name,
                'Completion Date': task_details.get('completed_at'),  # Completion Date
                'Oligo Pilot': task_details.get('assignee', {}).get('name')  # Assuming Oligo Pilot refers to assignee
            }
            crude_purity = None  # Initialize crude purity field
            material_number = None  # Initialize material number

            for field in custom_fields:
                field_name = field['name']  # Get the name of the custom field

                # Handle number, text, and dropdown fields
                if field['type'] == 'enum':
                    field_value = field.get('enum_value', {}).get('name', 'N/A')
                else:
                    field_value = field.get('text_value') or field.get('number_value') or 'N/A'

                if field_name == 'Crude Purity (%)' and field.get('number_value') is not None:
                    crude_purity = field.get('number_value')
                if field_name == 'Material Number' and field.get('text_value') is not None:
                    try:
                        # Convert string material number to integer
                        material_number = int(field.get('text_value'))
                    except ValueError:
                        st.warning(f"Invalid Material Number '{field.get('text_value')}' for task '{task_name}'")

                task_info[field_name] = field_value

            # Calculate coupling efficiency if crude_purity and material_number are available
            if crude_purity is not None and material_number in primer_parts:
                length = primer_parts[material_number]['length']
                coupling_eff = coupling_efficiency(length, crude_purity)
                task_info['Coupling Efficiency'] = coupling_eff

            if crude_purity is not None:
                task_info['Crude Purity (%)'] = crude_purity
                task_data.append(task_info)

        # Create a DataFrame from the collected task data
        df = pd.DataFrame(task_data)

        # Convert 'Completion Date' to datetime
        df['Completion Date'] = pd.to_datetime(df['Completion Date'])

        # Display the DataFrame in Streamlit
        st.write(df)

        # Function to create and display SPC chart for a given field with its own filter
        def create_spc_chart(df, field_name, filter_oligo=False):
            st.write(f'SPC Chart for {field_name}')

            # Create a dropdown to filter by 'Material Number', with an option to show all data
            unique_materials = ['All'] + df['Material Number'].dropna().unique().tolist()
            selected_material = st.selectbox(f'Select Material Number to filter {field_name} by:', unique_materials, key=field_name)

            # Additional dropdown for 'Oligo Pilot' if filter_oligo is True
            selected_oligo = None
            if filter_oligo:
                unique_oligos = ['All'] + df['Oligo Pilot'].dropna().unique().tolist()
                selected_oligo = st.selectbox(f'Select Oligo Pilot to filter {field_name} by:', unique_oligos, key=field_name + '_oligo')

            # Filter the DataFrame based on the selected 'Material Number' and 'Oligo Pilot'
            filtered_df = df
            if selected_material != 'All':
                filtered_df = filtered_df[filtered_df['Material Number'] == selected_material]
            if filter_oligo and selected_oligo != 'All':
                filtered_df = filtered_df[filtered_df['Oligo Pilot'] == selected_oligo]

            if field_name in filtered_df.columns:
                # Extract selected field data and drop any missing values (NaN)
                filtered_df = filtered_df.dropna(subset=['Completion Date', field_name])
                selected_data = filtered_df.sort_values('Completion Date')

                if not selected_data.empty:
                    # Calculate mean, UCL, and LCL for selected field
                    mean = selected_data[field_name].mean()
                    std_dev = selected_data[field_name].std()
                    UCL = mean + 3 * std_dev  # Upper control limit (mean + 3*std)
                    LCL = mean - 3 * std_dev  # Lower control limit (mean - 3*std)

                    # Create the SPC chart using Plotly
                    fig = go.Figure()

                    # Add data points as scatter plot with dates on x-axis
                    fig.add_trace(go.Scatter(
                        x=selected_data['Completion Date'],
                        y=selected_data[field_name],
                        mode='lines+markers',
                        marker=dict(color='blue'),
                        name=field_name
                    ))

                    # Loop through the data and color the points based on their values
                    for _, row in selected_data.iterrows():
                        color = 'green' if LCL <= row[field_name] <= UCL else 'red'
                        fig.add_trace(go.Scatter(
                            x=[row['Completion Date']],
                            y=[row[field_name]],
                            mode='markers',
                            marker=dict(color=color),
                            showlegend=False
                        ))

                    # Add mean, UCL, and LCL lines
                    fig.add_hline(y=mean, line=dict(color='green', dash='dash'), name='Mean')
                    fig.add_hline(y=UCL, line=dict(color='red', dash='dash'), name='Upper Control Limit (UCL)')
                    fig.add_hline(y=LCL, line=dict(color='red', dash='dash'), name='Lower Control Limit (LCL)')

                    # Update layout for the plot
                    fig.update_layout(
                        title=f'SPC Chart for {field_name}',
                        xaxis_title='Completion Date',
                        yaxis_title=field_name,
                        legend_title='Legend'
                    )

                    # Display the plot in Streamlit
                    st.plotly_chart(fig)
                else:
                    st.warning(f"No data available for {field_name}")

        # Pre-defined SPC charts with updated filters
        create_spc_chart(df, 'Crude Purity (%)', filter_oligo=True)
        create_spc_chart(df, 'Coupling Efficiency', filter_oligo=True)
        create_spc_chart(df, 'Crude Yield (OD)', filter_oligo=True)
        create_spc_chart(df, 'Final Purity (%)')
        create_spc_chart(df, 'Final Yield (µMol)')

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
