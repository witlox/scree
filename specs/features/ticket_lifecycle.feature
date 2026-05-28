@api
Feature: Ticket lifecycle (INV-LC-1, INV-LC-2)
  Tickets move open → resolved → closed, with a reopen path. community_visible is
  orthogonal to state and requires an explicit agent action.

  Background:
    Given ticket "ticket-2026-000123" has requester "ext:r.okafor@uni.example.ac"
    And ticket "ticket-2026-000123" has assignee "agent:dani"
    And ticket "ticket-2026-000123" is "open"

  Scenario Outline: Legal transitions performed by the assignee
    Given ticket "ticket-2026-000123" is "<from>"
    When "agent:dani" transitions it to "<to>"
    Then the ticket status is "<to>"

    Examples:
      | from     | to       |
      | open     | resolved |
      | resolved | closed   |
      | resolved | open     |
      | closed   | open     |

  Scenario: Illegal transition is rejected
    Given ticket "ticket-2026-000123" is "open"
    When "agent:dani" transitions it to "closed"
    Then the transition is rejected
    And the ticket status is "open"

  Scenario: A non-agent cannot transition a ticket
    When "ext:r.okafor@uni.example.ac" transitions "ticket-2026-000123" to "resolved"
    Then the transition is rejected

  Scenario: Promoting to community-visible requires explicit confirmed agent action
    Given ticket "ticket-2026-000123" is "resolved" and not community_visible
    When "agent:dani" promotes it to community_visible with confirmation
    Then "ticket-2026-000123" is community_visible
    And the promotion is recorded in the audit trail
