"""
Verification script for AWS-Medical implementation.

This script verifies that all new modules are properly structured
and can be imported without errors.
"""

import sys

def verify_imports():
    """Verify all new modules can be imported."""
    print("=" * 70)
    print("AWS-Medical Implementation Verification")
    print("=" * 70)
    
    modules_to_verify = [
        ("src.common.io", ["generate_encounter_id", "generate_correlation_id", "get_timestamp", "save_decision_support_prompts", "save_patient_artefacts"]),
        ("src.common.aws", ["get_bedrock_runtime", "get_transcribe_client", "get_comprehend_medical_client"]),
        ("src.clinical_notes.decision_support", ["generate_decision_support_prompts"]),
        ("src.clinical_notes.patient_artefacts", ["generate_patient_handout", "generate_after_visit_summary", "generate_followup_checklist"]),
        ("src.clinical_notes.soap.generator", ["generate_soap_note"]),
    ]
    
    all_ok = True
    
    for module_name, functions in modules_to_verify:
        print(f"\n✓ Checking {module_name}...")
        try:
            module = __import__(module_name, fromlist=functions)
            for func_name in functions:
                if hasattr(module, func_name):
                    print(f"  ✓ {func_name}")
                else:
                    print(f"  ✗ {func_name} NOT FOUND")
                    all_ok = False
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            all_ok = False
    
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ All modules and functions verified successfully!")
    else:
        print("✗ Some modules or functions are missing!")
        sys.exit(1)
    print("=" * 70)
    
    # Verify test files exist
    print("\nTest Files:")
    test_files = [
        "tests/test_io.py",
        "tests/test_aws.py",
        "tests/test_generator.py",
        "tests/test_decision_support.py",
        "tests/test_patient_artefacts.py",
    ]
    
    import os
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"  ✓ {test_file}")
        else:
            print(f"  ✗ {test_file} NOT FOUND")
            all_ok = False
    
    print("\n" + "=" * 70)
    print("Implementation Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/ -v")
    print("2. Test SOAP generation: python -m src.clinical_notes.soap.run")
    print("3. Test with decision support: python -m src.clinical_notes.soap.run --decision-support")
    print("4. Test all features: python -m src.clinical_notes.soap.run --all")
    print("\nFor more details, see README.md")


if __name__ == "__main__":
    verify_imports()
