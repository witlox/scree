@api
Feature: Orphan detection (INV-ORPH-1, OQ-A-005)
  An active resource whose owner lost access (left the org / removed from the
  Space / Space archived) is flagged in the hourly batch for manual reassignment.

  Scenario: An open risk whose owner lost Space access is flagged
    Given risk "risk-2026-044" is "open" with owner "j.tan"
    And "j.tan" has lost access to space "platform/handbook"
    When the hourly batch runs
    Then "risk-2026-044" appears in the "orphaned actives" report for "platform/handbook" maintainers
    And it is not automatically reassigned

  Scenario: Closed resources are not flagged
    Given risk "risk-2026-009" is "closed" with owner "j.tan"
    And "j.tan" has lost access to space "platform/handbook"
    When the hourly batch runs
    Then "risk-2026-009" does not appear in the "orphaned actives" report

  Scenario: A resource whose owner still has access is not flagged
    Given risk "risk-2026-044" is "open" with owner "rivera"
    And "rivera" still has access to "platform/handbook"
    When the hourly batch runs
    Then "risk-2026-044" does not appear in the "orphaned actives" report
