import os
import glob
from src.clinical_notes.soap.generator import generate_soap_note
from src.common.io import load_json, save_soap_note


def find_latest_medical_analysis(input_dir: str = "/workspaces/AWS-Medical/data/outputs") -> str:
    """
    Find the most recent medical analysis results file.
    
    Args:
        input_dir: Directory to search for analysis files
        
    Returns:
        Path to the most recent medical_analysis_results_*.json file
    """
    pattern = os.path.join(input_dir, "medical_analysis_results_*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    
    if not files:
        raise FileNotFoundError(f"No medical analysis results found in {input_dir}")
    
    return files[0]


def main():
    """Main workflow: Load medical analysis results and generate SOAP note."""
    
    # Find latest medical analysis results
    analysis_file = find_latest_medical_analysis()
    print(f"Loading medical analysis from: {analysis_file}")
    
    # Load encounter data
    encounter = load_json(analysis_file)
    
    # Extract IDs if they exist (for correlation)
    encounter_id = encounter.get('encounter_id')
    correlation_id = encounter.get('correlation_id')
    
    print(f"Generating SOAP note for encounter {encounter_id}")
    
    # Generate SOAP note
    soap = generate_soap_note(
        encounter_json=encounter,
        encounter_id=encounter_id,
        correlation_id=correlation_id
    )
    
    # Save SOAP note with dynamic naming and correlation IDs
    output_file = save_soap_note(
        soap_data=soap,
        encounter_id=encounter_id,
        correlation_id=correlation_id
    )
    
    print(f"SOAP note saved to: {output_file}")
    return output_file


if __name__ == "__main__":
    main()