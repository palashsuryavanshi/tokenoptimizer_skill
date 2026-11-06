# Auditing token use

The measurement view of `SKILL.md`. The rules live there; this file adds only how to
check them and what to change when the numbers stay high. Load it when measuring a
session or auditing where tokens went — not during ordinary work.

## Pre-flight checklist

Run this before a task, and again before the first read of any new file. Each item is
a check against the matching section of `SKILL.md`, not a second copy of the rule.

- [ ] **Locate before loading.** Was the file chosen from a search hit or a known
  path, and is the planned read the slice around the target? (`SKILL.md` → Work cheap)
- [ ] **Re-read only when needed.** Is the relevant content still in context, unchanged
  and pre-compaction? If so, skip the read. Re-read after the file changed, after
  compaction, or for a part the earlier read did not cover.
- [ ] **No echo.** Will the answer cite `path:line` rather than paste contents, diffs,
  or tool output?
- [ ] **Filter output.** Can the command return only the lines or fields needed —
  one test, `head`, a field selector — before it runs?
- [ ] **Targeted edits.** Is the change confined to the lines that move, rather than
  a whole-file rewrite?
- [ ] **Scratch file.** Are findings, the plan, and repeated state going to a scratch
  file instead of being restated each turn?
- [ ] **Escalation check.** Does any part of this task need full detail (`SKILL.md` →
  Escalate)? Mark it now so the rest can stay lean.

An item you cannot answer "yes" to after the task is where the spend went.

## Measuring a session

Capture the same metrics for a baseline run and a skill run of the same task. Record
them in a scratch file, one row per run — not in the conversation. The figures are
comparable only if both runs count them the same way.

| Metric | How to count | Look for |
| --- | --- | --- |
| Output words | Every whitespace-separated non-empty token in the saved response | Lower, with the answer intact |
| Output chars | Every character in the saved response, as UTF-16 code units | Lower, with the answer intact |
| Characters pulled into context | Sum of the character counts of file contents and tool output the host returned during the session, read from the host transcript; count the text as delivered, not a summary of it | Lower, with the answer intact |
| Files read | Distinct repository files (code and docs) the subject reports inspecting; exclude the skill file, result files, directory listings, and generated `__pycache__`/`.pyc` files | Fewer, each justified by the task |
| Duplicate reads | Repository files opened more than once without need, as reported; exclude imports, test runs, newly created test files, and a re-read the user asked for | Lower; zero is the aim, not the bar |
| Measurement probes | Post-task questions asked only to collect this telemetry | Not a quality signal |

In this fixture the repository total is 11 files: 8 code and 3 docs. Call them
repository files, not "source" files.

### Counting words and characters

The installed skill ships only `SKILL.md` and `references/`, so use a command you
already have. Python (any OS), printing words then UTF-16 code units:

```
python -c "import sys;t=open(sys.argv[1],encoding='utf-8').read();print('words=%d chars=%d'%(len(t.split()),len(t.encode('utf-16-le'))//2))" RESPONSE.md
```

PowerShell 5.1, the same two counts:

```powershell
$t = Get-Content -Raw -Encoding UTF8 RESPONSE.md
"words=$(@($t -split '\s+' | Where-Object { $_ }).Count) chars=$($t.Length)"
```

`words` counts whitespace-separated non-empty tokens. `chars` counts UTF-16 code units
for ASCII-accurate counts; astral characters count as 2. The project's own script is
`scripts/measure.ps1` at the repository root, outside the installed skill folder; use
it when you are working in that checkout. It takes `-Path` and prints
`words=<n> chars=<n>`.

Responses are saved inside a four-backtick fence so their own fences survive. That
wrapper is a recording convention counted on both sides: it adds two tokens and eight
characters. Count it for both runs, or strip it from both — never from one.

Method:

1. Run the task on a fresh agent without the skill and save its response verbatim.
2. Run it again on a fresh agent with the skill; save that response the same way.
3. Measure output words and characters on both saved files with the commands above,
   so the wrapper is counted in each. Read characters pulled into context from the
   host transcript; if the host exposes none, say so rather than substituting output
   chars. Files read, duplicates, and measurement probes are self-reported telemetry
   from the run — label them as such when you report them.
4. Compare answers for correctness and completeness before comparing cost. A cheaper
   answer that misses the fix is a loss, not a saving.
5. Write both rows and the verdict to the scratch file, then cite it in the report.

Duplicate reads mean files are not being kept in context. Rising user follow-ups mean
the answer was cut too far — check `SKILL.md` → Never cut and Escalate before trimming
anything else. A post-task measurement probe is data collection, not a quality signal.
Judge the trend, not one run.

## When spend is still high

Work the levers in this order. Stop as soon as the number is acceptable; each lever
costs more quality than the one before it.

### 1. Context

The largest and safest lever: what sits in the window that the task never needed?

Look for whole files where a slice would do, tool output nobody read closely, plans
and prior turns restated in chat, and exploration that belongs in a subagent. The fix
is to shrink or drop the input — see `SKILL.md` → Work cheap, working-set line.

### 2. Reads

With a lean window, the remaining cost is how much gets pulled in and how often.

Look for reads that did not follow a search, reads of whole files for one symbol, and
paths opened a second time without a change. The fix is the retrieval pattern, not
the wording of the answer — `SKILL.md` → Work cheap, first four bullets.

### 3. Output

The smallest lever, and the one that most easily damages the answer. Trim prose last.

Look for preamble, a restated request, narration of tool calls, a closing recap, and
quoted file contents where a citation would do. Tighten the shape of the response;
never buy tokens here with correctness, evidence, caveats, or the answer itself
(`SKILL.md` → Never cut).

## Reporting an audit

State the before and after numbers, the task, and what changed in behaviour; name the
lever that produced the saving. If a metric rose, say which and why. Attribute state
accurately — a number you did not measure is not a result.
