# Controlled AI actions in Intima

## Principle

`AI intent -> pending action -> user confirmation -> backend validation -> Neon -> audit log`

AI INSIGHT can propose an internal Intima credits operation, for example a
charge for an AI session or a credit bonus. It never creates a ledger row until
an administrator explicitly confirms the proposal.

## Supported action

`create_credit_transaction` is prepared through the Gemini tool
`prepare_credit_transaction`.

The draft payload must contain:

- `type`: `income` or `expense`;
- `amount`: a positive Intima credit amount;
- `category`: a non-empty Intima service category;
- `date`: an ISO `YYYY-MM-DD` date;
- optional `description`.

The backend uses Pydantic validation with forbidden extra fields both before a
pending action is created and again before confirmation.

## Lifecycle

- `pending`: a user-visible draft; the ledger has not changed.
- `confirmed`: the backend has created one validated `credit_transactions` row.
- `cancelled`: the draft was declined; the ledger has not changed.
- `failed`: confirmation could not validate the stored payload.

`POST /api/ai/actions/{action_id}/confirm` and
`POST /api/ai/actions/{action_id}/cancel` accept only actions in `pending`
status. Repeating either request is rejected with `409 Conflict`.

## Audit log and boundaries

Each creation, confirmation, cancellation or validation failure is written to
`ai_action_audit_logs` with the action and thread identifiers, action type,
event, timestamp and safe result metadata.

The action tool cannot delete, edit or bulk-change operations; execute raw SQL;
or access environment variables and secrets. It stores no API keys, database
URLs, bot tokens or passwords.
