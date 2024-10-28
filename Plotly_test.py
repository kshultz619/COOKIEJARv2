import asana
import streamlit as st
import plotly.graph_objects as go
from asana import ApiClient, Configuration
from asana.rest import ApiException
import pandas as pd

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
token = st.text_input('Input your Asana token:')

if token:
    configuration = Configuration()
    configuration.access_token = token
    client = ApiClient(configuration)
    project_id = '1208621578201454'  # Replace with your project ID
    tasks_api = asana.TasksApi(client)
    task_data = []

    try:
        tasks = list(tasks_api.get_tasks_for_project(project_id, opts={}))

        for task in tasks:
            if task is None:
                continue

            task_id = task.get('gid', '')
            task_name = task.get('name', 'Unknown Task')

            try:
                task_details = tasks_api.get_task(task_id, opts={})
                if task_details is None:
                    continue
            except ApiException:
                continue

            task_info = {'Task Name': task_name, 'Completion Date': None}
            custom_fields = task_details.get('custom_fields', [])

            # Process custom fields and calculate coupling efficiency if applicable
            crude_purity, material_number = None, None
            for field in custom_fields:
                if field is None:
                    continue

                field_name = field.get('name', 'Unknown Field')

                # Extract relevant custom field values
                if field_name == 'Completion Date':
                    date_field = field.get('date_value')
                    task_info['Completion Date'] = date_field.get('date') if date_field else None
                elif field_name == 'Crude Purity (%)':
                    crude_purity = field.get('number_value')
                    task_info['Crude Purity (%)'] = crude_purity
                elif field_name == 'Material Number':
                    material_number_text = field.get('text_value')
                    if material_number_text:
                        try:
                            material_number = int(material_number_text)
                        except ValueError:
                            pass
                    task_info['Material Number'] = material_number
                else:
                    if field.get('type') == 'enum' and field.get('enum_value') is not None:
                        task_info[field_name] = field['enum_value'].get('name', 'N/A')
                    else:
                        task_info[field_name] = field.get('text_value') or field.get('number_value') or 'N/A'

            # Calculate Coupling Efficiency if applicable
            if crude_purity is not None and material_number in primer_parts:
                length = primer_parts[material_number]['length']
                task_info['Coupling Efficiency'] = coupling_efficiency(length, crude_purity)

            task_data.append(task_info)

        # Function to create and display SPC chart for a given field
        def create_spc_chart(data, field_name, oligo_pilot_filter=False):
            st.write(f'SPC Chart for {field_name}')

            # Convert task data to DataFrame for charting
            df = pd.DataFrame(data)

            # Dropdown filter for Task Name
            unique_tasks = ['All'] + sorted(df['Task Name'].dropna().unique().tolist())
            selected_task = st.selectbox(f"Select Task Name for {field_name}:", unique_tasks, key=f"{field_name}_task")

            filtered_df = df[df['Task Name'] == selected_task] if selected_task != 'All' else df

            if oligo_pilot_filter:
                unique_oligos = ['All'] + sorted(filtered_df['Oligo Pilot'].dropna().unique().tolist())
                selected_oligo = st.selectbox(f"Select Oligo Pilot for {field_name}:", unique_oligos, key=f"{field_name}_oligo")
                filtered_df = filtered_df[filtered_df['Oligo Pilot'] == selected_oligo] if selected_oligo != 'All' else filtered_df

            # Proceed if there's data
            if field_name in filtered_df.columns:
                selected_data = filtered_df.dropna(subset=['Completion Date', field_name]).sort_values('Completion Date')
                if not selected_data.empty:
                    mean = selected_data[field_name].mean()
                    std_dev = selected_data[field_name].std()
                    UCL, LCL = mean + 3 * std_dev, mean - 3 * std_dev
                    y_min, y_max = LCL - std_dev, UCL + std_dev

                    fig = go.Figure(go.Scatter(x=selected_data['Completion Date'], y=selected_data[field_name],
                                               mode='lines+markers', marker=dict(color='blue'), name=field_name))

                    # Shading within UCL and LCL
                    fig.add_shape(type="rect", x0=selected_data['Completion Date'].min(),
                                  x1=selected_data['Completion Date'].max(), y0=LCL, y1=UCL,
                                  fillcolor="lightgreen", opacity=0.3, line_width=0)
                    fig.add_shape(type="rect", x0=selected_data['Completion Date'].min(),
                                  x1=selected_data['Completion Date'].max(), y0=y_min, y1=LCL,
                                  fillcolor="lightcoral", opacity=0.2, line_width=0)
                    fig.add_shape(type="rect", x0=selected_data['Completion Date'].min(),
                                  x1=selected_data['Completion Date'].max(), y0=UCL, y1=y_max,
                                  fillcolor="lightcoral", opacity=0.2, line_width=0)

                    # Adding control lines
                    fig.add_hline(y=mean, line=dict(color='green', dash='dash'), name='Mean')
                    fig.add_hline(y=UCL, line=dict(color='red', dash='dash'), name='UCL')
                    fig.add_hline(y=LCL, line=dict(color='red', dash='dash'), name='LCL')

                    fig.update_layout(title=f'SPC Chart for {field_name}', xaxis_title='Completion Date',
                                      yaxis_title=field_name, yaxis=dict(range=[y_min, y_max]), legend_title='Legend')
                    st.plotly_chart(fig)
                else:
                    st.warning(f"No valid data available for {field_name} to plot.")

        # Generate SPC charts
        create_spc_chart(task_data, 'Crude Purity (%)', oligo_pilot_filter=True)
        create_spc_chart(task_data, 'Coupling Efficiency', oligo_pilot_filter=True)
        create_spc_chart(task_data, 'Crude Yield (OD)', oligo_pilot_filter=True)
        create_spc_chart(task_data, 'Purification Recovery (%)')
        create_spc_chart(task_data, 'Desalt Recovery (%)')
        create_spc_chart(task_data, 'Desalt Volume (mL)')
        create_spc_chart(task_data, 'Final Purity (%)')
        create_spc_chart(task_data, 'Final Yield (OD)')

    except ApiException as e:
        st.error(f"Exception when calling TasksApi->get_tasks_for_project: {e}")
    except Exception as ex:
        st.error(f"An error occurred: {ex}")
