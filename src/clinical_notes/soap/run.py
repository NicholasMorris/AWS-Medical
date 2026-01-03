from src.clinical_notes.soap.generator import generate_soap_note
from src.common.io import load_json, save_json

encounter = load_json("/workspaces/AWS-Medical/data/outputs/medical_analysis_results_1759299516.json")

soap = generate_soap_note(encounter)

# Save SOAP note to file
save_json(soap, "/workspaces/AWS-Medical/data/outputs/soap_output.json")

print("SOAP note saved to soap_output.json")