import json
import os
import base64
import csv
from typing import List, Dict, Any

from langchain_huggingface import HuggingFacePipeline
from pydantic import BaseModel
from transformers import pipeline
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, BooleanObject

# === Common Models ===
class ServiceLine(BaseModel):
    from_date: str
    to_date: str
    place_of_service: str
    emergency: bool
    procedure_code: str
    modifier: str
    diagnosis_pointer: str
    charges: float
    days_units: int
    epsdt_family_plan: bool
    rendering_provider_npi: str

class CMS1500Form(BaseModel):
    # Patient Information (Boxes 1-13)
    patient_last_name: str
    patient_first_name: str
    patient_middle_initial: str
    patient_address: str
    patient_city: str
    patient_state: str
    patient_zip: str
    patient_phone: str
    patient_dob: str
    patient_sex: str
    patient_ssn: str
    patient_relationship_to_insured: str
    insured_last_name: str
    insured_first_name: str
    insured_middle_initial: str
    insured_policy_group_number: str
    insured_dob: str
    insured_sex: str
    insured_employer_name: str
    insured_plan_name: str
    insured_ssn: str
    
    # Insurance Information (Boxes 14-33)
    is_other_health_benefit_plan: bool
    reserved_for_local_use: str
    insured_signature: str
    insured_signature_date: str
    insured_authorization: bool
    
    # Provider Information (Boxes 24-33)
    referring_provider_last_name: str
    referring_provider_first_name: str
    referring_provider_npi: str
    additional_claim_info: str
    outside_lab: bool
    outside_lab_charges: float
    reserved_for_nucc_use: str
    diagnosis_codes: List[str]
    
    # Service Information (Boxes 24A-H)
    service_lines: List[ServiceLine]
    
    # Billing Information (Boxes 24I-J)
    federal_tax_id: str
    patient_account_number: str
    accept_assignment: bool
    total_charge: float
    amount_paid: float
    balance_due: float
    provider_signature: str
    provider_signature_date: str
    service_facility_location: str
    billing_provider_npi: str
    billing_provider_taxonomy: str

class CMS1500FormEnhanced(BaseModel):
    patient_name: str
    dob: str
    gender: str
    address: str
    phone_number: str
    relationship_to_insured: str
    insurance_name: str
    insurance_id: str
    other_insurance_name: str
    accident_related: str
    prior_auth_number: str
    provider_name: str
    provider_npi: str
    service_facility_name: str
    billing_provider_name: str
    billing_provider_address: str
    diagnosis_codes: List[str]
    procedure_codes: List[str]
    date_of_service: str
    total_charge: float
    physician_signature: str

# === Model Loading Functions ===
def load_model(model_name="HuggingFaceH4/zephyr-7b-beta"):
    """
    Load a HuggingFace model for text generation.
    
    Args:
        model_name (str): The name of the model to load. Defaults to "HuggingFaceH4/zephyr-7b-beta".
                         Other options include "mistralai/Mistral-7B-Instruct-v0.2"
    
    Returns:
        HuggingFacePipeline: The loaded model pipeline
    """
    return HuggingFacePipeline(
        pipeline=pipeline(
            "text-generation",
            model=model_name,
            device_map="auto",
            max_new_tokens=512,
            do_sample=False,
        )
    )


class CMS1500Filler:
    def __init__(self, template_path='form-cms1500.pdf', output_folder='pdf_outputs/'):
        self.template_path = template_path
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)

    def fill_pdf(input_pdf: str, data: dict, output_pdf: str):
        """Fill and save PDF with NeedAppearances = true."""
        reader = PdfReader(input_pdf)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        for page in writer.pages:
            writer.update_page_form_field_values(page, data)
        writer._root_object[NameObject("/AcroForm")][NameObject("/NeedAppearances")] = BooleanObject(True)
        with open(output_pdf, "wb") as out_f:
            writer.write(out_f)

# === Comparison Functions ===
def compare_forms(raw_data: Dict[str, Any], gt_data: Dict[str, Any], report_file: str = 'comparison_report.csv') -> str:
    """
    Compare two sets of form data and generate a CSV report.
    
    Args:
        raw_data (Dict[str, Any]): Data from raw extraction
        gt_data (Dict[str, Any]): Ground truth data
        report_file (str): Path to save the comparison report
    
    Returns:
        str: Path to the generated report file
    """
    print("Comparing forms")
    keys = set(raw_data.keys()) | set(gt_data.keys())
    with open(report_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Field', 'Raw Extraction', 'Ground Truth', 'Match'])
        for key in sorted(keys):
            raw_val = raw_data.get(key)
            gt_val = gt_data.get(key)
            match = raw_val == gt_val
            writer.writerow([key, raw_val, gt_val, match])
    print("FINISHED comparing forms")
    return report_file

# === FHIR Data Extraction ===
def extract_diagnostic_report_text(fhir_bundle):
    print("Extracting diagnostic report text")
    diagnostic_report = next(r['resource'] for r in fhir_bundle['entry'] if r['resource']['resourceType'] == 'DiagnosticReport')
    raw_text_b64 = diagnostic_report['presentedForm'][0]['data']
    print("FINISHED extracting diagnostic report text")
    return base64.b64decode(raw_text_b64).decode('utf-8') 