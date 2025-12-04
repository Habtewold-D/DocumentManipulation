"use client";

import { ReactNode } from "react";
import { Provider } from "react-redux";

import { makeStore } from "@/state/editor-store";

const store = makeStore();

type ProvidersProps = {
  children: ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  return <Provider store={store}>{children}</Provider>;
}
