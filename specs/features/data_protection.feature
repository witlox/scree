Feature: Data protection & erasure (ADR-0006, INV-DP-*)
  Customer identity lives outside Git; GDPR erasure anonymizes. Tickets may be
  born encrypted at create. Bounded by the GitLab substrate.

  @api
  Scenario: Creating a ticket with the encrypt option stores the body encrypted
    Given "cust-7f3a2b" submits a ticket with the encrypt option enabled
    Then the ticket body is stored encrypted at rest
    And it is not readable from a raw repo clone
    And an agent opening it via the Gateway sees the decrypted body
    And the ticket is indexed by metadata only, not full-text

  @api
  Scenario: Encryption is a create-time decision, not retroactive
    Given ticket "ticket-2026-000123" was created cleartext
    When an agent attempts to encrypt it after the fact
    Then they are warned that the prior cleartext remains in Git history
    And the action does not retroactively protect existing history

  @api
  Scenario: No direct customer PII is stored in Git frontmatter
    Given ticket "ticket-2026-000123" exists
    Then its frontmatter `requester` is an opaque id
    And no customer name or email appears in the frontmatter

  @contract
  Scenario: Erasure anonymizes by deleting the identity record
    Given customer "cust-7f3a2b" owns ticket "ticket-2026-000123"
    When a GDPR erasure request for "cust-7f3a2b" is fulfilled
    Then the identity-directory record for "cust-7f3a2b" is deleted
    And "ticket-2026-000123" remains but its requester id is unresolvable
    And Git history is not rewritten

  @contract
  Scenario: Erasing a customer with an encrypted ticket also crypto-shreds it
    Given customer "cust-7f3a2b" owns encrypted ticket "ticket-2026-000200"
    When a GDPR erasure request for "cust-7f3a2b" is fulfilled
    Then the per-requester key is destroyed
    And the encrypted body of "ticket-2026-000200" is permanently unrecoverable
