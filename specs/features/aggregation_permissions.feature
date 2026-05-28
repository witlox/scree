@api @security
Feature: Aggregation views never leak unauthorized items (INV-AGG)
  A principal sees, in any aggregation/search/portfolio/risk view, only items
  they could read by direct access. No title, excerpt, count, score, or metadata
  of an unauthorized item is exposed.

  Background:
    Given the user "rivera" is a member of space "platform/handbook" and "org/risk-portfolio"
    And the user "okafor" is a member of "org/risk-portfolio" only
    And risk "risk-2026-001" lives in "org/risk-portfolio"
    And risk "risk-2026-044" lives in "platform/handbook"

  Scenario: Cross-project risk register excludes unreadable risks
    When "okafor" queries the cross-project risk register
    Then the results include "risk-2026-001"
    And the results exclude "risk-2026-044"

  Scenario: No metadata leak in counts or titles
    When "okafor" queries the cross-project risk register
    Then the result count is 1
    And no title, score, or excerpt of "risk-2026-044" appears anywhere in the response

  Scenario: Sensitive categories come from the separate index and stay filtered
    Given risk "risk-2026-050" in "org/risk-security" has category "security"
    And "okafor" is not a member of "org/risk-security"
    When "okafor" searches all risks for the term "credential"
    Then the results exclude "risk-2026-050"

  Scenario: Stale permission cache fails closed
    Given "okafor" had access to "risk-2026-001" which was revoked 1 second ago
    And the permission cache has not yet refreshed
    When "okafor" queries the cross-project risk register
    Then the results exclude "risk-2026-001"
