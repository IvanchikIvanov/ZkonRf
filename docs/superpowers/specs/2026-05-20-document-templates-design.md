# Document Templates Design

## Goal

Add a Telegram bot feature that creates legal document drafts for users: complaints, claims, applications, and similar documents. The bot should detect when a user asks for a document, clarify missing personal and case data, generate a `.docx` file, and send it back in the chat.

The first version focuses on consumer-rights scenarios in Russia and keeps generated documents structured and predictable.

## First Template Set

The first release includes these document types:

1. Claim to seller for refund for goods.
2. Claim for poor-quality service.
3. Complaint to Rospotrebnadzor.
4. Consumer-rights lawsuit.
5. Application/claim to bank, MFO, or debt collector.
6. Complaint to air carrier or Russian Railways.
7. Refund request for online course or paid education.

## User Flow

User writes a natural request, for example: "Составь претензию на возврат денег за телефон, купил 10 мая, сломался через неделю".

The bot:

1. Detects a document-generation intent.
2. Chooses the closest template type.
3. Extracts any already provided facts.
4. Asks for missing required fields.
5. Stores the draft session until all required fields are filled.
6. Generates a `.docx` file.
7. Sends the file with a short reminder to review the draft before submission.

If the request is ambiguous, the bot asks which document the user wants instead of generating a weak draft.

## Required Fields

Common fields for most templates:

- User full name.
- User address.
- User phone or email.
- Recipient name and address.
- Date or approximate date of event.
- Purchase/service amount, when applicable.
- What happened.
- User demand.
- Evidence list, if available.

Additional lawsuit fields:

- Court name.
- Defendant name and address.
- Claim amount.
- Whether a pre-trial claim was sent.
- Penalty, moral damages, fine, and expenses, when user wants them included.

Additional bank/MFO/debt-collector fields:

- Organization name.
- Contract or loan number, if known.
- Disputed amount.
- Description of calls, write-offs, or debt issue.

## Architecture

Add a new service, `document_template_service`, with clear responsibilities:

- Detect document-template intent from user text.
- Choose a template.
- Track missing fields.
- Store per-user draft state.
- Render a final document.

The text handler should call this service before normal RAG search. If the service says the message belongs to an active document draft, the text handler should continue that draft and skip legal Q&A generation.

Templates should live as structured definitions in the repository, not only in prompts. Each definition contains:

- Template id.
- Human title.
- Required fields.
- Optional fields.
- Clarification prompts.
- Body sections.
- Filename pattern.

Generated documents use `python-docx`, which is already in `requirements.txt`.

## Data Flow

1. Incoming Telegram text enters `handle_text_message`.
2. Template service checks whether there is an active draft for the user.
3. If active, it treats the new message as field input.
4. If no active draft, it checks for a document-generation intent.
5. If intent is found, it starts a draft and asks for missing fields.
6. When all required fields are present, it renders `.docx` into a temporary output directory.
7. Handler sends the document through Telegram and clears the draft state.

Draft state should be stored in Redis because the bot already uses it and Redis works across multiple bot workers. If Redis is unavailable, the service may fall back to an in-memory draft store and log a warning; this fallback is only for local development and degraded operation.

## Error Handling

If document rendering fails, the bot sends a clear fallback message and keeps the draft state so the user does not lose entered data.

If a user provides incomplete data, the bot asks only for missing fields.

If a user changes document type mid-flow, the bot should confirm whether to discard the current draft.

If a generated document exceeds Telegram limits or cannot be sent, the bot reports the failure and logs the path/error.

## Legal Safety

The bot should describe files as drafts, not guaranteed court-ready documents. It should include a short note in chat: "Проверьте данные и при необходимости покажите документ юристу перед подачей."

The document itself should not invent facts. Unknown fields should either be clarified before generation or left as bracketed placeholders only for optional fields.

## Testing

Tests should cover:

- Intent detection for common Russian phrases.
- Template selection.
- Required-field detection.
- Active draft continuation.
- `.docx` rendering creates a readable file.
- Handler does not run normal RAG when a document draft is active.
- Error path when required fields are missing.

## Implementation Decisions

Draft state uses Redis first and in-memory fallback second.

Start with deterministic template text and optional LLM-assisted wording later. This keeps the first version reliable and easier to test.
