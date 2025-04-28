import os
import json
from llm_workflow import main as process_patient

def process_all_patients():
    # Path to the patient data directory
    patient_data_dir = 'patient_data'
    
    # Get all JSON files in the directory
    patient_files = [f for f in os.listdir(patient_data_dir) if f.endswith('.json')]
    
    # Create a directory for filled patient data if it doesn't exist
    os.makedirs('filled_patient_data', exist_ok=True)
    
    # Process each patient
    for patient_file in patient_files:
        try:
            print(f"Processing patient: {patient_file}")
            
            # Get the full path to the patient's file
            patient_file_path = os.path.join(patient_data_dir, patient_file)
            
            # Run the pipeline for this patient with the file path
            output_pdf = process_patient(patient_file_path)
            
            # Move the output file to filled_patient_data with patient-specific name
            patient_id = os.path.splitext(patient_file)[0]
            os.rename(output_pdf, f'filled_patient_data/Filled_{patient_id}.pdf')
            
        except Exception as e:
            print(f"Error processing {patient_file}: {str(e)}")
            continue

if __name__ == "__main__":
    process_all_patients() 