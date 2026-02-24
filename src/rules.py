"""Deterministic rule engine for claim completeness and risk triage.

This module contains auditable, non-LLM business rules used by the agent:
1) completeness checks for mandatory/preferred fields
2) keyword-based medical risk flagging
"""

# Diagnoses that should strongly trigger underwriting review.
HIGH_RISK_DIAGNOSES = [
    "cancer",
    "carcinoma",
    "malignant",
    "tumor",
    "leukaemia",
    "leukemia",
    "heart failure",
    "myocardial infarction",
    "stroke",
    "cerebrovascular",
    "hiv",
    "aids",
    "cirrhosis",
    "renal failure",
    "kidney failure",
    "aortic aneurysm",
    "pulmonary embolism",
    "psychosis",
    "schizophrenia",
]

# Medications that indicate elevated underwriting risk.
HIGH_RISK_MEDICATIONS = [
    "chemotherapy",
    "warfarin",
    "clozapine",
    "lithium",
    "methotrexate",
    "tacrolimus",
    "insulin",
    "morphine",
    "oxycodone",
    "fentanyl",
]

# Diagnoses that are relevant but not always immediate decline/refer triggers.
MODERATE_RISK_DIAGNOSES = [
    "hypertension",
    "diabetes",
    "angina",
    "atrial fibrillation",
    "asthma",
    "depression",
    "anxiety",
    "sleep apnea",
    "obesity",
]


def check_completeness(entities: dict, issues: dict) -> dict:
    """Compute a structured completeness report for triage decisions.

    Args:
        entities: Extracted entity dictionary from document parsing.
        issues: Extraction issue dictionary (quality flags and missing fields).

    Returns:
        Dict including present/missing mandatory and preferred fields, a
        completeness score (0-100), and readiness for decision.
    """
    required_for_decision = {
        "patient_name": "Patient full name",
        "dob": "Date of birth",
        "report_date": "Report / examination date",
        "provider_name": "Treating provider or clinic name",
    }
    preferred = {
        "diagnoses": "At least one diagnosis",
        "medications": "Medication list (if applicable)",
    }

    result = {
        "mandatory_present": [],
        "mandatory_missing": [],
        "preferred_present": [],
        "preferred_missing": [],
        "quality_flags": issues.get("data_quality_flags", []),
        "completeness_score": 0,
        "ready_for_decision": False,
    }

    for field, label in required_for_decision.items():
        if entities.get(field):
            result["mandatory_present"].append(label)
        else:
            result["mandatory_missing"].append(label)

    for field, label in preferred.items():
        if entities.get(field):
            result["preferred_present"].append(label)
        else:
            result["preferred_missing"].append(label)

    total = len(required_for_decision) + len(preferred)
    present = len(result["mandatory_present"]) + len(result["preferred_present"])
    result["completeness_score"] = round(100 * present / total)
    result["ready_for_decision"] = len(result["mandatory_missing"]) == 0
    return result


def assess_medical_risk(entities: dict) -> dict:
    """Assign a risk level from extracted diagnoses and medications.

    Args:
        entities: Extracted entity dictionary containing diagnoses/medications.

    Returns:
        Dict containing risk level, specific risk flags, and flag count.
    """
    risk_flags = []
    risk_level = "low"

    diagnoses_text = " ".join(d.get("name", "").lower() for d in entities.get("diagnoses", []))
    meds_text = " ".join(m.get("name", "").lower() for m in entities.get("medications", []))

    for term in HIGH_RISK_DIAGNOSES:
        if term in diagnoses_text:
            risk_flags.append(f"High-risk diagnosis keyword: '{term}'")
            risk_level = "high"

    for term in HIGH_RISK_MEDICATIONS:
        if term in meds_text:
            risk_flags.append(f"High-risk medication: '{term}'")
            if risk_level != "high":
                risk_level = "moderate"

    for term in MODERATE_RISK_DIAGNOSES:
        if term in diagnoses_text:
            risk_flags.append(f"Moderate-risk diagnosis keyword: '{term}'")
            if risk_level == "low":
                risk_level = "moderate"

    high_count = sum(1 for flag in risk_flags if "High-risk" in flag)
    mod_count = sum(1 for flag in risk_flags if "Moderate-risk" in flag)

    # Escalate if any high-risk hit is present or moderate findings accumulate.
    if high_count >= 1 or mod_count >= 3:
        risk_level = "refer_to_underwriter"

    return {
        "risk_level": risk_level,
        "risk_flags": risk_flags if risk_flags else ["No significant risk flags identified"],
        "flag_count": len(risk_flags),
    }
