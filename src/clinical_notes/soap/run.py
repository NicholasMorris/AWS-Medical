import os
import glob
import argparse
from pathlib import Path
from typing import Optional
from src.clinical_notes.soap.generator import generate_soap_note
from src.clinical_notes.decision_support import generate_decision_support_prompts
from src.clinical_notes.patient_artefacts import (
    generate_patient_handout,
    generate_after_visit_summary,
    generate_followup_checklist
)
from src.common.io import (
    load_json, 
    save_soap_note,
    save_decision_support_prompts,
    save_patient_artefacts
)


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


def main(
    decision_support: bool = False,
    patient_artefacts: bool = False,
    analysis_file: Optional[str] = None,
):
    """
    Main workflow: Load medical analysis results and generate SOAP note.
    
    Args:
        decision_support: If True, generate "Did you consider?" prompts
        patient_artefacts: If True, generate patient handout, summary, and checklist
        analysis_file: Optional path to an existing medical analysis JSON file; if not
            provided, the latest result in data/outputs/ will be used.
    """

    if analysis_file:
        analysis_path = Path(analysis_file)
        if not analysis_path.exists():
            raise FileNotFoundError(f"Requested medical analysis file not found: {analysis_file}")
        analysis_file = str(analysis_path)
    else:
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
    soap_output = save_soap_note(
        soap_data=soap,
        encounter_id=encounter_id,
        correlation_id=correlation_id
    )
    
    print(f"SOAP note saved to: {soap_output}")
    
    # Generate decision support prompts if requested
    if decision_support:
        print("Generating decision support prompts...")
        prompts = generate_decision_support_prompts(
            encounter_json=encounter,
            encounter_id=encounter_id
        )
        
        ds_output = save_decision_support_prompts(
            prompts_data=prompts,
            encounter_id=encounter_id,
            correlation_id=correlation_id
        )
        
        print(f"Decision support prompts saved to: {ds_output}")
    
    # Generate patient artefacts if requested
    if patient_artefacts:
        print("Generating patient artefacts (handout, summary, checklist)...")
        
        handout = generate_patient_handout(
            encounter_json=encounter,
            encounter_id=encounter_id
        )
        
        summary = generate_after_visit_summary(
            encounter_json=encounter,
            encounter_id=encounter_id
        )
        
        checklist = generate_followup_checklist(
            encounter_json=encounter,
            encounter_id=encounter_id
        )
        
        # Combine all artefacts
        all_artefacts = {
            **handout,
            **summary,
            **checklist
        }
        
        pa_output = save_patient_artefacts(
            artefacts_data=all_artefacts,
            encounter_id=encounter_id,
            correlation_id=correlation_id
        )
        
        print(f"Patient artefacts saved to: {pa_output}")
    
    return soap_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SOAP notes and optional clinical artefacts")
    parser.add_argument(
        "--decision-support",
        action="store_true",
        help="Generate 'Did you consider?' decision support prompts"
    )
    parser.add_argument(
        "--patient-artefacts",
        action="store_true",
        help="Generate patient handout, after-visit summary, and follow-up checklist"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all outputs (SOAP, decision support, patient artefacts)"
    )
    
    args = parser.parse_args()
    
    # If --all is specified, enable both options
    decision_support = args.decision_support or args.all
    patient_artefacts = args.patient_artefacts or args.all
    
    main(decision_support=decision_support, patient_artefacts=patient_artefacts)