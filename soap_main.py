from transcribe.soap_generator import generate_soap_note
import json

with open("medical_analysis_results_1759299516.json") as f:
    encounter = json.load(f)

soap = generate_soap_note(encounter)

print(json.dumps(soap, indent=2))

# Save SOAP note to file
with open("soap_output.json", "w") as f:
    json.dump(soap, f, indent=2)

print("SOAP note saved to soap_output.json")