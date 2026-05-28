@api
Feature: Slack capture (DD-012, DD-013, INV-ID-2)
  Snapshot capture only. Tickets from public threads default to requester-private.
  Actions are refused when the Slack user cannot be mapped to a Keycloak identity.

  Background:
    Given the public community channel "C-COMMUNITY" exists
    And Slack user "U_OKAFOR" maps to Keycloak "ext:r.okafor@uni.example.ac"

  Scenario: Reacting with :ticket: creates a requester-private draft from the thread
    Given a thread in "C-COMMUNITY" started by "U_OKAFOR"
    When "U_OKAFOR" adds the ":ticket:" reaction to the thread
    Then a draft ticket is created with requester "ext:r.okafor@uni.example.ac"
    And the ticket is not community_visible
    And the thread content at this moment is captured as a snapshot
    And the bot acknowledges in the thread

  Scenario: /link-ticket attaches a thread snapshot to an existing ticket
    Given "U_OKAFOR" can see ticket "ticket-2026-000123"
    When "U_OKAFOR" runs "/link-ticket 123" in a thread
    Then the thread snapshot is attached to "ticket-2026-000123"

  Scenario: Action refused when the Slack user is unmapped
    Given Slack user "U_GHOST" maps to no Keycloak identity
    When "U_GHOST" adds the ":ticket:" reaction to a thread
    Then the action is refused
    And no ticket is created
    And the bot explains that identity could not be resolved

  Scenario: Autocomplete only offers tickets the user may see
    Given "U_OKAFOR" cannot see ticket "ticket-2026-000999"
    When "U_OKAFOR" runs "/link-ticket" autocomplete
    Then "ticket-2026-000999" is not offered

  Scenario: Capturing another member's message sets them as requester, records the capturer
    Given a message in "C-COMMUNITY" authored by "U_OKAFOR"
    And Slack user "U_AGENT" maps to Keycloak "agent:dani"
    When "U_AGENT" adds the ":ticket:" reaction to that message
    Then a draft ticket is created with requester "ext:r.okafor@uni.example.ac"
    And "agent:dani" is recorded as the capturer
    And the ticket is requester-private

  Scenario: Capture is rate-limited per Slack user
    Given "U_OKAFOR" has created 5 captures in the last minute
    When "U_OKAFOR" adds another ":ticket:" reaction
    Then the capture is rate-limited and not created
    And the bot explains the limit
