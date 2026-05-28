@api
Feature: Ticket ReBAC read (validates INV-AGG ticket composition, AR-04, INV-ACC-2)
  A customer sees only tickets they relate to; an agent sees all desk tickets
  (GitLab desk membership ∪ OpenFGA viewer relations).

  Background:
    Given ticket "ticket-1" requested by "cust-okafor"
    And ticket "ticket-2" requested by "cust-lind"
    And "cust-okafor" is a watcher of "ticket-2"
    And ticket "ticket-3" requested by "cust-lind"
    And "agent:dani" is a desk agent

  Scenario: A customer's ticket list is only their related tickets (INV-AGG)
    When "cust-okafor" lists tickets
    Then the ticket results include "ticket-1"
    And the ticket results include "ticket-2"
    And the ticket results exclude "ticket-3"

  Scenario: A customer cannot read an unrelated ticket (existence-leak-safe 404)
    When "cust-okafor" reads ticket "ticket-3"
    Then the ticket response status is 404

  Scenario: An agent sees all desk tickets (AR-04 union)
    When "agent:dani" lists tickets
    Then the ticket results include "ticket-1"
    And the ticket results include "ticket-2"
    And the ticket results include "ticket-3"
