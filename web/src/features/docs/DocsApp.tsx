import { useState } from "react";

import { AppShell } from "../../ui/AppShell";
import { DocEditor } from "./DocEditor";
import { DocList } from "./DocList";
import { DocView } from "./DocView";

type View =
  | { mode: "list" }
  | { mode: "view"; id: string }
  | { mode: "edit"; id: string }
  | { mode: "create" };

/** Knowledge-management surface (#101): browse/read docs and edit them with the
 *  WYSIWYG editor. Single React island with internal navigation (no router needed
 *  for v1). `space` (from data-props) seeds a new doc's space. */
export function DocsApp({ space }: { space?: string }) {
  const [view, setView] = useState<View>({ mode: "list" });

  return (
    <AppShell title="Knowledge" current="knowledge">
      {view.mode === "list" && (
        <DocList
          onOpen={(id) => setView({ mode: "view", id })}
          onNew={() => setView({ mode: "create" })}
        />
      )}
      {view.mode === "view" && (
        <DocView
          docId={view.id}
          onEdit={(id) => setView({ mode: "edit", id })}
          onBack={() => setView({ mode: "list" })}
        />
      )}
      {view.mode === "edit" && (
        <DocEditor
          docId={view.id}
          isNew={false}
          onSaved={(id) => setView({ mode: "view", id })}
          onCancel={() => setView({ mode: "view", id: view.id })}
        />
      )}
      {view.mode === "create" && (
        <DocEditor
          isNew
          space={space}
          onSaved={(id) => setView({ mode: "view", id })}
          onCancel={() => setView({ mode: "list" })}
        />
      )}
    </AppShell>
  );
}
