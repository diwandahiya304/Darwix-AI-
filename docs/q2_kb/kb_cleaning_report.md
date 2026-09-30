# KB Cleaning Report

_Generated: 2026-09-30T11:13:00.846296+00:00_

## Summary

- Documents in: 20
- Chunks out: 54
- Exact duplicates removed: 0
- Near-duplicates removed: 1
- Extraction failures flagged: 1
- Records containing PII: 11
- Records versioned this run: 0

## PII found (by type)

| Type | Count |
|---|---|
| AADHAAR | 2 |
| EMAIL | 3 |
| PAN | 2 |
| PERSON | 2 |
| PHONE | 2 |

## Before / After Examples

### Example 1 -- `25062bf54e9fc77d`

_category=eligibility_qualification, source_type=form, language=en, pii=True_

**Before:**
```
SYNTHETIC TEST DATA -- fabricated eligibility form, no real customer data.
Health Insurance Eligibility Form
Applicant Name: Sunita Rao
Contact Phone: 9123456780
Email Address: sunita.rao@example.com
PAN Number: BXPRA5678K
Aadhaar Number: 9876-5432-1098
Date Of Birth: 12-08-1990
Qualification Rules: Applicant must be between 18 and 65 years old with no declined claims in the last 3
years.
```

**After:**
```
SYNTHETIC TEST DATA -- fabricated eligibility form, no real customer data.
Health Insurance Eligibility Form
Applicant Name: [PERSON]: [PHONE]
Email Address: [EMAIL]
PAN Number: [PAN]
Aadhaar Number: [AADHAAR]
Date Of Birth: 1990-08-12
Qualification Rules: Applicant must be between 18 and 65 years old with no declined claims in the last 3
years.
```

### Example 2 -- `780b1809e1291d28`

_category=compliance_disclosure, source_type=website, language=fil, pii=False_

**Before:**
```
# Compliance Disclosure Requirements

Dapat ipaalam sa customer sa simula ng tawag na ito po ay nire-record para sa quality assurance at training purposes.

Dapat munang kumpirmahin ang pagkakakilanlan ng customer, tulad ng buong pangalan at petsa ng kapanganakan o policy number, bago talakayin ang anumang detalye ng kanilang policy.

Bawal pong ibahagi ang detalye ng policy, halaga ng premium, o katayuan ng bayad sa ibang tao maliban sa may-ari mismo ng account o sa awtorisadong kinatawan nito, alinsunod sa Data Privacy Act.

Kung tatanggihan po ng customer na tumuloy sa tawag o magbigay ng k
```

**After:**
```
# Compliance Disclosure Requirements
Dapat ipaalam sa customer sa simula ng tawag na ito po ay nire-record para sa quality assurance at training purposes.
Dapat munang kumpirmahin ang pagkakakilanlan ng customer, tulad ng buong pangalan at petsa ng kapanganakan o policy number, bago talakayin ang anumang detalye ng kanilang policy.
Bawal pong ibahagi ang detalye ng policy, halaga ng premium, o katayuan ng bayad sa ibang tao maliban sa may-ari mismo ng account o sa awtorisadong kinatawan nito, alinsunod sa Data Privacy Act.
Kung tatanggihan po ng customer na tumuloy sa tawag o magbigay ng karag
```

### Example 3 -- `1f6f750c3f03b4ba`

_category=compliance_disclosure, source_type=website, language=id, pii=False_

**Before:**
```
# Compliance Disclosure OJK Conduct

Petugas penagihan dilarang mengancam, mempermalukan, atau menggunakan kata-kata kasar kepada nasabah dalam bentuk apa pun, baik secara langsung maupun tersirat.

Petugas dilarang mengungkapkan informasi tunggakan atau utang nasabah kepada pihak ketiga yang tidak berwenang, termasuk keluarga, tetangga, rekan kerja, atau atasan nasabah.

Penagihan hanya boleh dilakukan pada pukul 08.00 sampai 20.00 waktu setempat nasabah, dan tidak boleh dilakukan pada hari libur nasional kecuali disetujui oleh nasabah.

Setiap petugas penagihan wajib menyebutkan identitas re
```

**After:**
```
# Compliance Disclosure OJK Conduct
Petugas penagihan dilarang mengancam, mempermalukan, atau menggunakan kata-kata kasar kepada nasabah dalam bentuk apa pun, baik secara langsung maupun tersirat.
Petugas dilarang mengungkapkan informasi tunggakan atau utang nasabah kepada pihak ketiga yang tidak berwenang, termasuk keluarga, tetangga, rekan kerja, atau atasan nasabah.
Penagihan hanya boleh dilakukan pada pukul 08.00 sampai 20.00 waktu setempat nasabah, dan tidak boleh dilakukan pada hari libur nasional kecuali disetujui oleh nasabah.
Setiap petugas penagihan wajib menyebutkan identitas resmi 
```

