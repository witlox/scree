Feature: Multi-origin ticket creation and email threading (OQ-A-007, OQ-A-014)
  A ticket created from any origin normalizes to one coherent record. Email
  threads on headers, with a [SCREE-NNN] token as fallback.

  @api
  Scenario Outline: Each origin normalizes to one ticket record
    When a ticket is created from "<origin>" by "ext:r.okafor@uni.example.ac"
    Then a ticket exists with requester "ext:r.okafor@uni.example.ac"
    And its origin is "<origin>"
    And it is requester-private by default

    Examples:
      | origin |
      | email  |
      | web    |
      | slack  |
      | api    |

  @contract
  Scenario: Email reply with matching References header threads onto the ticket
    Given ticket "ticket-2026-000123" has email Message-ID "<CA+abc123@mail.uni.example.ac>"
    When an inbound email arrives with References "<CA+abc123@mail.uni.example.ac>"
    Then the email is appended to "ticket-2026-000123"
    And no new ticket is created

  @contract
  Scenario: Email reply missing headers threads via the [SCREE-NNN] token
    Given ticket "ticket-2026-000123" has email_token "SCREE-123"
    When an inbound email arrives with no References header and subject "Re: [SCREE-123] export fails"
    Then the email is appended to "ticket-2026-000123"

  @contract
  Scenario: Email with neither headers nor token creates a new ticket
    When an inbound email arrives with no References header and subject "help please"
    Then a new ticket is created
    And it is not appended to "ticket-2026-000123"

  @contract
  Scenario: A spoofed or mismatched sender is quarantined, not appended (INV-EMAIL-1)
    Given ticket "ticket-2026-000123" has requester "ext:r.okafor@uni.example.ac"
    When an inbound email quoting "[SCREE-123]" arrives from unverified sender "attacker@evil.example"
    Then the email is not appended to "ticket-2026-000123"
    And it is quarantined for agent review

  @api
  Scenario: An agent can merge two tickets that were the same conversation
    Given tickets "ticket-2026-000123" and "ticket-2026-000131" exist
    When "agent:dani" merges "ticket-2026-000131" into "ticket-2026-000123"
    Then "ticket-2026-000131" references "ticket-2026-000123" as merged-into
    And both threads are visible under "ticket-2026-000123"
