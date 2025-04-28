#!/usr/bin/env python3
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

# 1) Your fake_data dict (as defined earlier)
fake_data = {
    # Patient Demographics (Boxes 1–13)
    "pt_name":                "Smith, John A",
    "birth_mm":               "07",
    "birth_dd":               "23",
    "birth_yy":               "85",
    "sex":                    "M",
    "pt_street":              "123 Oak Ave",
    "pt_city":                "Springfield",
    "pt_state":               "IL",
    "pt_zip":                 "62704",
    "pt_AreaCode":            "217",
    "pt_phone":               "123-4567",
    "ssn":                    "123-45-6789",
    "rel_to_ins":             "Self",

    # Insurance Information (Boxes 14–33)
    "insurance_name":         "Acme Health Plan",
    "insurance_address":      "PO Box 567",
    "insurance_address2":     "Suite 100",
    "insurance_city_state_zip":"Springfield, IL 62704",
    "insurance_id":           "ABC123456",
    "insurance_type":         "Group",
    "ins_dob_mm":             "01",
    "ins_dob_dd":             "15",
    "ins_dob_yy":             "70",
    "ins_sex":                "F",
    "other_insurance_name":   "Secondary Health",
    "other_ins_policy":       "SEC7891011",
    "medicaid_resub":         "Yes",

    # Authorization & Signatures
    "ins_signature":          "Jane Doe",
    "pt_signature":           "John A Smith",
    "pt_date":                "07/23/23",
    "ins_signature_date":     "07/24/23",
    "assignment":             "Yes",
    "prior_auth":             "PA123456",

    # Condition Onset & Accident
    "cur_ill_mm":             "06",
    "cur_ill_dd":             "01",
    "cur_ill_yy":             "23",
    "sim_ill_mm":             "06",
    "sim_ill_dd":             "01",
    "sim_ill_yy":             "23",
    "work_mm_from":           "06",
    "work_dd_from":           "01",
    "work_yy_from":           "23",
    "work_mm_end":            "06",
    "work_dd_end":            "05",
    "work_yy_end":            "23",
    "hosp_mm_from":           "06",
    "hosp_dd_from":           "02",
    "hosp_yy_from":           "23",
    "hosp_mm_end":            "06",
    "hosp_dd_end":            "03",
    "hosp_yy_end":            "23",
    "pt_auto_accident":       "No",
    "accident_place":         "Highway",
    "other_accident":         "No",

    # Referring Provider (Box 17)
    "ref_physician":          "Dr. Alice Brown",
    "id_physician":           "1234567890",
    "physician number 17a":   "1234567890",
    "physician number 17a1":  "0987654321",

    # Service & Diagnosis (Boxes 24A–H)
    "lab":                    "No",
    "place1":                 "11",
    "emg1":                   "0",
    "sv1_mm_from":            "06",
    "sv1_dd_from":            "01",
    "sv1_yy_from":            "23",
    "sv1_mm_end":             "06",
    "sv1_dd_end":             "01",
    "sv1_yy_end":             "23",
    "cpt1":                   "99213",
    "mod1":                   "25",
    "diag1":                  "E11.9",
    "ch1":                    "150.00",
    "day1":                   "1",

    # Billing Provider & Facility
    "tax_id":                 "12-3456789",
    "pt_account":             "ACCT1234",
    "t_charge":               "150.00",
    "amt_paid":               "0.00",
    "physician_signature":    "Jane Doe",
    "physician_date":         "07/28/23",
    "service_facility_name":  "General Hospital",
    "fac_street":             "456 Elm St",
    "fac_location":           "Springfield, IL 62704",
    "billing_provider_name":  "Acme Billing Services",
    "doc_street":             "789 Oak St",
    "doc_name":               "Acme Billing Services",
    "doc_location":           "Springfield, IL 62704",
    "doc_phone area":         "217",
    "doc_phone":              "555-7890",
    "pin":                    "123456",
    "grp":                    "G789"
}
# 1) Load and clone everything (incl. form)
reader = PdfReader("form-cms1500.pdf")
writer = PdfWriter()
writer.clone_document_from_reader(reader)

# 2) Fill fields
for page in writer.pages:
    writer.update_page_form_field_values(page, fake_data)

# 3) Tell viewers to regenerate appearances
writer._root_object[NameObject("/AcroForm")][NameObject("/NeedAppearances")] = BooleanObject(True)

# 4) Save
with open("filled_with_appearances.pdf", "wb") as f:
    writer.write(f)
print("Done — open in Adobe Reader to see your filled form.")
