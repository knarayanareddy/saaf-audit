"""
Central prompt module for the Incident & Issue Intelligence Agent.

Purpose:
- define reusable prompt templates
- build prompts from step-specific input
- apply shared guardrails
- scrub and validate prompts before execution
- send prompts to the selected LLM

Recommended internal separation inside this file:
1. Guardrail definitions
2. Generic prompt utilities
3. Prompt quality/scrubbing helpers
4. Step-specific prompt builders
5. LLM execution wrapper

This is intentionally a first, mostly empty version.
The goal is to make responsibilities explicit before implementation starts.
"""


# ---------------------------------------------------------------------------
# 1. Guardrail definitions
# ---------------------------------------------------------------------------

# Central rules that every prompt should inherit.
# Examples:
# - do not request or expose unnecessary PII
# - keep outputs structured and auditable
# - explain uncertainty instead of fabricating certainty
# - stay within audit scope
GUARDRAILS = {
    "privacy": [],
    "scope": [],
    "quality": [],
    "output": [],
}


# ---------------------------------------------------------------------------
# 2. Generic prompt utilities
# ---------------------------------------------------------------------------

def merge_prompt_sections(*sections):
    """Combine prompt fragments into a single prompt string."""
    raise NotImplementedError


def inject_guardrails(prompt, guardrails=None):
    """Attach central or step-specific guardrails to a prompt."""
    raise NotImplementedError


def format_context_block(title, content):
    """Render a labeled context section for inclusion in a prompt."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 3. Prompt quality and scrubbing helpers
# ---------------------------------------------------------------------------

def build_prompt_writer_prompt(task_description, input_context=None):
    """
    Build a meta-prompt for generating or improving prompts.

    Intended use:
    - generate a first prompt draft for a new task
    - rewrite an existing prompt for clarity, structure, or safety
    """
    raise NotImplementedError


def build_prompt_scrub_prompt(prompt_text):
    """
    Build a prompt that reviews another prompt for issues such as:
    - missing guardrails
    - unclear instructions
    - privacy risks
    - output-format ambiguity
    """
    raise NotImplementedError


def scrub_prompt(prompt_text):
    """Apply deterministic checks and clean-up steps to a prompt."""
    raise NotImplementedError


def validate_prompt(prompt_text):
    """Validate that a prompt meets minimum safety and quality requirements."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 4. Step-specific prompt builders
# ---------------------------------------------------------------------------

def select_processes(audit_scope, process_catalog):
    """
    Build the prompt for selecting relevant processes from available process
    documentation.
    """
    raise NotImplementedError


def summarize_process(selected_process_docs):
    """Build the prompt for summarizing selected process documentation."""
    raise NotImplementedError


def audit_context(
    audit_scope,
    audit_description,
    policy_context,
    process_context,
    prior_outcomes,
):
    """Build the prompt for compiling a compact audit context."""
    raise NotImplementedError


# Placeholder section for future workflow steps.
# Add builders here for:
# - relevance selection
# - semantic classification
# - root-cause synthesis
# - materiality assessment
# - report drafting


# ---------------------------------------------------------------------------
# 5. LLM execution wrapper
# ---------------------------------------------------------------------------

def send_prompt(prompt_text, model, system_prompt=None):
    """
    Send a prepared prompt to the selected LLM.

    Expected responsibilities:
    - receive fully prepared prompt input
    - call the chosen model
    - return raw or lightly structured model output
    """
    raise NotImplementedError


def prepare_and_send(prompt_text, model, guardrails=None, system_prompt=None):
    """
    Standard prompt execution flow:
    1. scrub prompt
    2. validate prompt
    3. inject guardrails
    4. send prompt to LLM
    """
    raise NotImplementedError
