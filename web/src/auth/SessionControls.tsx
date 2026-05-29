import { useAuth } from "react-oidc-context";

import { Button } from "../ui/Button";
import { oidcConfig } from "./config";

/** Sign-out control for the app shell. Renders nothing when OIDC is unconfigured
 *  (dev), so it never calls useAuth without a provider. The oidcConfig() branch is a
 *  build-constant, so hook order stays stable. */
export function SessionControls() {
  if (!oidcConfig()) return null;
  return <SignedIn />;
}

function SignedIn() {
  const auth = useAuth();
  if (!auth.isAuthenticated) return null;
  const name =
    (auth.user?.profile.preferred_username as string | undefined) ?? auth.user?.profile.sub ?? "account";
  return (
    <Button onClick={() => void auth.signoutRedirect()}>Sign out ({name})</Button>
  );
}
