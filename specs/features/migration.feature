Feature: Atlassian migration (DD-014; resolves F-06)
  Big-bang cutover. Jira issues → tickets, Confluence pages → docs. Old→new ID
  mapping is preserved so existing references don't rot. Non-curated content goes
  to a read-only archive. Migration is idempotent and validated before cutover.

  @contract
  Scenario: A Jira issue migrates to a ticket with its old ID mapped
    Given a Jira issue "SUP-4821" is marked for migration
    When the migration pipeline runs
    Then a ticket exists whose body preserves the issue content
    And the mapping "SUP-4821" → that ticket id is recorded in the ID-mapping table
    And resolving "SUP-4821" via the mapping returns that ticket

  @contract
  Scenario: A Confluence page migrates to a doc with its old URL mapped
    Given a Confluence page "12345" titled "Onboarding" is marked for migration
    When the migration pipeline runs
    Then a doc exists preserving the page content
    And the mapping "confluence:12345" → that doc id is recorded

  @contract
  Scenario: Re-running the pipeline is idempotent
    Given "SUP-4821" was already migrated
    When the migration pipeline runs again
    Then no duplicate ticket is created
    And the existing mapping is unchanged

  @api
  Scenario: Non-curated content is archived, not migrated
    Given Jira issue "SUP-0001" is not marked for migration by the curation deadline
    When the migration pipeline runs
    Then no ticket is created for "SUP-0001"
    And "SUP-0001" remains available in the read-only archive

  @api
  Scenario: A reference to a migrated item resolves via the mapping
    Given doc "doc-onboarding" links to legacy URL for Confluence page "12345"
    And "confluence:12345" is mapped to "doc-onboarding-legacy"
    When a user follows the link
    Then they are resolved to the migrated doc, not a broken link
