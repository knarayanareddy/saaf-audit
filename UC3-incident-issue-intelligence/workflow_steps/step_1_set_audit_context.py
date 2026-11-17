"""
Goal:
- Build the analysis context before any incident data is processed.

Input:
- Audit scope and objectives
- Process boundaries
- UC1 policy/process context
- Prior audit findings or known issues

Output:
- Structured audit context object
- Search and filter hints for downstream steps

Code:
- Load audit scope and objectives from config/input (if available) or conversation
- Load process boundaries and system/team filters
- Load UC1 policy/process context
- Load known issues from prior audits
- Convert these inputs into a structured context object

AI:
- Sonnet 4.6: summarize long policy/process documents into a compact audit context
- Haiku 4.5: extract search and filter hints from free-text scope descriptions
"""

def acquire_audit_scope_objectives():
    audit_scope = None
    audit_description = None
    return audit_scope, audit_description

def acquire_policy_context():
    policy_context = None # To be requested from agent UC1
    return policy_context

def acquire_process_context():
    # Fetch overview of available process documentation
    # AI - Haiku 4.5: Select relevant processes
    # AI - Haiku 4.5: Summarize selected processes
    from prompts import select_processes, summarize_process
    process_context = None
    return process_context

def acquire_prior_audit_outcomes():
    prior_outcomes = None
    return prior_outcomes

def compile_audit_context(audit_scope, audit_description, policy_context, process_context, prior_outcomes, model = None):
    # AI - Sonnet 4.6: Summarize inputs into a compact audit context
    from prompts import audit_context
    audit_context = None
    return audit_context

