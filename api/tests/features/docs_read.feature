@api
Feature: Permission-filtered doc read (spike — validates INV-AGG, INV-ACC)
  A requester sees only docs in Spaces they may read. Aggregation results are a
  subset of what is directly readable; unreadable resources are existence-leak-safe.

  Background:
    Given doc "doc-onboarding" in space "platform/handbook"
    And doc "doc-secret" in space "org/risk-portfolio"
    And "rivera" can read space "platform/handbook"

  Scenario: Listing excludes docs the requester cannot read (INV-AGG)
    When "rivera" lists docs
    Then the results include "doc-onboarding"
    And the results exclude "doc-secret"

  Scenario: Reading an unreadable doc returns 404 (no existence leak)
    When "rivera" reads doc "doc-secret"
    Then the response status is 404

  Scenario: Reading a readable doc returns it
    When "rivera" reads doc "doc-onboarding"
    Then the response status is 200
    And the returned doc id is "doc-onboarding"
