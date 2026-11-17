# Presenter walkthrough (5 to 10 minutes)

A click-by-click script for showing the agent to an audience of auditors. It uses the synthetic sample data. Every result on screen is computed live by the agent; only the model step can fall back to a prepared result, and the screen says so when it does.

## The day before

1. Double-click **`Start Demo.command`** once on the presentation laptop, with internet. The first start installs the environment. Close the Terminal window afterwards.
2. Open Terminal, type `claude` and check that you are logged in. Type `/exit` to leave.
3. Start the demo again and run through all five steps once. Step 4 should say **Live · Claude Code**.
4. Test the fallback: switch Wi-Fi off, start again, run to step 4. It should say **Prepared result**. Switch Wi-Fi back on.
5. Turn on Do Not Disturb, close other apps, and set the browser zoom so the page fits the projector (Cmd and + or -).
6. In the browser, switch off password manager pop-ups for this page if they appear in the sign-off field.

If the venue network is unreliable, start with prepared results from the outset:

```bash
JML_DRAFT_MODE=prepared .venv/bin/python run.py
```

## On stage

Start: double-click **`Start Demo.command`**. The browser opens. Check the top right: **Claude Code ready**. Pick **EN** or **NL**.

A presentation clicker works: **next** (→ / Page Down) runs the next button, **back** (← / Page Up) goes back.

| Step | Click | Say (in your own words) |
|---|---|---|
| Opening | none | "Joiners, movers and leavers is one of the most tested IT general controls, and one of the most time-consuming. The question is always the same: does every access right go back to an approved request, and does access go when the job or the person goes?" Point at **Reads, Checks, Returns**. |
| 1 Scope | **Load the sources** | "Six exports from a fictional company: HR, Active Directory, the ERP, Jira tickets and the access policy. One quarter. The agent shows row counts and a hash of every file, so you know exactly what was tested." |
| 2 Controls | **Run the controls** | "Twelve JML controls plus five basic account checks, on every record, not a sample. This part is deterministic: no AI, the same data always gives the same answer." Point at the tests without exceptions: "Clean records pass too." Mention: "The baseline checks reuse an engine that a SAAF team built in an earlier hackathon." |
| 3 Exceptions | **See the exceptions**, then click one or two rows | "Fifteen exceptions. Each one has the person's timeline and the exact source rows." Good examples: **Lucas Mulder** (moved to Treasury, kept the invoice role: he can enter and pay an invoice), **Ruben Hendriks** (left in August, logged in six days later), **Mila Peters** (the ticket says 'same access as a colleague' and names no role). |
| 4 Findings | **Ask Claude to draft findings**, then **Draft the findings** | While the squares fill (about 30 seconds): "Claude runs on this laptop with every tool switched off. It gets only these exceptions, pseudonymised: no names. It cannot open files or browse." When the result appears: "Every finding is checked against the input. Anything that cites a record that does not exist is rejected, and you would see that here." Open a finding and click a source number to jump back to the evidence. Point at **Needs follow-up**: "The model separates what is proven from what needs a question to management." |
| 5 Sign-off | tick the box, type a name, **Sign off and open the report** | "The agent drafts. The auditor decides. Nothing is final until a person signs off." The report opens; scroll through it. |

Close: "This agent is open source in the SAAF Project. Any member can run it on their own exports, improve a control, or add a system."

## If something goes wrong

| What you see | What to do |
|---|---|
| Top right says **Claude Code not available** | Carry on. Step 4 will use the prepared result and say so. |
| Step 4 says **Prepared result** with a reason | Say: "The live call did not come through, so the agent shows the result it recorded earlier on the same data. It tells you that openly, which is exactly what you want from an audit tool." |
| The page does not open | Look at the Terminal window for a message. Close it and double-click **`Start Demo.command`** again. The address is `http://127.0.0.1:8765`. |
| You clicked too far | Press **back** on the clicker, or click a step in the bar at the top. |
| You want to start over | Reload the page (Cmd and R). |
