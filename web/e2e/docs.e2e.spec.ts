/**
 * @e2e — canonical docs.feature @e2e scenario (WYSIWYG markdown round-trip). The
 * binding is scaffolded but marked fixme: asserting the stored markdown is
 * byte-identical after a no-op Tiptap edit IS the fidelity the scenario questions
 * (ADR-0009), and a flaky/unverified round-trip assertion would be worse than an
 * honest pending. Lifting the fixme is the next step once the serializer is pinned.
 */
import { runFeature, Steps } from "./bdd";

runFeature("docs.feature", "e2e", new Steps(), {
  fixme: () => "Tiptap byte-identical markdown round-trip (tables/code blocks) pending a verified serializer (ADR-0009).",
});
