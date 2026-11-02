# Ready to submit: MCP-WP contributions

The code is uploaded to this fork. These links open prepared forms; you review
and submit them yourself. No upstream issue or pull request has been posted.

## First contribution: event-result contract

[**Open the first pull request, with title and body filled in**](https://github.com/steveh250/website-mcp-standard/compare/main...OllieinCanada:contrib/event-contract?expand=1&title=Fix+get_event+outcome%2Flifecycle+collision&body=Top-level+%60status%60+currently+uses+event+lifecycle+values%2C+rejecting+standard+%60ok%60%2Ferror+outcomes+and+leaving+success-field+requirements+ineffective.+The+published+example+also+repeats+%60status%60%2C+silently+replacing+%60ok%60+during+ordinary+JSON+parsing.%0A%0AReserve+outer+%60status%60+for+tool+outcomes+and+use+optional+%60event_status%60+consistently+in+detail+and+list+items.+Restore+successful+detail+requirements%2C+correct+both+examples%2C+and+update+the+specification%2Fchangelog.+This+is+a+draft+field-name+change+proposed+for+maintainer+agreement+%28MCPWP-EVT-001%2F003%3B+MCPWP-RES-001%2F010%2F011%29.%0A%0AValidation%3A+eight+focused+event+regressions+pass+as+part+of+the+integrated+suite+on+Python+3.10%2C+3.12%2C+and+3.14.+The+complete+integration+passes+76+tests+and+all+27+examples.+The+event-only+branch+contains+the+focused+tests%3B+later+contributions+add+the+validator+and+CI.%0A%0ATo+run+the+focused+tests+on+this+branch%3A%0A%0A%60%60%60bash%0Apython3+-m+pip+install+%22jsonschema%5Bformat-nongpl%5D%3D%3D4.26.0%22%0Apython3+tools%2Fvalidate_examples.py%0Apython3+-m+unittest+discover+-s+tests+-p+test_event_contract.py+-v%0A%60%60%60%0A)

Confirm the destination is **steveh250/website-mcp-standard**, base `main`, and
head **OllieinCanada:contrib/event-contract**. Review the seven-file diff and click
**Create pull request** when ready. The body is also available in
[copy-ready text](submission/01-event-contract-pr.md).

This fixes the duplicate `status` key and proposes optional `event_status` for
event lifecycle. Maintainer agreement on this draft field-name change is pending.

## Checker proposal

[**Open the proposal issue, with title and body filled in**](https://github.com/steveh250/website-mcp-standard/issues/new?title=Proposal%3A+bounded%2C+read-only+Core+conformance+checker&body=%23%23+Use+case%0A%0AAn+implementer+can+validate+the+published+response+examples+today%2C+but+cannot%0Acheck+whether+their+own+%60%2Fmcp%60+endpoint+exposes+the+five+Core+tools%2C+implements%0AMCP+initialization%2C+returns+valid+structured+results%2C+or+resolves+section+and%0Asearch+references.+Section+12+already+describes+a+conformance+checker%3B+this%0Acontribution+supplies+its+first%2C+Core-only+milestone.%0A%0A%23%23+Proposed+contribution%0A%0AAdd+a+Python+command-line+tool+that+takes+a+website+host%2C+derives+its+HTTPS%0A%60%2Fmcp%60+endpoint%2C+and+emits+either+readable+output+or+a+versioned+JSON+report.%0AUse+the+official+MCP+SDK+for+Streamable+HTTP%2C+negotiation%2C+session+headers%2C%0AJSON%2FSSE+responses%2C+and+lifecycle+notifications.+Use+the+repository%27s+strict%0AJSON+loader+and+normative+schemas+for+response+validation.%0A%0AExercise+the+ten+Core+groups+in+%C2%A712%2C+linking+evidence+to+permanent+requirement%0AIDs%3A+%60MCPWP-MCP-001%60%E2%80%93%60003%60%2C+%60MCPWP-DISC-001%60%E2%80%93%60005%60%2C+%60MCPWP-CORE-001%60%E2%80%93%60006%60%2C%0A%60MCPWP-CORE-010%60%2C+%60MCPWP-CORE-040%60%E2%80%93%60042%60%2C+%60MCPWP-CORE-050%60%E2%80%93%60052%60%2C%0A%60MCPWP-DECL-001%60%E2%80%93%60003%60%2C+%60MCPWP-RES-001%60%2F%60010%60%2F%60011%60%2C+and+%60MCPWP-EXTN-001%60.%0ADistinguish+mandatory+failures+from+recommendations+such+as+alternate-host%0Asupport+%28%60MCPWP-DISC-003%60%29+and+advertised+output+schemas+%28%60MCPWP-CORE-005%60%29.%0A%0A%23%23+Boundaries+and+reporting%0A%0A-+Call+only+the+five+Core+tools%2C+without+credentials.+Never+call+transaction%0A++tools+or+accept+a+remote+%60test%3A+true%60+declaration+as+authorization+to+do+so.%0A-+Bound+request+counts%2C+wall+time%2C+pagination%2C+redirects%2C+and+content+samples.%0A++Report+incomplete+coverage+and+blocked+dependencies+explicitly.%0A-+Report+PASS%2C+FAIL%2C+SKIP%2C+and+NOT+TESTED+with+concise+evidence.+A+passing%0A++sampled+run+is+not+certification+of+every+page%2C+every+possible+input%2C+human%0A++site+consistency%2C+privacy%2C+or+absence+of+side+effects.%0A-+Mark+Extended+and+Transactional+behavior+NOT+TESTED.+Declared+standard+tool%0A++presence+can+be+observed+through+%60tools%2Flist%60%2C+but+presence+does+not+prove%0A++behavior+or+custom-module+completeness.%0A-+Test+locally+against+controlled+JSON%2FSSE+fixture+servers+in+CI.+Live+runs%0A++require+an+operator+to+invoke+the+CLI+for+the+chosen+host.%0A%0A%23%23+Acceptance%0A%0AThe+repository%27s+corrected+schemas%2Fexamples+and+strict-validation+regressions%0Aremain+green.+Local+fixtures+exercise+lifecycle%2Fsession+headers%2C+pagination%2C%0Aredirects%2C+result+contracts%2C+declarations%2C+reference+resolution%2C+failures%2C+and%0Abudget+exhaustion.+Reports+retain+useful+partial+evidence+when+an+assessment%0Acannot+finish.+No+production+endpoint+is+needed+to+validate+this+contribution.%0A%0ABroader+module+checking%2C+transactional+integration+tests%2C+packaging+as+a+public%0Aservice%2C+and+a+report+registry+are+later+milestones+outside+this+proposal.%0A%0ADoes+this+Core-only+scope+and+reporting+model+fit+the+intended+roadmap%3F+Feedback+before+the+checker+PR+would+help+keep+the+contribution+aligned.%0A)

Review and submit the form. The [issue body](submission/checker-issue.md) is ready
to copy if GitHub shows a template chooser instead. It proposes bounded,
unauthenticated Core checking; no transactional tools are called. Submit the
checker PR after discussing this scope with maintainers.

## All uploaded branches

| Contribution | Branch | Prepared PR body |
| --- | --- | --- |
| Event contract | [contrib/event-contract](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/event-contract) | [Body](submission/01-event-contract-pr.md) |
| Strict validation and CI | [contrib/strict-validation](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/strict-validation) | [Body](submission/02-strict-validation-pr.md) |
| Declaration/public outcomes | [contrib/public-contracts](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/public-contracts) | [Body](submission/03-public-contracts-pr.md) |
| Transaction audit | [contrib/transaction-audit](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/transaction-audit) | [Body](submission/04-transaction-audit-pr.md) |
| Core checker / full integration | [contrib/core-checker](https://github.com/OllieinCanada/website-mcp-standard/tree/contrib/core-checker) | [Body](submission/05-core-checker-pr.md) |

The branches contain the ordered cumulative contributions. **Submit the event
fix first**, rather than opening all five against upstream `main` together.
After each earlier contribution lands, prepare the next PR against the updated
upstream so its diff contains only the next contribution. If maintainers squash
or change earlier commits, refresh onto current upstream and rerun the checks.
Do not merge these branches into the fork's `main` merely to submit them upstream.

The posting guide is on its own branch and is excluded from all contribution PRs.

## Verification

The complete integration passed **76 tests and all 27 examples** in fresh Python
**3.10.22** and **3.14.8** environments, with an earlier Python 3.12 pass.
Controlled direct TLS, HTTPS 307 redirection, and CONNECT-proxy scenarios passed
with certificate verification enabled. No public endpoint was scanned.

[**GitHub Actions runs**](https://github.com/OllieinCanada/website-mcp-standard/actions)
now provide hosted CI results. The full suite belongs to the integrated checker
branch; the first event branch contains its eight focused regression tests.

### Hosted CI results

All CI-enabled contribution branches pass on **Python 3.10 and 3.14**:

| Branch | Passing run |
| --- | --- |
| Strict validation | [CI passed](https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376843245) |
| Declaration/public outcomes | [CI passed](https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376860909) |
| Transaction audit | [CI passed](https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376863237) |
| Core checker / integration | [CI passed](https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376798582) |

The initial setup failure was fixed by explicitly selecting `requirements*.txt`
for pip caching. The fix was appended to each affected branch without rewriting
published history. The event-only branch intentionally precedes the CI addition;
its PR body includes standalone commands for the focused tests.
