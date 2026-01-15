# Expert Commentary: Pediatric Opioid Overdose Case

> **Commentators**: Kristine Markham, PharmD, BCPPS; Maki Usui, PharmD, BCPPS; Cady Smith, BA
> **Institution**: UC Davis Health
> **Published**: February 26, 2025
> **Source**: [AHRQ PSNet](https://psnet.ahrq.gov/web-mm/pain-relief-risk-case-suspected-opioid-overdose-pediatric-patient)

---

## Background Knowledge

### Pediatric Postoperative Pain Management Principles

1. **Multimodal approach** is recommended
2. **First-line agents**: Acetaminophen and NSAIDs (non-opioid)
3. **Opioids**: Should be prescribed at lowest effective doses for shortest necessary duration
4. **Evidence**: Rectal acetaminophen during surgery decreased opioid use without adverse events

### Current Guidelines

- Opioid prescriptions should be limited to **3-7 days** in opioid-naïve patients
- Postoperative prescriptions are the **most common source of excess opioids** in homes
- Comprehensive perioperative education is essential

---

## Expert Problem Identification

### Issues in This Case

| Issue | Details |
|-------|---------|
| **Initial prescription** | 5-day hydrocodone-acetaminophen was appropriate per guidelines |
| **ED prescription change** | Oxycodone dose at **upper end of range** (0.2 mg/kg/dose) for opioid-naïve patient |
| **Overlapping supply** | Original prescription may still have been in home → ~10-day supply of multiple agents |
| **Documentation gap** | Caregiver education on opioid safety was **not documented** |
| **Missing naloxone** | No prescription for naloxone on either occasion |

### Suspected Contributing Factors

1. **Dose stacking** - Inadvertent administration of multiple opioid formulations
2. **Opioid polypharmacy** - Multiple agents available in home
3. **Lack of education** - Family may not have understood risks

---

## Expert Recommendations

### 1. EHR System Optimization

| Intervention | Description | Evidence |
|--------------|-------------|----------|
| Pain management order sets | Clinical decision support for appropriate dosing/duration | Reduces over-prescribing |
| Low default dose values | Setting default to 12 doses | Decreased overall opioid prescribing without affecting pain control |
| Naloxone co-prescribing alert | BPA triggered by new opioid prescriptions | One hospital reported **28-fold increase** in naloxone co-prescribing |

### 2. Dose Stacking Prevention

| Measure | Details |
|---------|---------|
| PDMP check | Query state Prescription Drug Monitoring Program before prescribing |
| Robust education | When prescribing sedating medications in succession |
| Disposal instructions | When changing opioid formulation, educate on stopping and disposing of initial prescription |
| Ingredient awareness | Ensure understanding of combination medication ingredients |

### 3. Widespread Naloxone Dispensing

- 2017-2022: >50,000 naloxone prescriptions for ages 10-19
- March 2023: FDA approved first OTC naloxone nasal spray
- All states allow pharmacy dispensing of naloxone

---

## Take-Home Points (Expert Summary)

1. **Education is critical** - All caregivers of pediatric patients receiving opioid prescriptions should receive safety education on:
   - Adverse effects
   - Appropriate dosing
   - Medication storage

2. **Limit supply** - Postoperative opioid use should be limited to:
   - 3-7 day supply
   - Single agent
   - Purpose: Decrease home opioid availability, mitigate adverse effects

3. **EHR decision support** - Systems should:
   - Guide safe opioid prescribing
   - Alert providers to consider naloxone at discharge

4. **Naloxone prescribing and education** - Can:
   - Increase outpatient naloxone availability
   - Enhance caregiver understanding of emergency administration

---

## Expected RCA Classification

### 6M Fishbone Analysis

| Category | Contributing Factors |
|----------|---------------------|
| **Personnel** | Physician did not document/provide education; Did not consider naloxone |
| **Process** | No standardized medication change workflow; No PDMP query |
| **Equipment** | EHR lacks naloxone co-prescribing alert |
| **Environment** | ED workload and time pressure |
| **Material** | Original prescription not retrieved; Multiple medications in home |
| **Monitoring** | No post-discharge follow-up mechanism for high-risk prescriptions |

### HFACS Classification

| Level | Code | Factor |
|-------|------|--------|
| Unsafe Acts | UA-DV | Decision Violation - Not prescribing naloxone when indicated |
| Preconditions | PC-PPP | Patient Physical/Physiological Problems - 2-year-old cannot self-report symptoms |
| Unsafe Supervision | US-SV | Supervisory Violation - No standardized education protocol |
| Organizational Influences | OI-OP | Organizational Process - No EHR alert system |

### 5-Why Analysis

```text
Problem: 2-year-old male suspected opioid overdose death

Why 1: Why did opioid overdose occur?
→ Likely simultaneous administration of two opioid medications (dose stacking)

Why 2: Why were two medications taken simultaneously?
→ No instruction to stop/dispose of original prescription when medication was changed

Why 3: Why was there no instruction?
→ Caregiver education not documented, possibly not provided

Why 4: Why was education not provided?
→ No standardized education workflow; ED time pressure

Why 5: Why is there no standardized workflow?
→ Organizational level: No pediatric opioid prescribing safety policy established
   ★ ROOT CAUSE - Organizational Influences
```

### Key Improvement Recommendations

1. **EHR System**: Implement naloxone co-prescribing BPA alert
2. **Process Standardization**: Create pediatric opioid prescribing checklist
3. **Mandatory Education**: Require education completion before discharge workflow completion
4. **PDMP Integration**: Require query before prescribing

---

## References

1. Kelley-Quon LI, et al. Guidelines for Opioid Prescribing in Children and Adolescents After Surgery. JAMA Surg. 2021;156(1):76-90.
2. Cravero JP, et al. The Society of Pediatric Anesthesia recommendations for opioids in children. Paediatr Anaesth. 2019;26(6):547-571.
3. Dowell D, et al. CDC Clinical Practice Guideline for Prescribing Opioids for Pain. MMWR Recomm Rep. 2022;71(3):1-95.
4. FDA Drug Safety Communication: Naloxone prescribing recommendations. September 2024.
5. Nelson SD, et al. Assessment of a naloxone coprescribing alert. Anesth Analg. 2022;135(1):26-34.
