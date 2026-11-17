# RCM Control Frameworks Reference

## Risk Categories (COSO ERM)
| Code | Category | Description |
|------|----------|-------------|
| OPS  | Operational | Risks arising from people, processes, systems, or external events |
| IT   | IT | Risks arising from applications, infrastructure, cyber threats, or unreliable technology-enabled controls |
| FR   | Financial | Risks of material misstatement in financial statements or financial loss |
| COMP | Compliance | Risks of violating laws, regulations, or internal policies |
| FRAUD| Fraud | Risks of intentional manipulation, override, collusion, or misappropriation |
| STRAT| Strategic | Risks that threaten the achievement of high-level organizational objectives |

## Control Execution Types
| Type | Description | Example |
|------|-------------|---------|
| Manual | Performed by a person without system enforcement | Manager review and sign-off |
| IT-Dependent | Relies on IT system output but requires human judgment | Exception report review |
| Automated | Enforced entirely by the IT system with no human step | System access restriction |

## Control Nature
| Nature | Purpose | Timing |
|--------|---------|--------|
| Preventive | Stops the risk event from occurring | Before the event |
| Detective | Identifies that a risk event has occurred | After the event |

## Control Significance
| Level | Criteria |
|-------|----------|
| Key | Directly addresses a significant risk; failure would likely result in a material misstatement or significant operational loss |
| Non-Key | Supplementary; failure alone would not cause material impact |

## ITGC Dependency Types (COBIT)
| Type | Description |
|------|-------------|
| Access | Controls over logical access to systems, data, and programs |
| Change | Controls over changes to systems and programs (SDLC/change management) |
| Operations | Controls over IT operations: batch jobs, backups, incident management |

## IPE Reliability Levels
| Level | Criteria |
|-------|----------|
| Strong | Report/data is system-generated, not editable, with version control and reconciliation |
| Moderate | System-generated but can be exported/modified; some reconciliation exists |
| Weak | Manually prepared or heavily modified after export; limited reconciliation |
| None | No supporting evidence of data integrity; IPE not validated |

## Inherent Risk Score Matrix
|             | Impact 1 | Impact 2 | Impact 3 | Impact 4 | Impact 5 |
|-------------|----------|----------|----------|----------|----------|
| Likelihood 5| 5        | 10       | 15       | 20       | 25       |
| Likelihood 4| 4        | 8        | 12       | 16       | 20       |
| Likelihood 3| 3        | 6        | 9        | 12       | 15       |
| Likelihood 2| 2        | 4        | 6        | 8        | 10       |
| Likelihood 1| 1        | 2        | 3        | 4        | 5        |

## Design Effectiveness Reduction
| Design Effectiveness | Reduction Factor |
|---------------------|-----------------|
| Strong | 0.60 |
| Moderate | 0.35 |
| Weak | 0.15 |

## Residual Risk Reduction by Control Reliability
| Control Reliability | Reduction Factor |
|--------------------|-----------------|
| Reliable | 0.60 |
| Partially Reliable | 0.35 |
| Unreliable | 0.15 |
| Not Assessed | 0.00 |
