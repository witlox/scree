import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { createQueryClient } from "./queryClient";

const client = createQueryClient();

export function QueryProvider({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
