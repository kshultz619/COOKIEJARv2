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
    20028144: {'description': 'P15T6', 'length': 36},
    15053681: {'description': 'Nextera', 'length': 33},
    20015401: {'description': 'Nextera', 'length': 33}
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
        # Fetch all tasks for the project
        opts = {}
        tasks = list(tasks_api.get_tasks_for_project(project_id, opts))  # Convert to list
        st.write(f"Total tasks retrieved: {len(tasks)}")

        # Iterate over each task and retrieve all fields
        for task in tasks:
            task_id = task.get('gid', '')  # Task ID
            task_name = task.get('name', 'Unknown Task')  # Task name

            # Retrieve full task details, including custom fields
            try:
                task_details = tasks_api.get_task(task_id, opts={})
                if not task_details:
                    st.warning(f"Task details for {task_name} ({task_id}) are None.")
                    continue
            except ApiException as e:
                st.warning(f"Failed to retrieve details for task {task_id}: {e}")
                continue

            # Initialize task_info dictionary and populate with task fields
            task_info = {
                'Task Name': task_name,
                'Completion Date': None,  # Initialize as None for missing dates
            }

            # Extract custom fields, including `Completion Date` and others
            custom_fields = task_details.get('custom_fields', [])
            crude_purity = None
            material_number = None

            for field in custom_fields:
                field_name = field.get('name', 'Unknown Field')
                if field_name == 'Completion Date':
                    date_field = field.get('date_value')
                    task_info['Completion Date'] = date_field.get('date') if date_field else None
                elif field_name == 'Crude Purity (%)' and field.get('number_value') is not None:
                    crude_purity = field.get('number_value')
                    task_info['Crude Purity (%)'] = crude_purity
                elif field_name == 'Material Number' and field.get('text_value') is not None:
                    try:
                        material_number = int(field.get('text_value'))
                    except ValueError:
                        st.warning(f"Invalid Material Number '{field.get('text_value')}' for task '{task_name}'")
                    task_info['Material Number'] = material_number
                else:
                    if field.get('type') == 'enum':
                        task_info[field_name] = field.get('enum_value', {}).get('name', 'N/A')
                    else:
                        task_info[field_name] = field.get('text_value') or field.get('number_value') or 'N/A'

            # Calculate Coupling Efficiency if material and purity data are available
            if crude_purity is not None and material_number in primer_parts:
                length = primer_parts[material_number]['length']
                coupling_eff = coupling_efficiency(length, crude_purity)
                task_info['Coupling Efficiency'] = coupling_eff

            # Append task info to the data
            task_data.append(task_info)

        # Create and display the DataFrame with all fields for verification
        df = pd.DataFrame(task_data)
        st.write("Final DataFrame with All Task Fields:")
        st.write(df)

        # Function to create and display SPC chart for a given field with its own filter
        import plotly.graph_objects as go

        import plotly.graph_objects as go


        def create_spc_chart(df, field_name, oligo_pilot_filter=False):
            st.write(f'SPC Chart for {field_name}')

            # Dropdown for Material Number (applies to all SPC charts)
            unique_materials = ['All'] + sorted(df['Material Number'].dropna().unique().tolist())
            selected_material = st.selectbox(f"Select Material Number for {field_name}:", unique_materials,
                                             key=f"{field_name}_material")

            # Filter by Material Number
            if selected_material != 'All':
                filtered_df = df[df['Material Number'] == selected_material]
            else:
                filtered_df = df

            # Additional dropdown for Oligo Pilot (only for specific SPC charts)
            if oligo_pilot_filter:
                unique_oligos = ['All'] + sorted(filtered_df['Oligo Pilot'].dropna().unique().tolist())
                selected_oligo = st.selectbox(f"Select Oligo Pilot for {field_name}:", unique_oligos,
                                              key=f"{field_name}_oligo")

                # Filter by Oligo Pilot
                if selected_oligo != 'All':
                    filtered_df = filtered_df[filtered_df['Oligo Pilot'] == selected_oligo]

            # Proceed with SPC chart if data is available after filtering
            if field_name in filtered_df.columns:
                selected_data = filtered_df.dropna(subset=['Completion Date', field_name]).sort_values(
                    'Completion Date')

                if not selected_data.empty:
                    mean = selected_data[field_name].mean()
                    std_dev = selected_data[field_name].std()
                    UCL = mean + 3 * std_dev
                    LCL = mean - 3 * std_dev
                    y_min = LCL - std_dev
                    y_max = UCL + std_dev

                    fig = go.Figure()

                    # Plotting the data points
                    fig.add_trace(go.Scatter(
                        x=selected_data['Completion Date'],
                        y=selected_data[field_name],
                        mode='lines+markers',
                        marker=dict(color='blue'),
                        name=field_name
                    ))

                    # Shading within UCL and LCL (3-sigma limit) in light green
                    fig.add_shape(
                        type="rect",
                        x0=selected_data['Completion Date'].min(),
                        x1=selected_data['Completion Date'].max(),
                        y0=LCL,
                        y1=UCL,
                        fillcolor="lightgreen",
                        opacity=0.3,
                        line_width=0,
                    )

                    # Shading above UCL and below LCL (outside 3-sigma limit) in light red
                    fig.add_shape(
                        type="rect",
                        x0=selected_data['Completion Date'].min(),
                        x1=selected_data['Completion Date'].max(),
                        y0=y_min,
                        y1=LCL,
                        fillcolor="lightcoral",
                        opacity=0.2,
                        line_width=0,
                    )
                    fig.add_shape(
                        type="rect",
                        x0=selected_data['Completion Date'].min(),
                        x1=selected_data['Completion Date'].max(),
                        y0=UCL,
                        y1=y_max,
                        fillcolor="lightcoral",
                        opacity=0.2,
                        line_width=0,
                    )

                    # Adding control lines and sigma limits
                    fig.add_hline(y=mean, line=dict(color='green', dash='dash'), name='Mean')
                    fig.add_hline(y=UCL, line=dict(color='red', dash='dash'), name='UCL')
                    fig.add_hline(y=LCL, line=dict(color='red', dash='dash'), name='LCL')

                    # Updating layout with expanded y-axis limits
                    fig.update_layout(
                        title=f'SPC Chart for {field_name}',
                        xaxis_title='Completion Date',
                        yaxis_title=field_name,
                        yaxis=dict(range=[y_min, y_max]),
                        legend_title='Legend'
                    )

                    st.plotly_chart(fig)
                else:
                    st.warning(f"No valid data available for {field_name} to plot.")


        # Example of calling the function for different fields
        # Call with oligo_pilot_filter=True for fields that require the additional dropdown
        create_spc_chart(df, 'Crude Purity (%)', oligo_pilot_filter=True)
        create_spc_chart(df, 'Coupling Efficiency', oligo_pilot_filter=True)
        create_spc_chart(df, 'Crude Yield (OD)', oligo_pilot_filter=True)
        create_spc_chart(df, 'Final Purity (%)')
        create_spc_chart(df, 'Final Yield (OD)')

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
