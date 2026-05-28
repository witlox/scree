@contract
Feature: Graceful degradation when GitLab is unreachable (INV-DEG-1, DD-003)
  Reads from a local clone of authorized content still work; writes are refused
  clearly, never silently dropped or falsely succeeded.

  Background:
    Given GitLab is unreachable
    And a local clone of "platform/handbook" exists for "rivera"

  Scenario: Authorized reads from the local clone succeed
    When "rivera" opens doc "doc-platform-onboarding"
    Then the doc renders from the local clone

  Scenario: Ticket creation is refused with a clear error
    When "ext:r.okafor@uni.example.ac" submits a new ticket
    Then creation is refused with an error stating GitLab is unavailable
    And no ticket is queued as if it had succeeded

  Scenario: Reads respect permissions even from the local clone
    When "rivera" attempts to read a doc in a space they do not belong to
    Then access is denied
