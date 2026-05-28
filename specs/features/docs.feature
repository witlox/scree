Feature: Docs — versioning, governed paths, editor round-trip
  Docs are versioned, not stateful. Designated paths require an MR. The WYSIWYG
  editor round-trips clean markdown.

  @api
  Scenario: Editing a doc creates a new Git version with no state change
    Given doc "doc-platform-onboarding" exists in "platform/handbook"
    When "platform-team" edits its body and saves
    Then a new Git commit records the change with the author and timestamp
    And the doc has no "status" field

  @api
  Scenario: Editing a policy doc on an MR-required path by direct commit is rejected
    Given doc "doc-security-policy" is on an MR-required path
    When a direct commit attempts to change it
    Then the commit is rejected by branch protection and CODEOWNERS

  @e2e
  Scenario: WYSIWYG edit round-trips markdown unchanged
    Given doc "doc-platform-onboarding" with a table and a code block
    When an editor opens it, makes no change, and saves
    Then the stored markdown is byte-identical to before
