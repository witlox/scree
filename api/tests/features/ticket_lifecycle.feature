@api
Feature: Ticket lifecycle (INV-LC-1, INV-LC-2)
  open -> resolved -> closed with reopen; only the assignee or an agent may
  transition; community_visible is resolved-only and re-gated on reopen.

  Background:
    Given ticket "ticket-1" requested by "cust-okafor" assigned to "agent:dani"
    And "agent:dani" is a desk agent

  Scenario: An agent resolves then closes a ticket
    When "agent:dani" transitions "ticket-1" to "resolved"
    Then ticket "ticket-1" status is "resolved"
    When "agent:dani" transitions "ticket-1" to "closed"
    Then ticket "ticket-1" status is "closed"

  Scenario: An illegal transition is rejected (open -> closed)
    When "agent:dani" transitions "ticket-1" to "closed"
    Then the transition is rejected with 409
    And ticket "ticket-1" status is "open"

  Scenario: A non-agent, non-assignee cannot transition
    When "cust-okafor" transitions "ticket-1" to "resolved"
    Then the transition is rejected with 403

  Scenario: community_visible may only be set on a resolved ticket
    When "agent:dani" promotes "ticket-1" to community-visible
    Then the promotion is rejected with 409

  Scenario: Promote a resolved ticket, then reopening re-gates it to private
    When "agent:dani" transitions "ticket-1" to "resolved"
    And "agent:dani" promotes "ticket-1" to community-visible
    Then ticket "ticket-1" is community-visible
    When "agent:dani" transitions "ticket-1" to "open"
    Then ticket "ticket-1" is not community-visible
