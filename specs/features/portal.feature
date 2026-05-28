Feature: External customer portal v1 (OQ-A-015 — core + KB + self-service)
  Login, submit, view own tickets, reply with attachments, status, community KB
  search, and self-service preferences.

  Background:
    Given "ext:r.okafor@uni.example.ac" is authenticated via Keycloak

  @e2e
  Scenario: A customer sees only their own tickets
    Given "ext:r.okafor@uni.example.ac" owns "ticket-2026-000123"
    And "ticket-2026-000200" belongs to another customer and is not community_visible
    When they open "My tickets"
    Then "ticket-2026-000123" is listed
    And "ticket-2026-000200" is not listed

  @e2e
  Scenario: Submit a ticket and then reply with an attachment
    When they submit a ticket titled "Cannot reset my API key"
    Then a ticket is created with origin "web" and requester "ext:r.okafor@uni.example.ac"
    When they reply with the attachment "screenshot.png"
    Then the reply and attachment appear on the ticket
    And the attachment is stored in object storage, not Git

  @api
  Scenario: Community KB search returns only community-visible resolved tickets
    Given "ticket-2026-000123" is resolved and community_visible
    And "ticket-2026-000200" is resolved and not community_visible
    When "ext:r.okafor@uni.example.ac" searches the community knowledge base for "API key"
    Then "ticket-2026-000123" may appear
    And "ticket-2026-000200" never appears

  @api
  Scenario: Self-service notification preferences
    When "ext:r.okafor@uni.example.ac" sets email notifications to "on assignment and resolution"
    Then the preference is saved and applied to future notifications
