@api
Feature: Ticket creation across origins (INV-DP-1, DD-013)
  A ticket created from any origin normalizes to one record: opaque requester,
  status open, requester-private by default — even from a public Slack thread.

  Scenario Outline: A ticket from <origin> normalizes to a private open ticket
    When "cust-okafor" creates a ticket from "<origin>"
    Then the created ticket origin is "<origin>"
    And the created ticket status is "open"
    And the created ticket is requester-private
    And the created ticket requester is "cust-okafor"

    Examples:
      | origin |
      | web    |
      | api    |
      | email  |
      | slack  |
