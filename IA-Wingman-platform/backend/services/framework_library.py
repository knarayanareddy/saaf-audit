FRAMEWORK_LIBRARY = [
    # AML/CTF
    {"code": "WWFT", "name": "WWFT (Wet ter voorkoming van witwassen, 2024)", "entities": ["GRP"], "category": "aml"},
    {"code": "DNB_AML", "name": "DNB CDD Guidance (September 2021)", "entities": ["GRP"], "category": "aml"},
    {"code": "EBA_AML", "name": "EBA/GL/2022/05 - AML/CFT Guidelines", "entities": ["GRP", "INT", "AM", "RET", "BUS"], "category": "aml"},
    {"code": "AMLD6", "name": "AMLD6 - 6th Anti-Money Laundering Directive", "entities": ["GRP"], "category": "aml"},
    {"code": "MLR_2017", "name": "Money Laundering Regulations 2017 (UK)", "entities": ["INT"], "category": "aml"},
    {"code": "ANTI_WITWAS_WET_BE", "name": "Wet 18 september 2017 - Belgische AML-wet", "entities": ["RET"], "category": "aml"},
    {"code": "NBB_AML_CIRCULAIRE", "name": "NBB Circulaire AML/CFT (2020)", "entities": ["RET"], "category": "aml"},
    {"code": "LEY_10_2010_ES", "name": "Ley 10/2010 - prevención del blanqueo de capitales (España)", "entities": ["BUS"], "category": "aml"},
    {"code": "SEPBLAC_GUIA", "name": "SEPBLAC - Guía de procedimientos AML/CFT", "entities": ["BUS"], "category": "aml"},
    # Capital
    {"code": "CRR2", "name": "CRR2 / CRD5 - Capital Requirements Regulation", "entities": ["GRP", "INT", "RET", "BUS"], "category": "capital"},
    {"code": "ICAAP_GL", "name": "EBA ICAAP Guidelines (EBA/GL/2016/10)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "capital"},
    {"code": "ILAAP_GL", "name": "EBA ILAAP Guidelines (EBA/GL/2016/09)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "capital"},
    {"code": "IRRBB_GL", "name": "EBA IRRBB Guidelines (EBA/GL/2022/14)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "capital"},
    # ESG
    {"code": "SFDR", "name": "SFDR - Sustainable Finance Disclosure Regulation", "entities": ["GRP", "AM", "RET", "BUS"], "category": "esg"},
    {"code": "EU_TAXONOMY", "name": "EU Taxonomy Regulation (2020/852)", "entities": ["GRP", "AM", "RET", "BUS"], "category": "esg"},
    {"code": "CSRD", "name": "CSRD - Corporate Sustainability Reporting Directive", "entities": ["GRP", "RET", "BUS"], "category": "esg"},
    {"code": "EBA_ESG", "name": "EBA ESG Risk Guidelines (EBA/GL/2022/03)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "esg"},
    # Payments
    {"code": "PSD2", "name": "PSD2 - Payment Services Directive 2", "entities": ["GRP", "INT", "RET", "BUS"], "category": "payments"},
    {"code": "SEPA", "name": "SEPA Regulation (260/2012)", "entities": ["GRP", "RET", "BUS"], "category": "payments"},
    {"code": "CASS", "name": "FCA CASS - Client Asset Sourcebook", "entities": ["INT"], "category": "payments"},
    # IT
    {"code": "DORA", "name": "DORA - Digital Operational Resilience Act", "entities": ["GRP", "INT", "AM", "RET", "BUS"], "category": "it"},
    {"code": "EBA_ICT", "name": "EBA ICT Risk Guidelines (EBA/GL/2019/04)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "it"},
    {"code": "BIO", "name": "BIO - Baseline Informatiebeveiliging Overheid", "entities": ["GRP"], "category": "it"},
    # Governance
    {"code": "EBA_OUTSOURCING", "name": "EBA Outsourcing Guidelines (EBA/GL/2019/02)", "entities": ["GRP", "INT", "AM", "RET", "BUS"], "category": "governance"},
    {"code": "EBA_REMUN", "name": "EBA Remuneration Guidelines (EBA/GL/2021/04)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "governance"},
    {"code": "IFD", "name": "IFD - Investment Firms Directive", "entities": ["AM"], "category": "governance"},
    # Lending
    {"code": "EBA_LENDING", "name": "EBA Lending Guidelines (EBA/GL/2020/06)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "lending"},
    {"code": "DNB_MORTGAGE", "name": "DNB Mortgage Lending Supervisory Focus", "entities": ["GRP"], "category": "lending"},
    # Data
    {"code": "GDPR", "name": "GDPR / AVG - General Data Protection Regulation", "entities": ["GRP", "INT", "AM", "RET", "BUS"], "category": "data"},
    {"code": "EBA_DATA", "name": "EBA Data Governance Guidelines", "entities": ["GRP", "INT", "RET", "BUS"], "category": "data"},
    # Deposit
    {"code": "DGS", "name": "Deposit Guarantee Schemes Directive (2014/49/EU)", "entities": ["GRP", "INT", "RET", "BUS"], "category": "deposit"},
    {"code": "COVERED_BONDS", "name": "EU Covered Bonds Directive (2019/2162)", "entities": ["GRP"], "category": "deposit"},
]


def frameworks_for_entity(entity: str) -> list[dict]:
    return [f for f in FRAMEWORK_LIBRARY if entity in f["entities"]]
