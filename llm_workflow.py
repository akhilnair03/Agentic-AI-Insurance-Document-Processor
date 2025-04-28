#!/usr/bin/env python3
import os
import sys
import json
from openai import OpenAI
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

# 1) List of all CMS-1500 PDF field keys we expect
FIELD_KEYS = [
    # Patient Demographics
    "pt_name","birth_mm","birth_dd","birth_yy","sex",
    "pt_street","pt_city","pt_state","pt_zip","pt_AreaCode","pt_phone","ssn","rel_to_ins",
    # Insurance
    "insurance_name","insurance_address","insurance_address2","insurance_city_state_zip",
    "insurance_id","insurance_type","ins_dob_mm","ins_dob_dd","ins_dob_yy","ins_sex",
    "other_insurance_name","other_ins_policy","medicaid_resub",
    # Auth & Signatures
    "ins_signature","pt_signature","pt_date","ins_signature_date","assignment","prior_auth",
    # Illness & Accident
    "cur_ill_mm","cur_ill_dd","cur_ill_yy","sim_ill_mm","sim_ill_dd","sim_ill_yy",
    "work_mm_from","work_dd_from","work_yy_from","work_mm_end","work_dd_end","work_yy_end",
    "hosp_mm_from","hosp_dd_from","hosp_yy_from","hosp_mm_end","hosp_dd_end","hosp_yy_end",
    "pt_auto_accident","accident_place","other_accident",
    # Referring Provider
    "ref_physician","id_physician","physician number 17a","physician number 17a1",
    # Services & Diagnosis (line 1)
    "lab","place1","emg1",
    "sv1_mm_from","sv1_dd_from","sv1_yy_from","sv1_mm_end","sv1_dd_end","sv1_yy_end",
    "cpt1","mod1","diag1","ch1","day1",
    # Billing & Facility
    "tax_id","pt_account","t_charge","amt_paid",
    "physician_signature","physician_date",
    "service_facility_name","fac_street","fac_location",
    "billing_provider_name","doc_street","doc_name","doc_location","doc_phone area","doc_phone",
    "pin","grp"
]

def filter_fhir_bundle_for_lines(bundle: dict) -> dict:
    """Extract all service line details for each item in the claim."""
    service_lines = []
    claim = None
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Claim":
            claim = resource
            break
    if not claim:
        return {"service_lines": []}
    for item in claim.get("item", []):
        line = {
            "date_from": item.get("servicedPeriod", {}).get("start"),
            "date_to": item.get("servicedPeriod", {}).get("end"),
            "place_of_service": item.get("placeOfService"),
            "emg": item.get("emg"),
            "cpt": item.get("productOrService", {}).get("coding", [{}])[0].get("code"),
            "modifier": item.get("modifier", ""),
            "diagnosis_pointer": item.get("diagnosisPointer", []),
            "charge": item.get("unitPrice", {}).get("value"),
            "days_or_units": item.get("daysOrUnits"),
            "provider_npi": item.get("provider", {}).get("npi")
        }
        service_lines.append(line)
    return {"service_lines": service_lines}

def extract_with_llm(bundle_json_path: str) -> dict:
    """Call OpenAI to extract exactly FIELD_KEYS from the FHIR bundle."""
    bundle = json.load(open(bundle_json_path))
    prompt = (
        "You are a medical billing assistant. "
        "Given this FHIR bundle (in JSON), extract the following CMS-1500 fields "
        "and return a JSON object whose keys are exactly:\n"
        f"{FIELD_KEYS}\n"
        "Use these formats:\n"
        "- Dates split as MM, DD, YY (two digits)\n"
        "- Sex as 'M' or 'F'\n"
        "- Checkbox fields as 'Yes' or 'No'\n"
        "- Charges with two decimals\n"
        "- Phone as 'NNN-NNNN', SSN as 'XXX-XX-XXXX'\n\n"
        "FHIR Bundle:\n"
        f"{json.dumps(bundle, indent=2)}\n\n"
        "Output only the JSON."
    )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You extract structured data."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    extracted = json.loads(resp.choices[0].message.content)
    return extracted

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

def map_service_lines_to_pdf_fields(service_lines_dict):
    """Map service line data to CMS-1500 PDF field keys for each line."""
    pdf_fields = {}
    lines = service_lines_dict.get("service_lines", [])
    for idx, line in enumerate(lines, 1):
        if idx > 6:
            break
        if line.get("date_from"):
            try:
                dt = line["date_from"].split("T")[0].split("-")
                pdf_fields[f"sv{idx}_mm_from"] = dt[1]
                pdf_fields[f"sv{idx}_dd_from"] = dt[2]
                pdf_fields[f"sv{idx}_yy_from"] = dt[0][2:]
            except Exception:
                pdf_fields[f"sv{idx}_mm_from"] = ""
                pdf_fields[f"sv{idx}_dd_from"] = ""
                pdf_fields[f"sv{idx}_yy_from"] = ""
        if line.get("date_to"):
            try:
                dt = line["date_to"].split("T")[0].split("-")
                pdf_fields[f"sv{idx}_mm_end"] = dt[1]
                pdf_fields[f"sv{idx}_dd_end"] = dt[2]
                pdf_fields[f"sv{idx}_yy_end"] = dt[0][2:]
            except Exception:
                pdf_fields[f"sv{idx}_mm_end"] = ""
                pdf_fields[f"sv{idx}_dd_end"] = ""
                pdf_fields[f"sv{idx}_yy_end"] = ""
        pdf_fields[f"place{idx}"] = line.get("place_of_service", "")
        pdf_fields[f"emg{idx}"] = line.get("emg", "")
        pdf_fields[f"cpt{idx}"] = line.get("cpt", "")
        pdf_fields[f"mod{idx}"] = line.get("modifier", "")
        diag_ptr = line.get("diagnosis_pointer", [])
        if isinstance(diag_ptr, list):
            pdf_fields[f"diag{idx}"] = ",".join(str(d) for d in diag_ptr)
        else:
            pdf_fields[f"diag{idx}"] = str(diag_ptr)
        charge = line.get("charge")
        if charge is not None:
            pdf_fields[f"ch{idx}"] = f"{float(charge):.2f}"
        else:
            pdf_fields[f"ch{idx}"] = ""
        pdf_fields[f"day{idx}"] = str(line.get("days_or_units", ""))
    return pdf_fields

def main(bundle_json_path=None):
    if bundle_json_path is None:
        if len(sys.argv) != 2:
            print("Usage: python3 llm_workflow.py <FirstName_LastName>.json")
            sys.exit(1)
        bundle_json_path = sys.argv[1]
    
    with open(bundle_json_path) as f:
        bundle = json.load(f)
    print("Extracting all CMS-1500 fields from FHIR bundle via LLM…")
    llm_data = extract_with_llm(bundle_json_path)

    print("LLM Extracted fields:")
    print(json.dumps(llm_data, indent=2))

    service_lines = filter_fhir_bundle_for_lines(bundle)
    print("Extracted service lines:")
    print(json.dumps(service_lines, indent=2))

    service_line_fields = map_service_lines_to_pdf_fields(service_lines)
    merged_data = dict(llm_data)
    merged_data.update(service_line_fields)
    input_base = os.path.splitext(os.path.basename(bundle_json_path))[0]
    output_pdf = f"FILLED_{input_base}.pdf"
    
    fill_pdf("form-cms1500.pdf", merged_data, output_pdf)
    print("Done!", output_pdf)
    
    # Return the output PDF path when called programmatically
    if bundle_json_path is not None:
        return output_pdf

if __name__ == "__main__":
    main() 