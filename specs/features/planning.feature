@api
Feature: Planning views filter GitLab planning objects by permission (F-10, INV-AGG)
  Planning rollups reference GitLab epics/iterations/milestones; a viewer sees only
  objects they could see in GitLab directly. (Depends on assumptions A-4/A-5, which
  the architect validates in the spike.)

  Scenario: Portfolio rollup excludes epics the viewer cannot see
    Given epic "EPIC-100" is in a group "rivera" can read
    And epic "EPIC-200" is in a group "rivera" cannot read
    When "rivera" opens the portfolio rollup
    Then "EPIC-100" contributes to the rollup
    And "EPIC-200" does not contribute
    And the existence of "EPIC-200" is not revealed (count, title, or capacity)

  Scenario: A stale planning rollup shows an as-of timestamp
    Given the planning index was last refreshed 40 minutes ago
    When "rivera" opens the portfolio rollup
    Then the view shows the "as of" timestamp so staleness is visible
