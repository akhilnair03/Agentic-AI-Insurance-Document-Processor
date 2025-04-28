# Virtual Medical Biller

## System Overview
This project builds an **Agentic Virtual Medical Biller** that:
- Extracts clinical and insurance information from **raw clinical notes**.
- Extracts ground-truth information from **structured FHIR/Synthea JSON**.
- **Fills CMS-1500 insurance claim forms**


The system has two implementations:
1. A basic implementation using OpenAI's GPT-4
2. An enhanced agentic AI implementation using LangChain OpenAIagents

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Download the CMS-1500 form template:
- Place a PDF template of the CMS-1500 form named `form-cms1500.pdf` in the root directory
- The template should have form fields that match the field names in the code

3. Set up environment variables:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Running the Basic Implementation (llm_workflow.py)

The basic implementation uses OpenAI's GPT-4 to extract and process the data:

### Single Patient Processing
```bash
python llm_workflow.py path/to/your/fhir_bundle.json
```

This will:
1. Extract CMS-1500 fields from the FHIR bundle using GPT-4
2. Fill the CMS-1500 PDF form
3. Save the output as `FILLED_[patient_name].pdf`

### Batch Processing
To process multiple patients at once:

1. Place all FHIR bundle JSON files in the `patient_data` directory
2. Run the batch processor:
```bash
python batch_process.py
```

This will:
1. Process all JSON FHIR bundle files in the `patient_data` directory
2. Create a `filled_patient_data` directory if it doesn't exist
3. Generate filled PDFs for each patient
4. Save outputs as `filled_patient_data/Filled_[patient_id].pdf`

### Basic Implementation Workflow
```plaintext
[Input: FHIR Bundle JSON]
         |
         v
[Extract Fields via GPT-4]
         |
         v
[Filter FHIR Bundle for Service Lines]
         |
         v
[Map Service Lines to PDF Fields]
         |
         v
[Merge Extracted and Service Line Data]
         |
         v
[Fill CMS-1500 PDF]
         |
         v
[Save as FILLED_[patient_name].pdf]
```

## Running the Agentic Implementation (agentic_process.py)

The enhanced implementation uses LangChain agents for more sophisticated processing:

```bash
python agentic_process.py
```

This will:
1. Load a sample FHIR bundle from `synthea/output/fhir/`
2. Use multiple specialized agents to:
   - Extract raw data from clinical notes
   - Extract structured ground truth data
   - Fill both PDF forms
   - Generate a comparison report
3. Save outputs in the `filled_pdfs/` directory

### Agentic Implementation Workflow
```plaintext
[Input: FHIR Bundle JSON]
         |
         v
[Initialize Agent State]
         |
         v
[Agentic Controller]
  |           |
  v           v
[RawExtractionAgent]   [GroundTruthAgent]
  |                       |
  v                       v
[Fill Raw PDF]        [Fill Ground Truth PDF]
  |                       |
  \_______________________/
            |
            v
[Compare Forms]
            |
            v
[Generate CSV Report]
```

## Output Files

Implementations will generate:
- `filled_pdfs/raw_extraction_filled_cms1500.pdf` - Form filled with raw extraction
- `filled_pdfs/ground_truth_filled_cms1500.pdf` - Form filled with ground truth
- `comparison_report.csv` - Comparison between raw and ground truth data

## Notes

- The basic LLM implementation uses OpenAI's GPT-4 model
- The agentic implementation uses GPT-3.5-turbo with LangChain agents
- The FHIR bundle should contain a DiagnosticReport resource with the clinical note
- The output PDFs will be saved in the `filled_pdfs` directory

---

