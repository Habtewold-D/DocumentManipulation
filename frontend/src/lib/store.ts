import { configureStore } from "@reduxjs/toolkit";

import { editorReducer } from "@/lib/features/editorSlice";

export const makeStore = () =>
  configureStore({
    reducer: {
      editor: editorReducer,
    },
  });

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
