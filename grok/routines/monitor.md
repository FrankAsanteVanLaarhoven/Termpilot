# Monitoring routine

Grok CLI does not host a cloud cron. TermPilot implements the routine in-process:

```
POST /monitor/run
```

Schedule (optional, local):

```
*/30 * * * * curl -sS http://127.0.0.1:8000/monitor/run
```

Behaviour:

1. Recheck authorised sources.
2. Compare new observations with the last verified state.
3. Notify only when a material change occurs.
4. Never write externally without policy and approval checks.
5. Record routine executions and failures.

Headless Grok CLI equivalent:

```
grok -p "Run the TermPilot monitoring routine against the local API. Do not write calendars."
```
