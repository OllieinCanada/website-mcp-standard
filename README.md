# Your contributions are uploaded and ready

All five code branches and the prepared submission text are on this fork.
Start with the event fix below. You review and submit the forms from your own
GitHub account.

## 1. Submit the event fix

[**CREATE THE FIRST PULL REQUEST — title and description already filled in**](https://github.com/steveh250/website-mcp-standard/compare/main...OllieinCanada:contrib/event-contract?expand=1&title=Fix+get_event+outcome%2Flifecycle+collision&body=Top-level+%60status%60+currently+uses+event+lifecycle+values%2C+rejecting+standard+%60ok%60%2Ferror+outcomes+and+leaving+success-field+requirements+ineffective.+The+published+example+also+repeats+%60status%60%2C+silently+replacing+%60ok%60+during+ordinary+JSON+parsing.%0A%0AReserve+outer+%60status%60+for+tool+outcomes+and+use+optional+%60event_status%60+consistently+in+detail+and+list+items.+Restore+successful+detail+requirements%2C+correct+both+examples%2C+and+update+the+specification%2Fchangelog.+This+is+a+draft+field-name+change+proposed+for+maintainer+agreement+%28MCPWP-EVT-001%2F003%3B+MCPWP-RES-001%2F010%2F011%29.%0A%0AValidation%3A+eight+focused+event+regressions+pass+as+part+of+the+integrated+suite+on+Python+3.10%2C+3.12%2C+and+3.14.+The+complete+integration+passes+76+tests+and+all+27+examples.+The+event-only+branch+contains+the+focused+tests%3B+later+contributions+add+the+validator+and+CI.%0A%0ATo+run+the+focused+tests+on+this+branch%3A%0A%0A%60%60%60bash%0Apython3+-m+pip+install+%22jsonschema%5Bformat-nongpl%5D%3D%3D4.26.0%22%0Apython3+tools%2Fvalidate_examples.py%0Apython3+-m+unittest+discover+-s+tests+-p+test_event_contract.py+-v%0A%60%60%60%0A)

The link compares **steveh250/website-mcp-standard:main** with
**OllieinCanada/website-mcp-standard:contrib/event-contract**.
Review the seven-file diff, then click GitHub's **Create pull request** button.

[Read the PR description](submission/01-event-contract-pr.md)

## 2. Post the checker proposal

[**OPEN THE PROPOSAL ISSUE — title and description already filled in**](https://github.com/steveh250/website-mcp-standard/issues/new?title=Proposal%3A+bounded%2C+read-only+Core+conformance+checker&body=%23%23+Use+case%0A%0AAn+implementer+can+validate+the+published+response+examples+today%2C+but+cannot%0Acheck+whether+their+own+%60%2Fmcp%60+endpoint+exposes+the+five+Core+tools%2C+implements%0AMCP+initialization%2C+returns+valid+structured+results%2C+or+resolves+section+and%0Asearch+references.+Section+12+already+describes+a+conformance+checker%3B+this%0Acontribution+supplies+its+first%2C+Core-only+milestone.%0A%0A%23%23+Proposed+contribution%0A%0AAdd+a+Python+command-line+tool+that+takes+a+website+host%2C+derives+its+HTTPS%0A%60%2Fmcp%60+endpoint%2C+and+emits+either+readable+output+or+a+versioned+JSON+report.%0AUse+the+official+MCP+SDK+for+Streamable+HTTP%2C+negotiation%2C+session+headers%2C%0AJSON%2FSSE+responses%2C+and+lifecycle+notifications.+Use+the+repository%27s+strict%0AJSON+loader+and+normative+schemas+for+response+validation.%0A%0AExercise+the+ten+Core+groups+in+%C2%A712%2C+linking+evidence+to+permanent+requirement%0AIDs%3A+%60MCPWP-MCP-001%60%E2%80%93%60003%60%2C+%60MCPWP-DISC-001%60%E2%80%93%60005%60%2C+%60MCPWP-CORE-001%60%E2%80%93%60006%60%2C%0A%60MCPWP-CORE-010%60%2C+%60MCPWP-CORE-040%60%E2%80%93%60042%60%2C+%60MCPWP-CORE-050%60%E2%80%93%60052%60%2C%0A%60MCPWP-DECL-001%60%E2%80%93%60003%60%2C+%60MCPWP-RES-001%60%2F%60010%60%2F%60011%60%2C+and+%60MCPWP-EXTN-001%60.%0ADistinguish+mandatory+failures+from+recommendations+such+as+alternate-host%0Asupport+%28%60MCPWP-DISC-003%60%29+and+advertised+output+schemas+%28%60MCPWP-CORE-005%60%29.%0A%0A%23%23+Boundaries+and+reporting%0A%0A-+Call+only+the+five+Core+tools%2C+without+credentials.+Never+call+transaction%0A++tools+or+accept+a+remote+%60test%3A+true%60+declaration+as+authorization+to+do+so.%0A-+Bound+request+counts%2C+wall+time%2C+pagination%2C+redirects%2C+and+content+samples.%0A++Report+incomplete+coverage+and+blocked+dependencies+explicitly.%0A-+Report+PASS%2C+FAIL%2C+SKIP%2C+and+NOT+TESTED+with+concise+evidence.+A+passing%0A++sampled+run+is+not+certification+of+every+page%2C+every+possible+input%2C+human%0A++site+consistency%2C+privacy%2C+or+absence+of+side+effects.%0A-+Mark+Extended+and+Transactional+behavior+NOT+TESTED.+Declared+standard+tool%0A++presence+can+be+observed+through+%60tools%2Flist%60%2C+but+presence+does+not+prove%0A++behavior+or+custom-module+completeness.%0A-+Test+locally+against+controlled+JSON%2FSSE+fixture+servers+in+CI.+Live+runs%0A++require+an+operator+to+invoke+the+CLI+for+the+chosen+host.%0A%0A%23%23+Acceptance%0A%0AThe+repository%27s+corrected+schemas%2Fexamples+and+strict-validation+regressions%0Aremain+green.+Local+fixtures+exercise+lifecycle%2Fsession+headers%2C+pagination%2C%0Aredirects%2C+result+contracts%2C+declarations%2C+reference+resolution%2C+failures%2C+and%0Abudget+exhaustion.+Reports+retain+useful+partial+evidence+when+an+assessment%0Acannot+finish.+No+production+endpoint+is+needed+to+validate+this+contribution.%0A%0ABroader+module+checking%2C+transactional+integration+tests%2C+packaging+as+a+public%0Aservice%2C+and+a+report+registry+are+later+milestones+outside+this+proposal.%0A%0ADoes+this+Core-only+scope+and+reporting+model+fit+the+intended+roadmap%3F+Feedback+before+the+checker+PR+would+help+keep+the+contribution+aligned.%0A)

Review the form and click **Create**. If GitHub displays an issue-template
chooser, the [complete issue text](submission/checker-issue.md) is ready to paste.

## Code and checks

- [Full implementation: all five contributions](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/core-checker)
- [First event fix only](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/event-contract)
- [Passing integration CI: Python 3.10 and 3.14](https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376798582)
- [Full posting guide and remaining PR descriptions](POSTING_GUIDE.md)

The integrated suite passes **76 tests and all 27 examples**. Controlled TLS,
redirect, and proxy checks also pass.

Submit the event fix first. The other branches contain cumulative changes and
should be proposed in order, with each later diff refreshed after earlier work
lands. The checker proposal should be discussed before the checker PR.

This fork opens on the submission-guide branch so these actions are visible on
its homepage. The original `main` branch and all code branches are preserved.
No upstream PR or issue has been submitted by this setup.
