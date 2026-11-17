# Subcontracting Chain and Third-Party Risk Management

Use this framework for every assessment. It covers how the assessed entity manages its own suppliers and subcontractors (sub-outsourcing), and whether obligations are passed down the chain. Control IDs below are for use in findings.

Review status: drafted from general knowledge of the cited sources. Have a domain expert verify article numbers and thresholds before use on a client engagement.

## Sources
- DORA (Regulation (EU) 2022/2554), Articles 28, 29 and 30
- DORA RTS on subcontracting ICT services supporting critical or important functions (Commission Delegated Regulation (EU) 2025/532)
- NIS2 (Directive (EU) 2022/2555), Article 21(2)(d) and 21(3)
- ISO/IEC 27001:2022 Annex A, A.5.19 to A.5.23
- BIO2 supplier requirements (Dutch government)

## Controls

### SUB-01 Inventory of subcontractors (DORA Art.28(3), ISO A.5.19)
The entity has a current register of its suppliers and subcontractors, with the service each provides, the data processed, the location of processing and whether it supports a critical or important function.

### SUB-02 Subcontractors disclosed (DORA Art.30(2)(a), Art.30(3), RTS 2025/532)
The contract or the documents name the subcontractors that support the service, or state the conditions under which subcontracting is permitted (prior notice, right to object, change notification).

### SUB-03 Risk assessment and due diligence on subcontractors (DORA Art.28(4), NIS2 Art.21(3), ISO A.5.19, A.5.21)
The entity assesses the risk of its subcontractors before engagement and periodically, including each direct supplier's vulnerabilities and the quality of its security practices.

### SUB-04 Flow-down of requirements (DORA Art.30, ISO A.5.20, BIO2)
Security, confidentiality, incident reporting, audit and access rights, data location and exit requirements that apply to the assessed entity are passed on contractually to its subcontractors. For Dutch government work, BIO2 requirements are included.

### SUB-05 Monitoring of subcontractors (ISO A.5.22, DORA Art.28)
The entity monitors subcontractor performance and changes: review of assurance reports, SLA reporting, incident notification from subcontractors, change management of supplier services.

### SUB-06 Incident notification along the chain (NIS2 Art.21(2)(b), Art.23, DORA Art.19)
Incidents at a subcontractor are notified to the entity fast enough for the entity to meet its own reporting deadlines (NIS2: 24h early warning; DORA: 4h after classification as major, 24h after detection at the latest).

### SUB-07 Concentration and dependency (DORA Art.29)
The entity has identified concentration risk: reliance on one subcontractor for several services, or several services running on the same hyperscaler or location.

### SUB-08 Exit and substitutability (DORA Art.28(8), Art.30(3)(f))
Exit plans exist for critical subcontractors and cover data return, transition period and alternative providers.

### SUB-09 Assurance coverage of subcontractors (ISAE 3402 / SOC 2, ISO A.5.22)
Assurance reports or certificates cover the subcontractors that matter. See the evidence checks below.

## Evidence checks for assurance reports (SOC 1, SOC 2, ISAE 3402) and certificates
Report these as findings under SUB-09 when relevant:
- The scope of the report or certificate covers the service, locations and system the client actually uses. If not, status Partial or Gap.
- The auditor opinion is unqualified. A qualified or adverse opinion, or exceptions in tested controls, is a finding.
- Subservice organizations: the report states whether they are carved out (their controls are excluded) or included (inclusive method). With carve-out, ask for the subservice organization's own report. Name each subservice organization found.
- Complementary user entity controls (CUECs): list them and note whether evidence shows the client has implemented them. If there is no evidence, say so. CUECs are the client's responsibility and are a frequent gap.
- Gap between the end of the report period and today: a bridge letter or equivalent is expected. Currency thresholds are in document_validity_rules.

## Role of the assessed entity
- Client assessed itself (self-assessment): assess how the client manages its suppliers (SUB-01 to SUB-09 as the contracting party).
- Vendor or supplier of the client: assess how the vendor manages its own subcontractors and what flows down to them.
- Subcontractor (fourth party) of the client: assess it as a vendor, and add whether the client knows about it (SUB-02), has flow-down in place (SUB-04) and has assurance (SUB-09). The client's own documents are the evidence for the client side.
