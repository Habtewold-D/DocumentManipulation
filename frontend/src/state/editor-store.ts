import { configureStore, createSlice, type PayloadAction } from "@reduxjs/toolkit";

type EditorState = {
  activeDocumentId: string | null;
  selectedVersionId: string | null;
};

const initialState: EditorState = {
  activeDocumentId: null,
  selectedVersionId: null,
};

const editorSlice = createSlice({
  name: "editor",
  initialState,
  reducers: {
    setActiveDocumentId(state, action: PayloadAction<string | null>) {
      state.activeDocumentId = action.payload;
    },
    setSelectedVersionId(state, action: PayloadAction<string | null>) {
      state.selectedVersionId = action.payload;
    },
  },
});

export const { setActiveDocumentId, setSelectedVersionId } = editorSlice.actions;

export const makeStore = () =>
  configureStore({
    reducer: {
      editor: editorSlice.reducer,
    },
  });

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
