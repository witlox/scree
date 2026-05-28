@api
Feature: Risk register (5x5 scoring, ROAM, category-driven webhook, escalation)
  Risks score 5x5, carry a ROAM strategy, and live where the work is. Only
  security/compliance category fires the near-real-time webhook (INV-IX-1).

  Scenario: Creating a risk computes score and severity band
    When "platform-team-lead" creates risk "risk-2026-044" with likelihood 4 and impact 4
    Then its score is 16
    And its severity band is "critical"

  Scenario: A security-category change fires the webhook; a high-score delivery risk does not
    Given risk "risk-2026-050" has category "security" and score 6
    And risk "risk-2026-051" has category "delivery" and score 20
    When "risk-2026-050" is updated
    Then the near-real-time indexing webhook fires for "risk-2026-050"
    When "risk-2026-051" is updated
    Then no near-real-time webhook fires for "risk-2026-051"
    And "risk-2026-051" is picked up by the next hourly batch

  Scenario: Escalating a project risk creates an org duplicate with a cross-reference
    Given project risk "risk-2026-044" lives in "platform/handbook"
    When "platform-team-lead" escalates "risk-2026-044" to "org/risk-portfolio"
    Then a new risk exists in "org/risk-portfolio"
    And it references "risk-2026-044" as escalated_from
    And "risk-2026-044" remains in "platform/handbook"

  Scenario: Closing a risk requires a merge request
    Given risk "risk-2026-044" is "open" on an MR-required path
    When a direct commit attempts to set its status to "closed"
    Then the commit is rejected by branch protection
